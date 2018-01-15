## Grafana CSV Datasource - a generic backend datasource

Your backend needs to implement 4 urls:

 * `/` should return 200 ok. Used for "Test connection" on the datasource config page.
 * `/search` used by the find metric options on the query tab in panels.
 * `/query` should return metrics based on input.

## Installation

To install this plugin, clone this to your grafana plugins diretory :
```
sudo git clone https://github.com/SmartBlug/grafana-csv-datasource /var/lib/grafana/plugins/
sudo service grafana-server restart
```

You also need a backend server :
* sudo python /var/lib/grafana/plugins/grafana-csv-datasource/backend/PythonServer.py

source should now be available in the data source type dropdown in the Add Data Source View.
