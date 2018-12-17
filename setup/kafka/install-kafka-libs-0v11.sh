#!/usr/bin/env bash

# Installing librdkafka which is an C client library for Kafka
cd /kafka
git clone https://github.com/edenhill/librdkafka
cd librdkafka
git checkout v0.11.1 && \
./configure
make
make install
ldconfig

# Installing official python client which is based on librdkafka
pip3 install confluent-kafka==0.9.4
