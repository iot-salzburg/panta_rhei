#!/usr/bin/env bash
sudo apt-get update && sudo apt-get install openjdk-8-jre wget -y
export kafka_version=2.1.0
wget https://archive.apache.org/dist/kafka/${kafka_version}/kafka_2.12-${kafka_version}.tgz
tar -xvzf kafka_2.12-${kafka_version}.tgz
rm kafka_2.12-${kafka_version}.tgz
sudo rm -R /kafka > /dev/null 2>&1 || true
sudo mv kafka_2.12-${kafka_version} /kafka
sudo chmod +x /kafka/bin/*

# Used to write logs into specified data directory
#mkdir -p /kafka/data/zookeeper
#cp /kafka/config/zookeeper.properties /kafka/config/orig_zookeeper.properties
#sh -c "echo dataDir=/kafka/data/zookeeper >> /kafka/config/zookeeper.properties"
#
#mkdir -p /kafka/data/kafka
#cp /kafka/config/server.properties /kafka/config/orig_server.properties
#sh -c "echo '' >> /kafka/config/server.properties"
#sh -c "echo log.dirs=/kafka/data/kafka >> /kafka/config/server.properties"
