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

import time

from client.panta_rhei_client import PantaRheiClient

PANTA_RHEI_INSTANCES = "panta_rhei_mapping/instances.json"
PANTA_RHEI_SUBSCRIPTIONS = "panta_rhei_mapping/subscriptions.json"

client = PantaRheiClient("demo_app2")
client.register(instance_file=PANTA_RHEI_INSTANCES)
client.subscribe(subscription_file=PANTA_RHEI_SUBSCRIPTIONS)

fan_status = False
try:
    while True:
        # Receive all queued messages of 'demo_temperature'

        received_quantities = client.poll(timeout=1)
        if received_quantities is None:
            continue

        print("Received new data: {}".format(received_quantities))

        # As we have only subscribed one datastream, we can be sure that this is the Temperature data
        current_temperature = received_quantities["result"]
        if current_temperature > 70:
            fan_status = True
        elif current_temperature < 60:
            fan_status = False

            timestamp = time.time()  # epoch and ISO 8601 UTC are both valid

            # Sending fan status
            client.send(quantity="demo_fan-status", result=fan_status, timestamp=timestamp)

except KeyboardInterrupt:
    client.disconnect()
