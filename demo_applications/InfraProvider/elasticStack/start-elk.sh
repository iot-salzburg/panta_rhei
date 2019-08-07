#!/usr/bin/env bash
cd "$(dirname "$0")"
docker-compose build
docker-compose push
docker stack deploy --compose-file docker-compose.yml elk
