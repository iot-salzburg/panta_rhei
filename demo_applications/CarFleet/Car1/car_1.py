#!/usr/bin/env python3
"""
Demo Scenario: Connected Cars
    CarFleet:
        The connected car wants to enhance it's safety by retrieving temperature data, to warn the driver on
        approaching slippery road sections. As each car has also temperature data that is of interest for other
        cars, it sends this data to the the platform.
    InfraProv:
        The provider of the road infrastructure wants to enhance it's road quality and therefore consumes and analyses data.
    WeatherStation:
        stations: The weather stations are conducted by a local weather service provider which provides the data as a service.
        service_provider: The weather information provider offers temperature data for it's customers.
"""

import os
import time
import pytz
import inspect
import threading
from datetime import datetime

from client.digital_twin_client import DigitalTwinClient
from demo_applications.simulator.CarSimulator import CarSimulator

# Get dirname from inspect module
filename = inspect.getframeinfo(inspect.currentframe()).filename
dirname = os.path.dirname(os.path.abspath(filename))
INSTANCES = os.path.join(dirname, "instances.json")
SUBSCRIPTIONS = os.path.join(dirname, "subscriptions.json")
MAPPINGS = os.path.join(dirname, "ds-mappings.json")


def produce_metrics(car, client, interval=10):
    while not halt_event.is_set():
        # unix epoch and ISO 8601 UTC are both valid
        timestamp = datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat()

        # Measure metrics
        car.update_positions()
        temperature = car.temp.get_temp()
        acceleration = car.get_acceleration()
        latitude = car.get_latitude()
        longitude = car.get_longitude()
        attitude = car.get_attitude()

        # Print the temperature with the corresponding timestamp in ISO format
        print("The demo car 1 is at [{}, {}],   \twith the temp.: {} °C  \tand had a maximal acceleration of "
              "{} m/s²  \tat {}".format(latitude, longitude, temperature, acceleration, timestamp))

        # Send the metrics via the client, it is suggested to use the same timestamp for later analytics
        client.produce(quantity="temperature", result=temperature, timestamp=timestamp)
        client.produce(quantity="acceleration", result=acceleration, timestamp=timestamp)
        client.produce(quantity="GPS-position-latitude", result=latitude, timestamp=timestamp)
        client.produce(quantity="GPS-position-longitude", result=longitude, timestamp=timestamp)
        client.produce(quantity="GPS-position-attitude", result=attitude, timestamp=timestamp)

        time.sleep(interval)


# Receive all temperatures of the weather-service and other cars and check whether they are subzero
def consume_metrics(client):
    while not halt_event.is_set():
        # In this list, each datapoint is stored that yiels a result below zero degC.
        subzero_temp = list()

        # Data of the same instance can be consumed directly via the class method
        temperature = car.temp.get_temp()
        if temperature < 0:
            subzero_temp.append({"origin": config["system"], "temperature": temperature})

        # Data of other instances (and also the same one) can be consumed via the client
        received_quantities = client.consume(timeout=1.0)
        for received_quantity in received_quantities:
            # The resolves the all meta-data for an received data-point
            print("  -> Received new external data-point at {}: '{}' = {} {}."
                  .format(received_quantity["phenomenonTime"],
                          received_quantity["Datastream"]["name"],
                          received_quantity["result"],
                          received_quantity["Datastream"]["unitOfMeasurement"]["symbol"]))
            # To view the whole data-point in a pretty format, uncomment:
            # print("Received new data: {}".format(json.dumps(received_quantity, indent=2)))
            if received_quantity["Datastream"]["unitOfMeasurement"]["symbol"] == "degC" \
                    and received_quantity["result"] < 0:
                subzero_temp.append(
                    {"origin": received_quantity["Datastream"]["name"], "temperature": received_quantity["result"]})

        # Check whether there are temperatures are subzero
        if subzero_temp != list():
            print("    WARNING, the road could be slippery, see: {}".format(subzero_temp))


if __name__ == "__main__":
    # Set the configs, create a new Digital Twin Instance and register file structure
    # This config is generated when registering a client application on the platform
    # Make sure that Kafka and GOST are up and running before starting the platform
    config = {"client_name": "car_1",
              "system": "cz.icecars.iot-iot4cps-wp5.CarFleet",
              "gost_servers": "localhost:8082",
              "kafka_bootstrap_servers": "localhost:9092"}
    client = DigitalTwinClient(**config)
    client.logger.info("Main: Starting client.")
    client.register(instance_file=INSTANCES)  # Register new instances should be outsourced to the platform
    client.subscribe(subscription_file=SUBSCRIPTIONS)

    # Create an instance of the CarSimulator that simulates a car driving on different tracks through Salzburg
    car = CarSimulator(track_id=1, time_factor=100, speed=30, cautiousness=1,
                       temp_day_amplitude=4, temp_year_amplitude=-4, temp_average=3, seed=1)
    client.logger.info("Main: Created instance of CarSimulator.")

    client.logger.info("Main: Starting producer and consumer threads.")
    halt_event = threading.Event()

    # Create and start the receiver Thread that consumes data via the client
    consumer = threading.Thread(target=consume_metrics, kwargs=({"client": client}))
    consumer.start()
    # Create and start the receiver Thread that publishes data via the client
    producer = threading.Thread(target=produce_metrics, kwargs=({"car": car, "client": client, "interval": 1}))
    producer.start()

    # set halt signal to stop the threads if a KeyboardInterrupt occurs
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        client.logger.info("Main: Set halt signal to producer and consumer.")
        halt_event.set()
        producer.join()
        consumer.join()
        client.logger.info("Main: Stopped the demo applications.")
        client.disconnect()
