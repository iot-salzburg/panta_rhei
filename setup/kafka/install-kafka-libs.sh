#!/usr/bin/env bash
sudo apt-get update && sudo apt-get install make
# Installing librdkafka which is an C client library for Kafka
mkdir /kafka  > /dev/null 2>&1 || true
cd /kafka
git clone https://github.com/edenhill/librdkafka
cd librdkafka
git checkout v1.5.2
./configure
make
sudo make install
sudo ldconfig

# Installing official python client which is based on librdkafka with
# pip3 install confluent-kafka
