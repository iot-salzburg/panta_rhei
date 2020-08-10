#!/usr/bin/env python3

"""This is a script to demonstrate an exactly-once time-series filtering that is based on joins using
 the local stream buffering algorithm with Apache Kafka.

It consumes all metrics from 'cz.icecars.iot4cps-wp5-CarFleet.Car1.int' and forwards it to
'cz.icecars.iot4cps-wp5-CarFleet.Car2.ext' only iff the relative position between both cars is below a given threshold.


A join rate of around 15000 time-series joins per second was reached with a exactly-once semantic for
the consume-join-produce using Apache Kafka.

Don't forget to start the demo consumers in in advance in order to produce records into the Kafka topic.
"""

import time
import json
import math
import uuid

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
MAX_PROXIMITY = 10
VERBOSE = True

print(f"Starting the time-series join on topic '{KAFKA_TOPIC_IN_1}'")


# Create a kafka producer and consumer instance and subscribe to the topics
kafka_consumer = Consumer({
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': f"time-series-joiner_{uuid.uuid4()}",
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False,
    'enable.auto.offset.store': False
})
kafka_consumer.subscribe([KAFKA_TOPIC_IN_1, KAFKA_TOPIC_IN_2])
# kafka_consumer.assign([TopicPartition(KAFKA_TOPIC_IN_1), TopicPartition(KAFKA_TOPIC_IN_2)])

# Create a Kafka producer
kafka_producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
                           "transactional.id": 'eos-transactions.py'})
# Initialize producer transaction.
kafka_producer.init_transactions()
# Start producer transaction.
kafka_producer.begin_transaction()


class Counter:
    """
    A counter class that is used to count the number of joins
    """
    def __init__(self):
        self.cnt = 0

    def increment(self):
        self.cnt += 1

    def get(self):
        return self.cnt


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
        d2 = 0
        d2 += (record_left.get("longitude") - record_right.get("longitude"))**2
        d2 += (record_left.get("latitude") - record_right.get("latitude"))**2
    except (KeyError, TypeError, ArithmeticError) as e:
        print(f"WARNING, error while joining streams: {e}")
        print(record_left)
        print(record_right)
        return None

    if d2 < MAX_PROXIMITY**2:
        record_dict = dict({"thing": record_left.get("thing"), "quantity": record_left.get("quantity"),
                            "result": record_left.get_result(),
                            "timestamp": (record_left.get_time() + record_right.get_time()) / 2,
                            "meta": record_left.get_metadata()})
        # produce a Kafka message, the delivery report callback, the key must be thing + quantity
        kafka_producer.produce(KAFKA_TOPIC_OUT, json.dumps(record_dict).encode('utf-8'),
                               key=f"{record_dict.get('thing')}.{record_dict.get('quantity')}".encode('utf-8'),
                               callback=delivery_report)
        cnt_out.increment()

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
    else:
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
    stream_buffer = StreamBuffer(instant_emit=True, left="Car1", right="vaTorque_C11",
                                 buffer_results=True, delta_time=1,
                                 verbose=VERBOSE, join_function=join_fct, commit_function=commit_fct)

    cnt_left = 0
    cnt_right = 0
    cnt_out = Counter()
    st0 = ts_stop = None
    try:
        while True:
            msg = kafka_consumer.poll(0.1)

            # if there is no msg within a second, continue
            if msg is None:
                continue
            elif msg.error():
                raise Exception("Consumer error: {}".format(msg.error()))
            elif st0 is None:
                st0 = time.time()
                print("Start the count clock")

            record_json = json.loads(msg.value().decode('utf-8'))
            if VERBOSE:
                print(f"Received new record: {record_json}")

            # create a Record from the json
            record = Record(
                thing=record_json.get("thing"),
                quantity=record_json.get("quantity"),
                timestamp=record_json.get("phenomenonTime"),
                result=record_json.get("result"),
                topic=msg.topic(), partition=msg.partition(), offset=msg.offset(),
                longitude=record_json.get("longitude"),
                latitude=record_json.get("latitude"),
                attitude=record_json.get("attitude"))

            # ingest the record into the StreamBuffer instance, instant emit
            if msg.topic() == KAFKA_TOPIC_IN_1:  # Car1
                stream_buffer.ingest_left(record)  # with instant emit
                cnt_left += 1
            elif msg.topic() == KAFKA_TOPIC_IN_2:  # Car2
                stream_buffer.ingest_right(record)
                cnt_right += 1

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

        print(f"\nRecords in |{KAFKA_TOPIC_OUT}| = {cnt_out.get()}, "
              f"|{KAFKA_TOPIC_IN_1}| = {cnt_left}, |{KAFKA_TOPIC_IN_2}| = {cnt_right}.")
        print(f"Joined time-series {ts_stop - st0:.5g} s long, "
              f"that are {cnt_out.get() / (ts_stop - st0):.6g} joins per second.")
