#!/usr/bin/env bash
echo "Printing 'docker service ls | grep elk':"
docker service ls | grep elk
echo ""
echo "Printing 'docker stack ps elk':"
docker stack ps elk | grep Running
