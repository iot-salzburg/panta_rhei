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

# Set the configs, create a new Digital Twin Instance and register file structure
config = {"client_name": "datastack-adapter",
          "system": "at.srfg.iot-iot4cps-wp5.CarFleet1",  # TODO Change that to infraprov
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

fan_status = False
try:
    while True:
        # Receive all queued messages of 'demo_temperature'
        received_quantities = client.consume(timeout=0.5)
        for received_quantity in received_quantities:
            # The resolves the all meta-data for an received data-point
            print("  -> Received new external data-point at {}: '{}' = {} {}."
                  .format(received_quantity["phenomenonTime"],
                          received_quantity["Datastream"]["name"],
                          received_quantity["result"],
                          received_quantity["Datastream"]["unitOfMeasurement"]["symbol"]))
            # To view the whole data-point in a pretty format, uncomment:
            # print("Received new data: {}".format(json.dumps(received_quantity, indent=2)))
            if received_quantity["result"] <= 0:
                # print("Received new data: {}".format(json.dumps(received_quantity, indent=2)))
                logger_metric.info('', extra=received_quantity)

except KeyboardInterrupt:
    client.disconnect()
