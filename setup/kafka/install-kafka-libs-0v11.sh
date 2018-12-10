#!/usr/bin/env bash
apt-get update
cd ~
git clone https://github.com/edenhill/librdkafka
cd librdkafka
git checkout v0.11.1 && \
./configure
make
make install
ldconfig

pip3 install confluent-kafka==0.9.4
