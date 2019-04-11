#!/usr/bin/env bash
docker-compose --project-name iot4cps logs -f | grep -v keycloak_1
