#!/usr/bin/env python3

"""This is a script to demonstrate an exactly-once time-series filtering that is based on joins using
 the local stream buffering algorithm with Apache Kafka.

It consumes all metrics from 'cz.icecars.iot4cps-wp5-CarFleet.Car1.int' and forwards it to
'cz.icecars.iot4cps-wp5-CarFleet.Car2.ext' only iff the relative position between both cars is below a given threshold.


A join rate of around 15000 time-series joins per second was reached with a exactly-once semantic for
the consume-join-produce using Apache Kafka.

Don't forget to start the demo producers in in advance in order to produce records into the Kafka topic.
"""
import time
import json
import math
import pytz
from datetime import datetime

from confluent_kafka import Producer, Consumer, TopicPartition

try:
    from .LocalStreamBuffer.local_stream_buffer import Record, StreamBuffer, record_from_dict
except (ModuleNotFoundError, ImportError):
    # noinspection PyUnresolvedReferences
    from LocalStreamBuffer.local_stream_buffer import Record, StreamBuffer, record_from_dict

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"  # of the form 'mybroker1,mybroker2'
KAFKA_TOPIC_IN_1 = "cz.icecars.iot4cps-wp5-CarFleet.Car1.int"
KAFKA_TOPIC_IN_2 = "cz.icecars.iot4cps-wp5-CarFleet.Car2.int"
KAFKA_TOPIC_OUT = "cz.icecars.iot4cps-wp5-CarFleet.Car2.ext"
# QUANTITIES = ["actSpeed_C11", "vaTorque_C11"]
# RES_QUANTITY = "vaPower_C11"
ADDITIONAL_ATTRIBUTES = "longitude,latitude,attitude"
MAX_PROXIMITY = 15
VERBOSE = True

print(f"Starting the time-series join on topic '{KAFKA_TOPIC_IN_1}'")


# Create a kafka producer and consumer instance and subscribe to the topics
kafka_consumer = Consumer({
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': f"TS-joiner_{__name__}_2",
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False,
    'enable.auto.offset.store': False
})
kafka_consumer.subscribe([KAFKA_TOPIC_IN_1, KAFKA_TOPIC_IN_2])
kafka_consumer.assign([TopicPartition(KAFKA_TOPIC_IN_1), TopicPartition(KAFKA_TOPIC_IN_2)])

# Create a Kafka producer
kafka_producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
                           "transactional.id": 'eos-transactions.py'})
# Initialize producer transaction.
kafka_producer.init_transactions()
# Start producer transaction.
kafka_producer.begin_transaction()


def delivery_report(err, msg):
    """ Delivery callback for Kafka Produce. Called once for each message produced to indicate delivery result.
        Triggered by poll() or flush(). """
    if err is not None:
        print('Message delivery failed: {}'.format(err))
    else:
        if VERBOSE:
            # get the sent message using msg.value()
            print(f"Message '{msg.key().decode('utf-8')}'  \tdelivered to topic '{msg.topic()}' [{msg.partition()}].")


# define customized function for join
def join_fct(record_left, record_right):
    try:
        # calculate the distance based on a spherical approach (correct even for large distances)
        k = math.pi/180
        distance = 6378.388 * math.acos(
            math.sin(k * record_left.get("latitude")) * math.sin(k * record_right.get("latitude")) +
            math.cos(k * record_left.get("latitude")) * math.cos(k * record_right.get("latitude")) *
            math.cos(k * (record_right.get("longitude") - record_left.get("longitude"))))
        # # a better understandable approach that is correct for small distances is this:
        # dx = 111.3 * math.cos(k * (record_left.get("latitude") + record_right.get("latitude")) / 2) * \
        #      (record_right.get("longitude") - record_left.get("longitude"))
        # dy = 111.3 * (record_left.get("latitude") - record_right.get("latitude"))
        # # distance = math.sqrt(dx * dx + dy * dy)
        # print(f"Distances: {distance} -- {math.sqrt(dx * dx + dy * dy)}")
        # # more information for calculating distances based on coordinates are here: www.kompf.de/gps/distcalc.html
    except (KeyError, TypeError) as e:
        print(f"WARNING, error while joining streams: {e}")
        print(record_left)
        print(record_right)
        return None

    if distance < MAX_PROXIMITY:
        record_dict = dict({"thing": record_left.get("thing"), "quantity": record_left.get("quantity"),
                            "result": record_left.get_result(),
                            "phenomenonTime": (record_left.get_time() + record_right.get_time()) / 2,
                            "resultTime": datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat(),
                            "longitude": record_left.get("longitude"),
                            "latitude": record_left.get("latitude"),
                            "attitude": record_left.get("attitude"),
                            "rel_distance": distance})
        # produce a Kafka message, the delivery report callback, the key must be thing + quantity
        kafka_producer.produce(KAFKA_TOPIC_OUT, json.dumps(record_dict).encode('utf-8'),
                               key=f"{record_dict.get('thing')}.{record_dict.get('quantity')}".encode('utf-8'),
                               callback=delivery_report)

        # Send the consumer's position to transaction to commit them along with the transaction, committing both
        # input and outputs in the same transaction is what provides EOS.
        kafka_producer.send_offsets_to_transaction(
            kafka_consumer.position(kafka_consumer.assignment()),
            kafka_consumer.consumer_group_metadata())
        # Commit the transaction
        kafka_producer.commit_transaction()
        # Begin new transaction
        kafka_producer.begin_transaction()

        return record_from_dict(record_dict)
    elif VERBOSE:
        print(f"The relative distance of {distance} km is higher than the maximum of {MAX_PROXIMITY} km.")
        return None


def commit_fct(record_to_commit):
    # Test the commit: Uncomment commit() in order to consume and join always the same Records.
    # It is of importance that the
    rec = record_to_commit.data.get("record")
    # Commit message’s offset + 1
    kafka_consumer.commit(offsets=[TopicPartition(topic=rec.get("topic"),
                                                  partition=rec.get("partition"),
                                                  offset=rec.get("offset") + 1)])  # commit the next (n+1) offset


if __name__ == "__main__":
    import pdb

    print("Create a StreamBuffer instance.")
    stream_buffer = StreamBuffer(instant_emit=True, left="Car1", right="Car2",
                                 buffer_results=False, delta_time=10,
                                 verbose=VERBOSE, join_function=join_fct, commit_function=commit_fct)

    st0 = time.time()
    try:
        while True:
            msg = kafka_consumer.poll(0.1)

            # if there is no msg within a second, continue
            if msg is None:
                continue
            elif msg.error():
                raise Exception("Consumer error: {}".format(msg.error()))

            record_json = json.loads(msg.value().decode('utf-8'))
            if VERBOSE:
                print(f"Received new record: {record_json}")

            # create a Record from the json
            additional_attributes = {att: record_json.get(att.strip()) for att in ADDITIONAL_ATTRIBUTES.split(",")
                                     if att != ""}
            record = Record(
                thing=record_json.get("thing"),
                quantity=record_json.get("quantity"),
                timestamp=record_json.get("phenomenonTime"),
                result=record_json.get("result"),
                topic=msg.topic(), partition=msg.partition(), offset=msg.offset(),
                **additional_attributes)

            # ingest the record into the StreamBuffer instance, instant emit
            if record.get("topic") == KAFKA_TOPIC_IN_1:  # Car1
                stream_buffer.ingest_left(record)  # with instant emit
            elif record.get("topic") == KAFKA_TOPIC_IN_2:  # Car2
                stream_buffer.ingest_right(record)

    except KeyboardInterrupt:
        print("Gracefully stopping")
    finally:
        ts_stop = time.time()

        # commit processed message offsets to the transaction
        kafka_producer.send_offsets_to_transaction(
            kafka_consumer.position(kafka_consumer.assignment()),
            kafka_consumer.consumer_group_metadata())
        # commit transaction
        kafka_producer.commit_transaction()
        # Leave group and commit offsets
        kafka_consumer.close()

        print(f"\nRecords in |{KAFKA_TOPIC_OUT}| = {stream_buffer.get_join_counter()}, "
              f"|{KAFKA_TOPIC_IN_1}| = {stream_buffer.get_left_counter()}, "
              f"|{KAFKA_TOPIC_IN_2}| = {stream_buffer.get_right_counter()}.")
        print(f"Joined time-series {ts_stop - st0:.5g} s long, "
              f"this are {stream_buffer.get_join_counter() / (ts_stop - st0):.6g} joins per second.")
