#!/usr/bin/env bash
echo "Printing 'docker service ls | grep jupyter':"
docker service ls | grep jupyter
echo ""
echo "Printing 'docker stack ps jupyter':"
docker stack ps jupyter | grep Running
