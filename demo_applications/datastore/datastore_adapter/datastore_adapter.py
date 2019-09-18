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
import inspect
import json
import logging
from logstash import TCPLogstashHandler

# Append path of client to pythonpath in order to import the client from cli
sys.path.append(os.getcwd())
from client.digital_twin_client import DigitalTwinClient

# Logstash host
datastore_host = "192.168.48.71"

# Get dirname from inspect module
filename = inspect.getframeinfo(inspect.currentframe()).filename
dirname = os.path.dirname(os.path.abspath(filename))
# INSTANCES = os.path.join(dirname, "instances.json")
SUBSCRIPTIONS = os.path.join(dirname, "subscriptions.json")

# Set the configs, create a new Digital Twin Instance and register file structure
config = {"client_name": "datastore-adapter",
          "system": "at.srfg.iot.dtz",
          "kafka_bootstrap_servers": "192.168.48.71:9092,192.168.48.72:9092,192.168.48.73:9092,192.168.48.74:9092,192.168.48.75:9092",
          "gost_servers": "192.168.48.71:8082"}
client = DigitalTwinClient(**config)
# client.register(instance_file=INSTANCES)
client.subscribe(subscription_file=SUBSCRIPTIONS)

# Init logstash logging for data
logging.basicConfig(level='WARNING')
loggername_metric = 'datastore-adapter'
logger_metric = logging.getLogger(loggername_metric)
logger_metric.setLevel(logging.INFO)
#  use default and init Logstash Handler
logstash_handler = TCPLogstashHandler(host=datastore_host,
                                      port=5000,
                                      version=1)
logger_metric.addHandler(logstash_handler)

print("Loaded clients, now start adapting")
try:
    while True:
        # Receive all queued messages of 'demo_temperature'
        received_quantities = client.consume(timeout=1)
        for received_quantity in received_quantities:
            # The resolves the all meta-data for an received data-point
            print("Received new data-point: '{}' = {} {} at {}."
                  .format(received_quantity["Datastream"]["name"],
                          received_quantity["result"],
                          received_quantity["Datastream"]["unitOfMeasurement"]["symbol"],
                          received_quantity["phenomenonTime"]))
            # To view the whole data-point in a pretty format, uncomment:
            data = dict()
            data["Datastream"] = dict()
            data["Datastream"]["name"] = received_quantity["Datastream"]["name"].split(".")[-1]
            data["Datastream"]["@iot.id"] = received_quantity["Datastream"]["@iot.id"]
            data["Datastream"]["@iot.selfLink"] = received_quantity["Datastream"]["@iot.selfLink"]
            data["result"] = received_quantity["result"]
            data["phenomenonTime"] = received_quantity["phenomenonTime"]
            data["resultTime"] = received_quantity["resultTime"]

            # send to logstash
            # print("Received new data: {}".format(json.dumps(data, indent=2)))
            logger_metric.info('', extra=data)

except KeyboardInterrupt:
    client.disconnect()
