#!/usr/bin/env bash
sudo docker stack deploy  --compose-file swarm_docker-compose-with-redundant-volume.yml gost
