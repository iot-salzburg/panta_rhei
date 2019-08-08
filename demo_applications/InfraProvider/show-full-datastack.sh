#!/usr/bin/env bash
cd $(cd -P -- "$(dirname -- "$0")" && pwd -P)

docker-compose -f elasticStack/docker-compose.yml ps
docker-compose -f grafana/docker-compose.yml ps
docker-compose -f jupyter/docker-compose.yml ps
