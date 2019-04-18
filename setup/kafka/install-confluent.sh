#!/usr/bin/env bash
sudo apt-get update && sudo apt-get install openjdk-8-jre wget -y
export confluent_version=5.2.1
wget http://packages.confluent.io/archive/5.2/confluent-community-${confluent_version}-2.12.tar.gz

tar -xvzf confluent-community-${confluent_version}-2.12.tar.gz
rm confluent-community-${confluent_version}-2.12.tar.gz
sudo rm -R /confluent > /dev/null 2>&1 || true
sudo mv confluent-${confluent_version} /confluent
sudo chmod +x /confluent/bin/*
