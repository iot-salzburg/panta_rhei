#!/usr/bin/env bash
sudo apt-get update && sudo apt-get install openjdk-8-jre wget -y
export kafka_version=2.3.1
wget https://archive.apache.org/dist/kafka/${kafka_version}/kafka_2.12-${kafka_version}.tgz
tar -xvzf kafka_2.12-${kafka_version}.tgz
rm kafka_2.12-${kafka_version}.tgz

sudo rm -R /kafka > /dev/null 2>&1 || true
sudo mv kafka_2.12-${kafka_version} /kafka
sudo chmod +x /kafka/bin/*
