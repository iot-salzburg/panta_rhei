#!/usr/bin/env bash
cd $(cd -P -- "$(dirname -- "$0")" && pwd -P)

echo "Make sure the environment variable ELK_VERSION is set in .env"

source elasticStack/.env
docker-compose -f elasticStack/docker-compose.yml build
docker-compose -f elasticStack/docker-compose.yml up -d

docker-compose -f grafana/docker-compose.yml build
#docker-compose -f jupyter/docker-compose.yml build

docker-compose -f grafana/docker-compose.yml up -d
#docker-compose -f jupyter/docker-compose.yml up -d

docker-compose -f elasticStack/docker-compose.yml ps
docker-compose -f grafana/docker-compose.yml ps
#docker-compose -f jupyter/docker-compose.yml ps

echo
echo
echo "Started the whole DataStack."
echo "Make sure Elasticsearch is running and fully indexed before ingesting data."
