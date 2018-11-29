## Grafana CSV Datasource - a generic backend datasource

Your backend needs to implement 4 urls:

 * `/<folder>/` should return 200 ok. Used for "Test connection" on the datasource config page.
 * `/<folder>/sources` should return the list of CSV within the group folder.
 * `/<folder>/search` used by the find metric options on the query tab in panels.
 * `/<folder>/query` should return metrics based on input.

## Installation

To install this plugin, clone this to your grafana plugins diretory :
```
sudo git clone https://github.com/SmartBlug/grafana-csv-datasource /var/lib/grafana/plugins/grafana-csv-datasource
sudo service grafana-server restart
```

You also need a backend server :
```
sudo python /var/lib/grafana/plugins/grafana-csv-datasource/backend/PythonServer.py -f ./folders
```

where "folders" contains :
 * one folder per group
```
./folders/sample
```
 * CSV within the group folder
```
./folders/sample/myFirstCSV.csv
./folders/sample/mySecondCSV.csv
...
```

Configure Source with the group folder
* URL : http://localhost:3003/sample
* Access : Proxy

source should now be available in the data source type dropdown in the Add Data Source View.
