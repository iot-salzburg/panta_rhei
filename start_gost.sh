#!/usr/bin/env bash
cd gost_server
sudo docker-compose build
sudo docker-compose push || true
sudo docker stack deploy  --compose-file docker-compose.yml gost