#!/usr/bin/env bash
echo "Printing 'docker service ls | grep grafana':"
docker service ls | grep grafana
echo ""
echo "Printing 'docker stack ps grafana':"
docker stack ps grafana | grep Running
