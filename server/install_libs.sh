#!/usr/bin/env bash
cd $(cd -P -- "$(dirname -- "$0")" && pwd -P)

sudo apt-get install -y postgresql
sudo apt-get install -y python-psycopg2
sudo apt-get install -y libpq-dev
