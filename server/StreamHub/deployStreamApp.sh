#!/usr/bin/env bash
cd $(cd -P -- "$(dirname -- "$0")" && pwd -P)

# Get the host's ip
export HOST_IP=$(hostname -I | cut -d' ' -f1)
echo "Starting a StreamApp via docker-compose with host $HOST_IP."

docker-compose up --build -d
echo "Started. Check 'docker-compose logs -f' for logs."
