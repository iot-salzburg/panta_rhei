#!/usr/bin/env python3
"""
Demo Setting: Connected Cars
    car1:   The connected car wants to enhance it's safety by retrieving temperature data, to warn the driver on
            approaching slippery road sections. As each car has also temperature data that is of interest for other
            cars, it sends this data to the the platform.
    car2:   The connected car wants to enhance it's safety by retrieving temperature data, to warn the driver on
            approaching slippery road sections. As each car has also temperature data that is of interest for other
            cars, it sends this data to the the platform.
    station1: The weather station is conducted by a local weather service provider which provides the data as a service.
    station2: The weather station is conducted by a local weather service provider which provides the data as a service.
    service_provider: The weather information provider offers temperature data for it's customers.
"""

import os
import sys
import inspect
import time
import pytz
from datetime import datetime

# Append path of client to pythonpath in order to import the client from cli
sys.path.append(os.getcwd())
from client.digital_twin_client import DigitalTwinClient
from demo_applications.simulator.SimulateTemperatures import SimulateTemperatures

# Get dirname from inspect module
filename = inspect.getframeinfo(inspect.currentframe()).filename
dirname = os.path.dirname(os.path.abspath(filename))
INSTANCES = os.path.join(dirname, "instances.json")
SUBSCRIPTIONS = os.path.join(dirname, "subscriptions.json")
MAPPINGS = os.path.join(dirname, "ds-mappings.json")

# Set the configs, create a new Digital Twin Instance and register file structure
config = {"client_name": "demo_car_1",
          "system": "eu.srfg.iot-iot4cps-wp5.CarFleet1",
          "gost_servers": "localhost:8084",
          "kafka_bootstrap_servers": "localhost:9092"}
client = DigitalTwinClient(**config)
client.register_existing(mappings_file=MAPPINGS)
# client.register_new(instance_file=INSTANCES)  # Registering of new instances should be outsourced to the platform
client.subscribe(subscription_file=SUBSCRIPTIONS)
randomised_temp = SimulateTemperatures(t_factor=100, day_amplitude=4, year_amplitude=-4, average=3)

try:
    while True:
        # unix epoch and ISO 8601 UTC are both valid
        timestamp = datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat()

        # Measure the demo temperature
        temperature = randomised_temp.get_temp()

        # Send the demo temperature
        client.produce(quantity="temperature", result=temperature, timestamp=timestamp)

        # Print the temperature with the corresponding timestamp in ISO format
        print("The air temperature at the demo car 1 is {} °C at {}".format(temperature, timestamp))

        # Receive all queued messages of the weather-service and other connected cars and calculate the minimum
        minimal_temps = list()
        if temperature <= 0:
            minimal_temps.append({"origin": config["system"], "temperature": temperature})

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
                minimal_temps.append(
                    {"origin": received_quantity["Datastream"]["name"], "temperature": received_quantity["result"]})

        if minimal_temps != list():
            print("    WARNING, the road could be slippery, see: {}".format(minimal_temps))

        time.sleep(10)
except KeyboardInterrupt:
    client.disconnect()
