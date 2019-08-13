# Elastic Stack with configuration for Docker swarm

#### composed by the [Elastic Stack 6.2](https://github.com/elastic/).

## Contents

1. [Requirements](../README.md) (parent directory)
2. [Quickstart](#quickstart)
2. [Deployment](#deployment)
3. [Services](#services)

## Quickstart

Running these commands will build, push and deploy the stack:

**Check if the paths in 'docker-compose.yml' do exist and are syncronized!**

```bash
sudo docker-compose -f elasticStack/docker-compose.yml up --build
```

With these commands we can see if everything worked well:
```bash
docker-compose -f elasticStack/docker-compose.yml ps
docker logs [service_name] -f  # with e.g. elasticstack_kibana_1
```


## Deployment

Running these commands will build, push and deploy the stack:

**Check if the paths in 'docker-compose.yml' do exist and are syncronized!**

```bash
./elasticStack/start_stack.sh
```

With these commands we can see if everything worked well:
```bash
./elasticStack/show_stack.sh
docker service ps service-name # (e.g elasticstack_elasticsearch)
```

##  Services

Give Kibana a minute to initialize, then access the Kibana web UI by hitting
[http://localhost:5601](http://localhost:5601) with a web browser.
The indexing of elasticsearch could last 15 minutes or more, so we have to be patient.
On Kibana UI, DevTools we can trace the indexing success by hitting the REST request
`GET _cat/indices`.


By default, the stack exposes the following ports:
* 9200: Elasticsearch HTTP
* 5000: Logstash TCP input
* 9600: Logstash HTTP
* **5601: Kibana:** User Interface for data in Elasticsearch
on elastic data


### Tracing

Watch if everything worked fine with:
```bash
sudo docker service ls
sudo docker service logs -f service-name
sudo docker service ps service-name --no-trunc
```
