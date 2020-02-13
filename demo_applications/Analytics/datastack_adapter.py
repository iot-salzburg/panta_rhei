#!/usr/bin/env python3
"""
Example:
    app1 measures the temperature of a machine and sends it into Digital Twin Stack
    app2 is an application which regulates a fan. if the temperatur exceeds a limit,
        it turns on the fan until the temperature falls below a second limit.
        It also sends the fan data into Digital Twin Stack
    datastack subscribes both variables and stores it in the elastic stack.
        Jupyter and Grafana helps to display the data.
"""

import os
import sys
import time
import json
import inspect
import requests

import logging
from logstash import TCPLogstashHandler

# Append path of client to pythonpath in order to import the client from cli
sys.path.append(os.getcwd())
from client.digital_twin_client import DigitalTwinClient

# Get dirname from inspect module
filename = inspect.getframeinfo(inspect.currentframe()).filename
dirname = os.path.dirname(os.path.abspath(filename))
# INSTANCES = os.path.join(dirname, "digital_twin_mapping/instances.json")
SUBSCRIPTIONS = os.path.join(dirname, "subscriptions.json")
ELASTICSTACK_URLS = ["http://localhost:9200", "http://localhost:9600"]

# Set the configs, create a new Digital Twin Instance and register file structure
# This config is generated when registering a client application on the platform
# Make sure that Kafka and GOST are up and running before starting the platform
config = {"client_name": "datastack-adapter",
          "system": "at.datahouse.iot-iot4cps-wp5.RoadAnalytics",
          "kafka_bootstrap_servers": "localhost:9092",  # "192.168.48.81:9092,192.168.48.82:9092,192.168.48.83:9092"
          "gost_servers": "localhost:8084"}  # "192.168.48.81:8082"
client = DigitalTwinClient(**config)
# client.register(instance_file=INSTANCES)
client.subscribe(subscription_file=SUBSCRIPTIONS)

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

        # Receive all queued messages of 'demo_temperature'
        received_quantities = client.consume(timeout=0.1)

        for received_quantity in received_quantities:
            # The resolves the all meta-data for an received data-point
            print("  -> Received new external data-point at {}: '{}' = {} {}."
                  .format(received_quantity["phenomenonTime"],
                          received_quantity["Datastream"]["name"],
                          received_quantity["result"],
                          received_quantity["Datastream"]["unitOfMeasurement"]["symbol"]))
            data = dict({"Datastream": {"@iot.id": received_quantity["Datastream"]["@iot.id"],
                                        "name": received_quantity["Datastream"]["name"],
                                        "unitOfMeasurement":
                                            received_quantity["Datastream"]["unitOfMeasurement"]["symbol"]},
                         "phenomenonTime": received_quantity["phenomenonTime"],
                         "resultTime": received_quantity["resultTime"],
                         "result": received_quantity["result"]})

            # Pipe the data to Logstash of the Elastic Stack
            logger_metric.info('', extra=data)
            print(json.dumps(data, indent=2))

except KeyboardInterrupt:
    client.disconnect()
