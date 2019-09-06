#!/usr/bin/env python3
"""
This script tests the connection to the Elastic stack by ingesting random-walk data periodically
"""

import os
import sys
import time
import inspect
import random
import requests
import pytz
from datetime import datetime

import logging
from logstash import TCPLogstashHandler

# Set the configs, create a new Digital Twin Instance and register file structure
config = {"client_name": "datastack-adapter-test",
          "system": "test"}
ELASTICSTACK_URLS = ["http://localhost:9200", "http://localhost:9600"]

# Init logstash logging for data
logging.basicConfig(level='WARNING')
loggername_metric = config["system"] + "." + config["client_name"]
logger_metric = logging.getLogger(loggername_metric)
logger_metric.setLevel(logging.INFO)
#  use default and init Logstash Handler
logstash_handler = TCPLogstashHandler(host="localhost",
                                      port=5000,
                                      version=1)
logger_metric.addHandler(logstash_handler)

current_number = 0
try:
    while True:
        # Check first if Elastic Search is up and running
        connected = False
        try:
            if requests.get(ELASTICSTACK_URLS[0]).status_code == 200 \
                    and requests.get(ELASTICSTACK_URLS[1]).status_code == 200:
                connected = True
        except requests.exceptions.ConnectionError as e:
            print("Connection Error: {}".format(e))
        if not connected:
            print("Connection to Elastic Stack on URLS {} couldn't be established. Trying again in 5 s."
                  .format(ELASTICSTACK_URLS))
            time.sleep(5)
            continue
        # Build a sample quantity
        current_number += random.random() - 0.5
        dt = datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat()
        data = dict({"Datastream": {"@iot.id": 0,
                                    "name": config["system"] + ".random_walk",
                                    "unitOfMeasurement": 1},
                     "phenomenonTime": dt,
                     "resultTime": dt,
                     "result": current_number})

        # Send to logstash
        logger_metric.info('', extra=data)
        # sys.exit()
        time.sleep(3)

except KeyboardInterrupt:
    print("stopped gracefully")
