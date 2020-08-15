#!/usr/bin/env python3

"""This file customizes the general stream_join_engine.py by configuring important constants and functions.
Therefore, name the following constants and the functions 'ingest_fct()' and 'on_join()' More info of how
to define the functions can be found in their respective docstring.
"""

import math

# Kafka configuration
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"  # kafka nodes of the form 'mybroker1,mybroker2'
# declare one or two Kafka Topics to consume from
KAFKA_TOPICS_IN = ["cz.icecars.iot4cps-wp5-CarFleet.Car1.int", "cz.icecars.iot4cps-wp5-CarFleet.Car2.int"]
KAFKA_TOPIC_OUT = "cz.icecars.iot4cps-wp5-CarFleet.Car2.ext"

# join configuration
TIME_DELTA = None  # int, float or None: Maximal time difference between two Records being joined
ADDITIONAL_ATTRIBUTES = "longitude,latitude,attitude"  # optional attributes in observation records "att1,att2,..."
USE_ISO_TIMESTAMPS = True  # boolean timestamp format of the resulting records, ISO 8601 or unix timestamp if False
MAX_BATCH_SIZE = 100  # consume up to this number messages at once
TRANSACTION_TIME = 1  # time interval to commit the transactions
VERBOSE = True


# ingest routine for record into the StreamBuffer instance
def ingest_fct(record, stream_buffer):
    """Ingestion function. Defines how a record is ingested into the stream_buffer, i.e., specifies under which
    constraints a record is ingested into the buffer's left or right buffer.

    Use the stream_buffer methods 'ingest_left(record)' and 'ingest_right(record)', as well as the record's getter
    functions:
      * 'get_quantity()' get the quantity name if set
      * 'get("topic")' get Kafka's topic name
      * 'get("thing")' get the thing name if set

    :param record: Record
      Record instance defined in local_stream_buffer.py
    :param stream_buffer: LocalStreamBuffer
      Instance of the LocalStreamBuffer, allows to ingest left and right join partners, joins them automatically
    :return: None
    """
    # ingest into left buffer, iff the records was consumed from system Car 1
    if record.get("topic") == "cz.icecars.iot4cps-wp5-CarFleet.Car1.int":
        stream_buffer.ingest_left(record)  # with instant emit
    # ingest into left buffer, iff the records was consumed from system Car 2
    elif record.get("topic") == "cz.icecars.iot4cps-wp5-CarFleet.Car2.int":
        stream_buffer.ingest_right(record)


def on_join(record_left, record_right):
    """Procedure on a join event.
    This function customizes the behaviour on a join event. It receives two Records, one that is a left join partner
    and one right.
    :param record_left:
    :param record_right:
    :return: dictionary, None
      If no join should be done return None. Else, return a dictionary containing the mandatory keys "quantity",
      "result" and "phenomenonTime". It is allowed to use more keys.
    """
    # calculate the relative distance between the cars from the given GPC coordinates based on a spherical approach.
    # This solution is even correct for large distances. The distance is in kilometer.
    k = math.pi/180
    distance = 6378.388 * math.acos(
        math.sin(k * record_left.get("latitude")) * math.sin(k * record_right.get("latitude")) +
        math.cos(k * record_left.get("latitude")) * math.cos(k * record_right.get("latitude")) *
        math.cos(k * (record_right.get("longitude") - record_left.get("longitude"))))
    # # the above solution is for small distances similar than the one below, but the later is better understandable
    # dx = 111.3 * math.cos(k * (record_left.get("latitude") + record_right.get("latitude")) / 2) * \
    #      (record_right.get("longitude") - record_left.get("longitude"))
    # dy = 111.3 * (record_left.get("latitude") - record_right.get("latitude"))
    # # distance = math.sqrt(dx * dx + dy * dy)
    # print(f"Distances: {distance} -- {math.sqrt(dx * dx + dy * dy)}")
    # # more information for calculating distances based on coordinates are here: www.kompf.de/gps/distcalc.html

    if distance < 1.23:  # distance is lesser than the set distance in kilometers
        record_dict = dict({"thing": record_left.get("thing"),
                            "quantity": record_left.get("quantity"),
                            "result": record_left.get_result(),
                            "phenomenonTime": record_left.get_time(),
                            # often the mean is used: (record_left.get_time() + record_right.get_time()) / 2
                            "longitude": record_left.get("longitude"),
                            "latitude": record_left.get("latitude"),
                            "attitude": record_left.get("attitude"),
                            "rel_distance": distance})
        return record_dict

    elif VERBOSE:
        print(f"The relative distance of {distance:.3f} km between the cars exceeds the maximal allowed distance.")
        return None
