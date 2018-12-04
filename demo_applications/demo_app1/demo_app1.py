#!/usr/bin/env python3
"""
Example:
    app1 measures the temperature of a machine and sends it into panta rhei
    app2 is an application which regulates a fan. if the temperatur exceeds a limit,
        it turns on the fan until the temperature falls below a second limit.
        It also sends the fan data into panta rhei
    datastack subscribes both variables and stores it in the elastic stack.
        Jupyter and Grafana helps to display the data.
"""

import os
import sys
import inspect

import time
import pytz
from datetime import datetime

# Append path of client to pythonpath in order to import the client from cli
sys.path.append(os.getcwd())
from client.panta_rhei_client import PantaRheiClient
from demo_applications.demo_app1.RandomisedTemp import RandomisedTemp

# Get dirname from inspect module
filename = inspect.getframeinfo(inspect.currentframe()).filename
dirname = os.path.dirname(os.path.abspath(filename))
PANTA_RHEI_INSTANCES = os.path.join(dirname, "panta_rhei_mapping/instances.json")
PANTA_RHEI_SUBSCRIPTIONS = os.path.join(dirname, "panta_rhei_mapping/subscriptions.json")

# Init a new Panta Rhei Instance and register file structure
client = PantaRheiClient("demo_app1")
client.register(instance_file=PANTA_RHEI_INSTANCES)

randomised_temp = RandomisedTemp()
try:
    while True:
        # epoch and ISO 8601 UTC are both valid
        timestamp = time.time()

        # Measure the demo temperature
        demo_temp = randomised_temp.get_temp()

        # Send the demo temperature
        client.send(quantity="demo_temperature", result=demo_temp, timestamp=timestamp)

        # Print the temperature with the corresponding timestamp in ISO format
        print("The temperature of the demo machine is {} °C at {}".format(
            demo_temp, datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat()))

        time.sleep(1)

except KeyboardInterrupt:
    client.disconnect()
