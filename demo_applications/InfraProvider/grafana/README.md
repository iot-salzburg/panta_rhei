# Grafana visualizing data

#### Module [Grafana 5](http://docs.grafana.org/)


The easiest way to feed data into the DataStack is to use the
[datastack-adapter](https://github.com/iot-salzburg/dtz_datastack/tree/master/datastack-adapter) to stream data
from the [panta-rhei messaging system](https://github.com/iot-salzburg/dtz_datastack/tree/master/elasticStack).

## Contents

1. [Requirements](../README.md) (parent directory)
2. [Quickstart](#quickstart)
2. [Deployment](#deployment)

## Quickstart

Running these commands will build, push and deploy the stack:

**Check if the paths in 'docker-compose.yml' do exist and are syncronized!**

```bash
sudo docker-compose -f grafana/docker-compose.yml up --build
```

Grafana will be reachable on [localhost:3000](http://localhost:3000).
It is normal that only a ugly interface is seen here, the real UI is only accessible via
the Proxy. To see the real UI on localhost, comment out
 `GF_SERVER_ROOT_URL: "%(protocol)s://%(domain)s/grafana/"` in the `grafana/docker-compose.yml`.

### Add a new dashboard:

Add a new datasource where the url is `http://elasticsearch:9200` and test it.

Add a new dashboard panel an select for example (using lucene query) 
`Datastream.name: "Robot X-Vibration"`.
Then a new graph should appear that can be configured.


With these commands we can see if everything worked well:
```bash
docker-compose -f grafana/docker-compose.yml ps
docker logs grafana_grafana -f
```

## Deployment

Running these commands will build, push and deploy the stack:

**Check if the paths in 'docker-compose.yml' do exist and are syncronized!**

```bash
./grafana/start_grafana.sh
```

With these commands we can see if everything worked well:
```bash
./grafana/show_grafana.sh
docker service ps grafana_grafana
```
