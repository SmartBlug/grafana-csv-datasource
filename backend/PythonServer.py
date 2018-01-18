#!/usr/bin/python

from flask import Flask, request, jsonify, json, abort
from flask_cors import CORS, cross_origin

import pandas as pd
import numpy as np
import glob,os
import csv
import sys,getopt

from datetime import datetime

app = Flask(__name__)

cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

methods = ('GET', 'POST')
path = './'

metric_finders= {}
metric_readers = {}
annotation_readers = {}
panel_readers = {}

#path = os.getcwd();

def add_reader(name, reader):
  metric_readers[name] = reader


def add_finder(name, finder):
  metric_finders[name] = finder


def add_annotation_reader(name, reader):
  annotation_readers[name] = reader


def add_panel_reader(name, reader):
  panel_readers[name] = reader

#----------------------------------------------------------------------------------
@app.route('/<folder>/', methods=methods)
@app.route('/<folder>', methods=methods)
@cross_origin()
def hello_world(folder):
	#print(path)
	print(path+str(folder))
	if (os.path.isdir(path+str(folder))):
		return 'CSV Python Grafana datasource for '+str(folder)
	else:
		abort(404)

#----------------------------------------------------------------------------------
@app.route('/<folder>/sources', methods=methods)
@cross_origin(max_age=600)
def query_routes(folder):
  results = []
  for file in glob.glob(path+str(folder)+"/*.csv"):
  	results.append(os.path.basename(file)[:-4])
  return jsonify(results)

#----------------------------------------------------------------------------------
@app.route('/<folder>/search', methods=methods)
@cross_origin()
def find_metrics(folder):
	#print request.headers, request.get_json()
	req = request.get_json()
	source = req.get('source', '')
	# Load headers
	#with open(path+str(folder)+"/"+source+".csv",'rb') as csvfile:
	#	reader = csv.DictReader(csvfile, delimiter=';', quotechar='|')
	#	fieldnames = reader.fieldnames

	with open(path+str(folder)+"/"+source+".csv",'rb') as csvfile:
		dialect = csv.Sniffer().sniff(csvfile.read(1024))
		csvfile.seek(0) 
		reader = csv.reader(csvfile, dialect)
		fieldnames = reader.next()

	target = req.get('target', '')
	metrics = []
	for key in fieldnames:
		if key.find(target)!=-1:
			metrics.append(key)
	#print(metrics)
	return jsonify(metrics)

#----------------------------------------------------------------------------------
def dataframe_to_response(target, df):
	response = []
	
	#print("dataframe_to_response")
	if df.empty:
	    return response
	
	#if freq is not None:
	#    orig_tz = df.index.tz
	#    df = df.tz_convert('UTC').resample(rule=freq, label='right', closed='right', how='mean').tz_convert(orig_tz)
	
	if isinstance(df, pd.Series):
	    response.append(_series_to_response(df, target))
	elif isinstance(df, pd.DataFrame):
		for col in df:
			#print("------")
			#print(col)
			response.append(_series_to_response(df[col], target))
	else:
	    abort(404, Exception('Received object is not a dataframe or series.'))
	
	return response


def dataframe_to_json_table(target, df):
    response = []

    if df.empty:
        return response

    if isinstance(df, pd.DataFrame):
        response.append({'type': 'table',
                         'columns': df.columns.map(lambda col: {"text": col}).tolist(),
                         'rows': df.where(pd.notnull(df), None).values.tolist()})
    else:
        abort(404, Exception('Received object is not a dataframe.'))

    return response


def annotations_to_response(target, df):
    response = []

    # Single series with DatetimeIndex and values as text
    if isinstance(df, pd.Series):
        for timestamp, value in df.iteritems():
            response.append({
                "annotation": target, # The original annotation sent from Grafana.
                "time": timestamp.value // 10 ** 6, # Time since UNIX Epoch in milliseconds. (required)
                "title": value, # The title for the annotation tooltip. (required)
                #"tags": tags, # Tags for the annotation. (optional)
                #"text": text # Text for the annotation. (optional)
            })
    # Dataframe with annotation text/tags for each entry
    elif isinstance(df, pd.DataFrame):
        for timestamp, row in df.iterrows():
            annotation = {
                "annotation": target,  # The original annotation sent from Grafana.
                "time": timestamp.value // 10 ** 6,  # Time since UNIX Epoch in milliseconds. (required)
                "title": row.get('title', ''),  # The title for the annotation tooltip. (required)
            }

            if 'text' in row:
                annotation['text'] = str(row.get('text'))
            if 'tags' in row:
                annotation['tags'] = str(row.get('tags'))

            response.append(annotation)
    else:
        abort(404, Exception('Received object is not a dataframe or series.'))

    return response

def _series_to_annotations(df, target):
    if df.empty:
        return {'target': '%s' % (target),
                'datapoints': []}

    sorted_df = df.dropna().sort_index()
    timestamps = (sorted_df.index.astype(pd.np.int64) // 10 ** 6).values.tolist()
    values = sorted_df.values.tolist()

    return {'target': '%s' % (df.name),
            'datapoints': zip(values, timestamps)}


def _series_to_response(df, target):
    if df.empty:
        return {'target': '%s' % (target),
                'datapoints': []}

    sorted_df = df.dropna().sort_index()

    try:
        timestamps = (sorted_df.index.astype(pd.np.int64) // 10 ** 6).values.tolist() # New pandas version
    except:
        timestamps = (sorted_df.index.astype(pd.np.int64) // 10 ** 6).tolist()

    values = sorted_df.values.tolist()

    return {'target': '%s' % (df.name),
            'datapoints': zip(values, timestamps)}

#----------------------------------------------------------------------------------
@app.route('/<folder>/query', methods=methods)
@cross_origin(max_age=600)
def query_metrics(folder):
	#print request.headers, request.get_json()
	req = request.get_json()
	#print("#debug query",req)
	
	results = []
	
	# On charge les CSVs
	CSVs = {}
	for target in req['targets']:
		source = target['source']
		if source=="":
			return jsonify(results)
		if source not in CSVs:
			with open(path+str(folder)+"/"+source+".csv",'rb') as csvfile:
				dialect = csv.Sniffer().sniff(csvfile.read(1024))
				CSVs[source] = pd.read_csv(path+str(folder)+"/"+source+".csv",index_col=0 , dialect=dialect)
				#CSVs[source] = pd.read_csv(path+str(folder)+"/"+source+".csv",index_col=0 , delimiter=';', dialect=dialect)

	#print(CSVs)
	
	
	#ts_range = {'$gt': pd.Timestamp(req['range']['from']).to_pydatetime(),
	#            '$lte': pd.Timestamp(req['range']['to']).to_pydatetime()}
	#ts = pd.date_range(ts_range['$gt'], ts_range['$lte'], freq='H')
	#if 'intervalMs' in req:
	#    freq = str(req.get('intervalMs')) + 'ms'
	#else:
	#    freq = None
	    
	for target in req['targets']:
		#print("target",target)
		#print(ts_range)
		source = target['source']
		query_results = CSVs[source].filter(items=[target["target"]])
		#print(query_results)
		#query_results = query_results.rename(columns={target["target"]: 'value'})
		# Convertis en numerique
		#print(query_results[target["target"]].dtype==object)
		if (query_results[target["target"]].dtype==object):
			query_results[target["target"]] = pd.to_numeric(query_results[target["target"]].str.replace(',','.'), errors='coerce')
		# On ajuste la date
		query_results.index = pd.to_datetime(query_results.index).tz_localize('Europe/Paris')
		#print("query_results before timing filter",query_results)
		#print('timing Filter',ts_range)
		query_results = query_results[(query_results.index >= pd.Timestamp(req['range']['from']).to_pydatetime()) & (query_results.index <= pd.Timestamp(req['range']['to']).to_pydatetime())]
		#query_results = query_results[query_results.index.isin(pd.date_range(pd.Timestamp(req['range']['from']).to_pydatetime(), pd.Timestamp(req['range']['to']).to_pydatetime()))]
		#print("query_results after timing filter",query_results)
		#query_results = query_results(index=ts)
		#print('time',loc)
		#print(loc.columns.values)
		#index = loc.columns.values[0]
		#print(index)
		#loc.index.tz_localize('UTC')
		#del loc[index]
		#print('date',loc)
		#loc.index = loc['date']
		#loc.index.tz_localize('UTC')
		#del loc['date']
		#print('filteredtime',loc)
		#results.extend(dataframe_to_response(target, loc))
		#return jsonify(results)
		
		#ts = pd.date_range(ts_range['$gt'], ts_range['$lte'], freq='H')
		#print(pd.Series(loc, index=ts).to_frame('value'))
		#myts = loc.unstack()
		#series1=loc.loc[0,:]
		#print(loc)
		#print(loc.to_string())
		
		#ts = pd.date_range(ts_range['$gt'], ts_range['$lte'], freq='H')
		#print(pd.Series(CSVs[source], index=ts).to_frame('Traffic'))
		#if ':' not in target.get('target', ''):
		#    abort(404, Exception('Target must be of type: <finder>:<metric_query>, got instead: ' + target['target']))
		#target["target"] = "sine_wave:10"
		#if ':' in target.get('target', ''): 
		#  req_type = target.get('type', 'timeserie')
		#  finder, target = target['target'].split(':', 1)
		#  query_results = metric_readers[finder](target, ts_range)
		#  print(query_results)
		#print("results before",results)
		#print("target before",target)
		#print("query_results before",query_results)
		#print(">>>>>>>>>>>>>>>>>>>>>>>>>>")
		if target.get('type', 'timeserie') == 'table':
		    results.extend(dataframe_to_json_table(target, query_results))
		else:
		    results.extend(dataframe_to_response(target, query_results))
		#print("results after",results)
		
	#print(results)
	return jsonify(results)

#----------------------------------------------------------------------------------
@app.route('/<folder>/annotations', methods=methods)
@cross_origin(max_age=600)
def query_annotations(folder):
    print request.headers, request.get_json()
    req = request.get_json()

    results = []

    ts_range = {'$gt': pd.Timestamp(req['range']['from']).to_pydatetime(),
                '$lte': pd.Timestamp(req['range']['to']).to_pydatetime()}

    query = req['annotation']['query']

    if ':' not in query:
        abort(404, Exception('Target must be of type: <finder>:<metric_query>, got instead: ' + query))

    finder, target = query.split(':', 1)
    results.extend(annotations_to_response(query, annotation_readers[finder](target, ts_range)))

    return jsonify(results)


#----------------------------------------------------------------------------------
@app.route('/<folder>/panels', methods=methods)
@cross_origin()
def get_panel(folder):
    print request.headers, request.get_json()
    req = request.args

    ts_range = {'$gt': pd.Timestamp(int(req['from']), unit='ms').to_pydatetime(),
                '$lte': pd.Timestamp(int(req['to']), unit='ms').to_pydatetime()}

    query = req['query']

    if ':' not in query:
        abort(404, Exception('Target must be of type: <finder>:<metric_query>, got instead: ' + query))

    finder, target = query.split(':', 1)
    return panel_readers[finder](target, ts_range)

#----------------------------------------------------------------------------------
def main(argv):
	global path
	port = 3003
	debug = False
	addr = '0.0.0.0'
	try:
	  opts, args = getopt.getopt(argv,"hvp:f:a:",["port=","folder=","addr="])
	except getopt.GetoptError:
	  print 'PythonServer.py -p <port> -f <folder>'
	  sys.exit(2)
	for opt, arg in opts:
	  if opt == '-h':
	     print 'PythonServer.py -p <port> -f <folder>'
	     sys.exit()
	  elif opt in ("-a", "--addr"):
	     addr = arg
	  elif opt in ("-p", "--port"):
	     port = int(arg)
	  elif opt in ("-f", "--folder"):
	     path = arg
	  elif opt in ("-v"):
	     debug = True
	#print 'Port is ', port
	#print 'Folder is ', path
	print 'debug', debug
	
	app.run(host=addr, port=port, debug=debug)
   
if __name__ == '__main__':
	main(sys.argv[1:])
