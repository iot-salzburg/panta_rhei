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
import time

# Append path of client to pythonpath in order to import the client from cli
sys.path.append(os.getcwd())
from client.digital_twin_client import DigitalTwinClient

# Get dirname from inspect module
filename = inspect.getframeinfo(inspect.currentframe()).filename
dirname = os.path.dirname(os.path.abspath(filename))
INSTANCES = os.path.join(dirname, "digital_twin_mapping/instances.json")
SUBSCRIPTIONS = os.path.join(dirname, "digital_twin_mapping/subscriptions.json")

# Set the configs, create a new Digital Twin Instance and register file structure
config = {"client_name": "demo_app2",
          "system_name": "demo-system",
          "kafka_bootstrap_servers": "localhost:9092",  # "192.168.48.81:9092,192.168.48.82:9092,192.168.48.83:9092"
          "gost_servers": "localhost:8082"}  # "192.168.48.81:8082"
client = DigitalTwinClient(**config)
client.register(instance_file=INSTANCES)
client.subscribe(subscription_file=SUBSCRIPTIONS)

fan_status = False
try:
    while True:
        # Receive all queued messages of 'demo_temperature'
        received_quantity = client.poll(timeout=1)
        if received_quantity is None:
            continue

        print("Received new data: {}".format(received_quantity))

        # Only use the quantity, if it is the Machine Temperature
        if received_quantity.get("Datastream").get("name") == "Machine Temperature":
            current_temperature = received_quantity["result"]
            # If the temperature exceeds 70 degree, it will turned on. Under 60 degree, it is turned off.
            if current_temperature > 70:
                fan_status = True
            elif current_temperature < 60:
                fan_status = False

                timestamp = time.time()  # epoch and ISO 8601 UTC are both valid

                # Sending fan status
                client.send(quantity="demo_fan-status", result=fan_status, timestamp=timestamp)

except KeyboardInterrupt:
    client.disconnect()
