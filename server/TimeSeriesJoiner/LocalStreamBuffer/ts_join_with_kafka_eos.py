#!/usr/bin/env python3

"""This is a demo-script for exactly-once time-series joins of the local stream buffering algorithm with Apache Kafka.

It consumes from KAFKA_TOPIC_IN_1/2 the quantities 'vaTorque_C11' and 'actSpeed_C11', joins the time-series via the
LocalStreamBuffer method and produces the resulting 'vaPower_C11' to KAFKA_TOPIC_OUT.

A join rate of around 15000 time-series joins per second was reached with a exactly-once semantic for
the consume-join-produce using Apache Kafka.

Don't forget to start ../01_Simulator/simulatorToKafka.py in advance in order to produce records into the Kafka topic.
"""

import time
import json
import math

from confluent_kafka import Producer, Consumer, TopicPartition
import confluent_kafka.admin as kafka_admin

try:
    from .local_stream_buffer import Record, StreamBuffer, record_from_dict
except (ModuleNotFoundError, ImportError):
    # noinspection PyUnresolvedReferences
    from local_stream_buffer import Record, StreamBuffer, record_from_dict

KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"  # of the form 'mybroker1,mybroker2'
KAFKA_TOPIC_FROM = "machine.data"   # topic names
KAFKA_TOPIC_OUT = "machine.out"
QUANTITIES = ["actSpeed_C11", "vaTorque_C11"]
RES_QUANTITY = "vaPower_C11"
MAX_JOIN_CNT = 50  # None or a integer
VERBOSE = True

print(f"Starting the time-series join for {RES_QUANTITY}")

# Create a Kafka instances
k_admin_client = kafka_admin.AdminClient({'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS})

# Create a kafka producer and consumer instance and subscribe to the topics
kafka_consumer = Consumer({
    'bootstrap.servers': KAFKA_BOOTSTRAP_SERVERS,
    'group.id': "kafka-eof_2",
    'auto.offset.reset': 'earliest',
    'enable.auto.commit': False,
    'enable.auto.offset.store': False
})
kafka_consumer.subscribe([KAFKA_TOPIC_FROM])
kafka_consumer.assign([TopicPartition(KAFKA_TOPIC_FROM)])

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
    record_dict = dict({"thing": record_left.get("thing"), "quantity": RES_QUANTITY,
                        "result": (2 * math.pi / 60) * record_left.get_result() * record_right.get_result(),
                        "timestamp": (record_left.get_time() + record_right.get_time()) / 2})
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


def commit_fct(record_to_commit):
    # Test the commit: Uncomment commit() in order to consume and join always the same Records.
    # It is of importance that the
    rec = record_to_commit.data.get("record")
    # Commit message’s offset + 1
    kafka_consumer.commit(offsets=[TopicPartition(topic=rec.get("topic"),
                                                  partition=rec.get("partition"),
                                                  offset=rec.get("offset") + 1)])  # commit the next (n+1) offset


if __name__ == "__main__":
    print("Create a StreamBuffer instance.")
    stream_buffer = StreamBuffer(instant_emit=True, left="actSpeed_C11", right="vaTorque_C11",
                                 buffer_results=True, delta_time=1,
                                 verbose=VERBOSE, join_function=join_fct, commit_function=commit_fct)

    cnt_left = 0
    cnt_right = 0
    cnt_out = Counter()
    st0 = ts_stop = None
    while True:
        msg = kafka_consumer.poll(0.1)

        # if there is no msg within a second, continue
        if msg is None:
            if st0 is not None and time.time() - st0 > 5 + MAX_JOIN_CNT / 1000:
                print("  Break as there won't come enough messages.")
                ts_stop = time.time()
                break
            continue
        elif msg.error():
            raise Exception("Consumer error: {}".format(msg.error()))
        elif st0 is None:
            st0 = time.time()
            print("Start the count clock")

        record_json = json.loads(msg.value().decode('utf-8'))
        if VERBOSE:
            if record_json.get("quantity").endswith("_C11"):
                print(f"Received new record: {record_json}")

        # create a Record from the json
        record = Record(
            thing=record_json.get("thing"),
            quantity=record_json.get("quantity"),
            timestamp=record_json.get("phenomenonTime"),
            result=record_json.get("result"),
            topic=msg.topic(), partition=msg.partition(), offset=msg.offset())

        # ingest the record into the StreamBuffer instance, instant emit
        if record_json.get("quantity") == "actSpeed_C11":
            stream_buffer.ingest_left(record)  # with instant emit
            cnt_left += 1
        elif record_json.get("quantity") == "vaTorque_C11":
            stream_buffer.ingest_right(record)
            cnt_right += 1

        if MAX_JOIN_CNT is not None and cnt_out.get() >= MAX_JOIN_CNT:
            ts_stop = time.time()
            print("Reached the maximal join count, graceful stopping.")
            break

    # commit processed message offsets to the transaction
    kafka_producer.send_offsets_to_transaction(
        kafka_consumer.position(kafka_consumer.assignment()),
        kafka_consumer.consumer_group_metadata())
    # commit transaction
    kafka_producer.commit_transaction()
    # Leave group and commit offsets
    kafka_consumer.close()

    print(f"\nLength of |{RES_QUANTITY}| = {cnt_out.get()}, "
          f"|{QUANTITIES[0]}| = {cnt_left}, |{QUANTITIES[1]}| = {cnt_right}.")
    print(f"Joined time-series {ts_stop - st0:.5g} s long, "
          f"that are {cnt_out.get() / (ts_stop - st0):.6g} joins per second.")


# How to see if the exactly-once join processing works:

## Last rows after transactional write
# New ingest into 'vaTorque_C11' with timestamp: 1554096500.385
#  join case JR2:	 {phenomenonTime=1554096500.385, quantity=vaPower_C11, result=2273.8234297335903, meta={'kwargs': {'thing': 'R0815'}}}.
#  join case JS2:	 {phenomenonTime=1554096500.385, quantity=vaPower_C11, result=2273.8234297335903, meta={'kwargs': {'thing': 'R0815'}}}.
#   removing superseded record {phenomenonTime=1554096489.394, quantity=actSpeed_C11, result=619.5870535714286, meta={'thing': 'R0815', 'topic': 'test.machine.in.1', 'partition': 0, 'offset': 41}}, leader: {phenomenonTime=1554096500.385, quantity=vaTorque_C11, result=13.995000000000001, meta={'thing': 'R0815', 'topic': 'test.machine.in.2', 'partition': 0, 'offset': 46}}
# Received new record: {'phenomenonTime': 1554096501382, 'quantity': 'vaTorque_C11', 'thing': 'R0815', 'result': 15.397}
# New ingest into 'vaTorque_C11' with timestamp: 1554096501.382
#  join case JR2:	 {phenomenonTime=1554096501.382, quantity=vaPower_C11, result=2896.6111331147167, meta={'kwargs': {'thing': 'R0815'}}}.
#  join case JS2:	 {phenomenonTime=1554096501.382, quantity=vaPower_C11, result=2896.6111331147167, meta={'kwargs': {'thing': 'R0815'}}}.
#   removing superseded record {phenomenonTime=1554096500.385, quantity=actSpeed_C11, result=1551.5122767857142, meta={'thing': 'R0815', 'topic': 'test.machine.in.1', 'partition': 0, 'offset': 42}}, leader: {phenomenonTime=1554096501.382, quantity=vaTorque_C11, result=15.397, meta={'thing': 'R0815', 'topic': 'test.machine.in.2', 'partition': 0, 'offset': 47}}
# Reached the maximal join count, graceful stopping.
# Length of |vaPower_C11| = 51, |actSpeed_C11| = 64, |vaTorque_C11| = 48.
# Joined time-series 5.1076 s long, that are 9.98519 joins per second.

## Last rows after most of the records were commited
# New ingest into 'vaTorque_C11' with timestamp: 1554096490.394
# Received new record: {'phenomenonTime': 1554096491391, 'quantity': 'vaTorque_C11', 'thing': 'R0815', 'result': 11.962}
# New ingest into 'vaTorque_C11' with timestamp: 1554096491.391
# Received new record: {'phenomenonTime': 1554096492391, 'quantity': 'vaTorque_C11', 'thing': 'R0815', 'result': 11.565}
# New ingest into 'vaTorque_C11' with timestamp: 1554096492.391

# messages won't be consumed again after they were commited in the commit function and resulting join pairs won't be
# joined again.
