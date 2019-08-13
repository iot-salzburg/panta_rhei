#!/usr/bin/env bash
cd $(cd -P -- "$(dirname -- "$0")" && pwd -P)

docker-compose -f grafana/docker-compose.yml down
docker-compose -f jupyter/docker-compose.yml down
docker-compose -f elasticStack/docker-compose.yml down

echo
echo "Stopped the whole DataStack."
