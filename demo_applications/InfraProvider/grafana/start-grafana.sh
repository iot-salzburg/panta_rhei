#!/usr/bin/env bash
cd $(cd -P -- "$(dirname -- "$0")" && pwd -P)
docker-compose build
docker-compose push
docker stack deploy --compose-file swarm-docker-compose.yml grafana
