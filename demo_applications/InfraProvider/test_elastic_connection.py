#!/usr/bin/env python3
"""
This script tests the connection to the Elastic stack by ingesting random-walk data periodically
"""

import os
import sys
import time
import inspect
import random
import pytz
from datetime import datetime

import logging
from logstash import TCPLogstashHandler

# Set the configs, create a new Digital Twin Instance and register file structure
config = {"client_name": "datastack-adapter-test",
          "system_name": "test"}

# Init logstash logging for data
logging.basicConfig(level='WARNING')
loggername_metric = config["system_name"] + "." + config["client_name"]
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
        # Build a sample quantity
        current_number += random.random() - 0.5
        dt = datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat()
        received_quantity = {"phenomenonTime": dt,
                             "resultTime": dt,
                             "result": current_number,
                             "Datastream": {"@iot.id": 0}}

        # Send to logstash
        logger_metric.info('', extra=received_quantity)

        time.sleep(3)

except KeyboardInterrupt:
    print("stopped gracefully")
