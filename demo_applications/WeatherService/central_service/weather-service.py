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
import inspect

# Append path of client to pythonpath in order to import the client from cli
sys.path.append(os.getcwd())
from client.digital_twin_client import DigitalTwinClient

# Get dirname from inspect module
filename = inspect.getframeinfo(inspect.currentframe()).filename
dirname = os.path.dirname(os.path.abspath(filename))
INSTANCES = os.path.join(dirname, "instances.json")
SUBSCRIPTIONS = os.path.join(dirname, "subscriptions.json")

# Set the configs, create a new Digital Twin Instance and register file structure
config = {"client_name": "weather-service-consumer",
          "system": "eu.srfg.iot-iot4cps-wp5.WeatherService",
          "gost_servers": "localhost:8084",
          "kafka_bootstrap_servers": "localhost:9092",  # kafka bootstrap server is the preferred way to connect
          "kafka_rest_server": "localhost:8082"}
client = DigitalTwinClient(**config)
# client.register_new(instance_file=INSTANCES)
client.subscribe(subscription_file=SUBSCRIPTIONS)


fan_status = False
try:
    while True:
        # Receive all queued messages of the weather-service
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

except KeyboardInterrupt:
    client.disconnect()
