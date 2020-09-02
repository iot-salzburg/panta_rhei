#!/usr/bin/env python3

"""This engine enables to customize the stream joining very flexible by importing only few lines of code that
 define customized functionality. This framework ensures exactly-once time-series processing  that are based on joins
 using the local stream buffering algorithm with Apache Kafka.

Import constants and 'ingest_fct()' and 'on_join()' to customize the processing.

A join rate of around 15000 time-series joins per second is reached with a exactly-once semantic for
the consume-join-produce procedures using Apache Kafka.

Don't forget to start the demo producers in in advance in order to produce records into the Kafka topic.
"""

import os
import sys
import socket
import time
import json
from datetime import datetime

import pytz
from confluent_kafka import Producer, Consumer, TopicPartition

try:
    from .LocalStreamBuffer.local_stream_buffer import Record, StreamBuffer, record_from_dict
except (ModuleNotFoundError, ImportError):
    # noinspection PyUnresolvedReferences
    from LocalStreamBuffer.local_stream_buffer import Record, StreamBuffer, record_from_dict


def delivery_report(err, msg):
    """Delivery callback for Kafka Produce. Called once for each message produced to indicate delivery result.
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
        # create a record dictionary from both join partners
        record_dict = on_join(record_left, record_right)

        if record_dict is not None:
            # adapt two time fields of the record
            record_dict["processingTime"] = time.time()
            if USE_ISO_TIMESTAMPS:
                record_dict["phenomenonTime"] = to_iso_time(record_dict.get("phenomenonTime"))
                record_dict["processingTime"] = to_iso_time(record_dict.get("processingTime"))

            # produce a Kafka message, the delivery report callback, the key must be thing + quantity
            kafka_producer.produce(f"{TARGET_SYSTEM}.ext", json.dumps(record_dict).encode('utf-8'),
                                   key=f"{record_dict.get('thing')}.{record_dict.get('quantity')}".encode('utf-8'),
                                   callback=delivery_report)

    except Exception as ex:  # this block catches possible errors in custom code
        print(f"WARNING, Exception while joining streams: {ex}")
        print(f"left record: {record_left}")
        print(f"right record: {record_right}")
        raise ex


def commit_transaction(verbose=False, commit_time=time.time()):
    # Send the consumer's position to transaction to commit them along with the transaction, committing both
    # input and outputs in the same transaction is what provides EOS.
    kafka_producer.send_offsets_to_transaction(
        kafka_consumer.position(kafka_consumer.assignment()),
        kafka_consumer.consumer_group_metadata())
    # Commit the transaction
    kafka_producer.commit_transaction()
    # Begin new transaction
    kafka_producer.begin_transaction()

    # commit the offset of the latest records that got obsolete in order to consume and join always the same Records.
    latest_records = []
    if stream_buffer.last_removed_left:
        latest_records.append(stream_buffer.last_removed_left.data.get("record"))
    if stream_buffer.last_removed_right:
        latest_records.append(stream_buffer.last_removed_right.data.get("record"))

    # Commit message’s offset + 1
    kafka_consumer.commit(offsets=[TopicPartition(topic=rec.get("topic"),
                                                  partition=rec.get("partition"),
                                                  offset=rec.get("offset") + 1)  # commit the next (n+1) offset
                                   for rec in latest_records])
    if verbose:
        print(f"Committed to latest offsets at {commit_time:.6f}.")


def to_iso_time(timestamp):
    """Receives an arbitrary timestamp in UTC format (most likely in unix timestamp) and returns it as ISO-format.

    :param timestamp: arbitrary timestamp
    :return: timestamp in ISO 8601 and UTC timezone
    """
    if isinstance(timestamp, (int, float)):
        return datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.UTC).isoformat()
    if timestamp is None:
        return datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat()
    return timestamp


if __name__ == "__main__":
    # Import the original, or if used in Docker the overwritten custom functions
    try:
        from .customization.custom_fct import *
    except (ModuleNotFoundError, ImportError):
        # noinspection PyUnresolvedReferences
        from customization.custom_fct import *

    if "--use-env-config" in sys.argv:
        print(f"Load environment variables: {os.environ}")
        try:
            STREAM_NAME = os.environ["STREAM_NAME"]
            SOURCE_SYSTEMS = os.environ["SOURCE_SYSTEM"]
            TARGET_SYSTEM = os.environ["TARGET_SYSTEM"]
            GOST_SERVER = os.environ["GOST_SERVER"]
            KAFKA_BOOTSTRAP_SERVERS = os.environ["KAFKA_BOOTSTRAP_SERVERS"]
            FILTER_LOGIC = os.environ["FILTER_LOGIC"]
            # Execute the customization passed as filter logic to load necessary constants and function.
            exec(FILTER_LOGIC)
            _ = TIME_DELTA  # Check if it worked
        except Exception as e:
            print("Could not load config.")
            raise e

    print(f"Starting the stream join with the following configurations: "
          f"\n\tKAFKA_BOOTSTRAP_SERVERS: '{KAFKA_BOOTSTRAP_SERVERS}'"
          f"\n\tSTREAM_NAME: '{STREAM_NAME}'"
          f"\n\tSOURCE_SYSTEMS: '{SOURCE_SYSTEMS}'"
          f"\n\tTARGET_SYSTEM: '{TARGET_SYSTEM}'"
          f"\n\tTIME_DELTA: '{TIME_DELTA}'"
          f"\n\tADDITIONAL_ATTRIBUTES: '{ADDITIONAL_ATTRIBUTES}'")

    # Create a kafka producer and consumer instance and subscribe to the topics
    kafka_consumer = Consumer({
        'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
        'group.id': f"TS-joiner_{socket.gethostname()}_1",
        'auto.offset.reset': 'earliest',
        'enable.auto.commit': False,
        'enable.auto.offset.store': False
    })
    kafka_topics_in = [f"{sys}.int" for sys in SOURCE_SYSTEMS.split(",")]
    kafka_consumer.subscribe(kafka_topics_in)
    # kafka_consumer.assign([TopicPartition(topic, 0) for topic in kafka_topics_in])  # manually assign to an offset

    # Create a Kafka producer
    kafka_producer = Producer({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
                               "transactional.id": f'ms-stream-app_{SOURCE_SYSTEMS}_{STREAM_NAME}'})
    # Initialize producer transaction.
    kafka_producer.init_transactions()
    # Start producer transaction.
    kafka_producer.begin_transaction()

    print("Create a StreamBuffer instance.")
    stream_buffer = StreamBuffer(instant_emit=True, buffer_results=False,
                                 verbose=VERBOSE, join_function=join_fct)

    start_time = last_transaction_time = time.time()
    n_none_polls = 0
    started = False
    try:
        print("Start the Stream Processing.")
        while True:
            # Here, a small timeout can be used, as the commit is done manually and based on TRANSACTION_TIME
            msgs = kafka_consumer.consume(num_messages=MAX_BATCH_SIZE, timeout=0.2)

            # iterate over each message that was consumed
            for msg in msgs:
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

                ingest_fct(record, stream_buffer)

            # commit the transaction every TRANSACTION_TIME
            cur_time = time.time()
            if cur_time >= last_transaction_time + TRANSACTION_TIME:
                last_transaction_time = cur_time
                commit_transaction(verbose=VERBOSE, commit_time=last_transaction_time)

    except KeyboardInterrupt:
        print("Gracefully stopping")
    finally:
        stop_time = time.time()

        # commit processed message offsets to the transaction
        kafka_producer.send_offsets_to_transaction(
            kafka_consumer.position(kafka_consumer.assignment()),
            kafka_consumer.consumer_group_metadata())
        # commit transaction
        kafka_producer.commit_transaction()
        # Leave group and commit offsets
        kafka_consumer.close()

        print(f"\nRecords in |{TARGET_SYSTEM}| = {stream_buffer.get_join_counter()}, "
              f"|left buffer| = {stream_buffer.get_left_counter()}, "
              f"|right buffer| = {stream_buffer.get_right_counter()}.")
    if start_time != stop_time:
        print(f"Joined time-series {stop_time - start_time:.6f} s long, "
              f"that are {stream_buffer.get_join_counter() / (stop_time - start_time):.2f} joins per second.")
