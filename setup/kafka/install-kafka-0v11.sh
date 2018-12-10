#!/usr/bin/env bash
sudo apt-get update && sudo apt-get install openjdk-8-jre wget -y
export kafka_version=0.11.0.3
wget https://archive.apache.org/dist/kafka/${kafka_version}/kafka_2.11-${kafka_version}.tgz
tar -xvzf kafka_2.11-${kafka_version}.tgz
rm kafka_2.11-${kafka_version}.tgz
sudo mv kafka_2.11-${kafka_version} /kafka
sudo chmod +x /kafka/bin/*
