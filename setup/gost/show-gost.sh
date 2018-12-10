#!/usr/bin/env bash
echo "docker service ls |grep gost_"
docker service ls |grep gost_

echo "docker stack ps gost"
docker stack ps gost
