#!/usr/bin/env python3
"""
Demo Scenario: Connected Cars
    CarFleet:
        Connected cars want to enhance their safety by retrieving temperature, acceleration and position data from each
        other, to warn the drivers on approaching dangerous road sections. As each car measures these quantities by
        them selves, they are shared to others via the the platform.
    Analytics:
        A provider of applied data analytics with the goal to improve the road quality. Therefore, data of various
         sources are consumed.
    WeatherService:
        A Weather Service provider that conducts multiple Stations that measure weather conditions, as well as a
        central service to forecast the Weather. Additionally, the temperature data is of interest for the CarFleet and
        therefore shared with them.
"""

import os
import time
import pytz
import threading
from datetime import datetime

from client.digital_twin_client import DigitalTwinClient
from demo_applications.simulator.CarSimulator import CarSimulator

# load files relative to this file
dirname = os.path.dirname(os.path.abspath(__file__))
INSTANCES = os.path.join(dirname, "instances.json")
SUBSCRIPTIONS = os.path.join(dirname, "subscriptions.json")


def produce_metrics(interval=10):
    while not halt_event.is_set():
        # unix epoch and ISO 8601 UTC are both valid
        timestamp = datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat()

        # Measure metrics
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
def consume_metrics():
    while not halt_event.is_set():
        # In this list, each datapoint is stored that yiels a result below zero degC.
        subzero_temp = list()

        # Data of the same instance can be consumed directly via the class method
        temperature = car.temp.get_temp()
        if temperature < 0:
            subzero_temp.append({"origin": config["system"], "temperature": temperature})

        # Data of other instances (and also the same one) can be consumed via the client
        received_quantities = client.consume(timeout=0.1)
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

        # # Check whether there are temperatures are subzero
        # if subzero_temp != list():
        #     print("    WARNING, the road could be slippery, see: {}".format(subzero_temp))


if __name__ == "__main__":
    # Set the configs, create a new Digital Twin Instance and register file structure
    # This config is generated when registering a client application on the platform
    # Make sure that Kafka and GOST are up and running before starting the platform
    config = {"client_name": "client",
              "system": "cz.icecars.iot4cps-wp5-CarFleet.Car1",
              "gost_servers": "localhost:8082",
              "kafka_bootstrap_servers": "localhost:9092"}
    client = DigitalTwinClient(**config)
    client.logger.info("Main: Starting client.")
    client.register(instance_file=INSTANCES)  # Register new instances could be outsourced to the platform
    client.subscribe(subscription_file=SUBSCRIPTIONS)  # Subscribe to datastreams

    # Create an instance of the CarSimulator that simulates a car driving on different tracks through Salzburg
    car = CarSimulator(track_id=1, time_factor=100, speed=30, cautiousness=1,
                       temp_day_amplitude=4, temp_year_amplitude=-4, temp_average=3, seed=1)
    client.logger.info("Main: Created instance of CarSimulator.")

    client.logger.info("Main: Starting producer and consumer threads.")
    halt_event = threading.Event()

    # Create and start the receiver Thread that consumes data via the client
    consumer = threading.Thread(target=consume_metrics)
    consumer.start()
    # Create and start the receiver Thread that publishes data via the client
    producer = threading.Thread(target=produce_metrics, kwargs=({"interval": 10}))
    producer.start()

    # set halt signal to stop the threads if a KeyboardInterrupt occurs
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        client.logger.info("Main: Sent halt signal to producer and consumer.")
        halt_event.set()
        # wait for the threads to get finished (can take about the timeout duration)
        producer.join()
        consumer.join()
        client.logger.info("Main: Stopped the demo applications.")
        client.disconnect()
