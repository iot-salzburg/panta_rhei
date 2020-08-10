#!/usr/bin/env python3
# Tester for the join-algorithm in local_stream_buffer.

import sys
import time
import random

try:
    from .local_stream_buffer import Record, StreamBuffer
except ImportError:
    from local_stream_buffer import Record, StreamBuffer


def join_fct(record_left, record_right):
    """
    Blueprint for the join function, takes two records and merges them using the defined routine.
    :param record_left: Record 
        Record that is joined as left join partner
    :param record_right: Record 
        Record that is joined as right join partner
    :return: Record
        the resulting record from the join of both partners
    """
    record = Record(quantity="t",
                    result=record_left.get_result() * record_right.get_result(),
                    timestamp=(record_left.get_time() + record_right.get_time()) / 2)
    # here, the resulting record can be produced to e.g. Apache Kafka or a pipeline
    return record


def test_one_one():
    ts = time.time()

    # create an instance of the StreamBuffer class
    stream_buffer = StreamBuffer(instant_emit=True, delta_time=sys.maxsize, left="r", buffer_results=True,
                                 verbose=True)

    # create Queues to store the input streams
    events_r = list()
    events_s = list()

    # Fill the input_stream with randomized Records
    N = 100
    random.seed(0)
    event_order = ["r", "s"] * int(N / 2)
    start_time = 1600000000
    for i in range(len(event_order)):
        if event_order[i] == "r":
            events_r.append(Record(timestamp=i + start_time, quantity=event_order[i], result=random.random()))
        elif event_order[i] == "s":
            events_s.append(Record(timestamp=i + start_time, quantity=event_order[i], result=random.random()))

    ingestion_order = ["r", "s"] * int(N/2)            # works
    n_r = n_s = 0
    for i in range(N):
        # decide based on the ingestion order which stream record is forwarded
        # store as dict of KafkaRecords and a flag whether it was already joined as older sibling
        if ingestion_order[i] == "r":
            # receive the first record from the event stream
            stream_buffer.ingest_left(events_r[n_r])  # instant emit
            n_r += 1
        elif ingestion_order[i] == "s":
            # receive the first record from the event stream
            stream_buffer.ingest_right(events_s[n_s])
            n_s += 1

    # print("\nRecords in buffer r:")
    # for rec in stream_buffer.buffer_left:
    #     print(rec)
    # print("Records in buffer s:")
    # for rec in stream_buffer.buffer_right:
    #     print(rec)
    # print("Merged records in buffer t:")
    events_t = stream_buffer.fetch_results()
    # for rec in events_t:
    #     print(rec)

    print(f"Join time-series with |r| = {n_r}, |s| = {n_s}.")
    print(f"joined {len(events_t)} tuples in {time.time() - ts} s.")
    assert len(events_t) == 99


def test_five_five():
    # create an instance of the StreamBuffer class
    stream_buffer = StreamBuffer(instant_emit=True, delta_time=sys.maxsize, left="r", buffer_results=True,
                                 verbose=True)

    # Test Settings:
    # Create Queues to store the input streams
    events_r = list()
    events_s = list()

    # Fill the input_stream with randomized
    N = 20
    random.seed(0)
    event_order = (["r"] * 5 + ["s"] * 5) * int(N / 10)
    start_time = 1600000000

    for i in range(len(event_order)):
        if event_order[i] == "r":
            events_r.append(Record(timestamp=i + start_time, quantity=event_order[i], result=random.random()))
        elif event_order[i] == "s":
            events_s.append(Record(timestamp=i + start_time, quantity=event_order[i], result=random.random()))

    ingestion_order = (["r"] * 5 + ["s"] * 5) * N
    n_r = n_s = 0
    ts = time.time()
    for i in range(N):
        # decide based on the ingestion order which stream record is forwarded
        # store as dict of KafkaRecords and a flag whether it was already joined as older sibling
        if ingestion_order[i] == "r":
            # receive the first record from the event stream
            stream_buffer.ingest_left(events_r[n_r])  # instant emit
            n_r += 1
        elif ingestion_order[i] == "s":
            # receive the first record from the event stream
            stream_buffer.ingest_right(events_s[n_s])
            n_s += 1

    events_t = stream_buffer.fetch_results()

    print(f"Join time-series with |r| = {n_r}, |s| = {n_s}.")
    print(f"joined {len(events_t)} tuples in {time.time() - ts} s.")
    assert len(events_t) == 23


def test_five_five_many():

    # create an instance of the StreamBuffer class
    stream_buffer = StreamBuffer(instant_emit=True, delta_time=sys.maxsize, left="r", buffer_results=True,
                                 verbose=False)

    # Test Settings:
    # Create Queues to store the input streams
    events_r = list()
    events_s = list()

    # Fill the input_stream with randomized
    N = 100_000
    random.seed(0)
    event_order = (["r"] * 5 + ["s"] * 5) * int(N / 10)
    start_time = 1600000000

    for i in range(len(event_order)):
        if event_order[i] == "r":
            events_r.append(Record(timestamp=i + start_time, quantity=event_order[i], result=random.random()))
        elif event_order[i] == "s":
            events_s.append(Record(timestamp=i + start_time, quantity=event_order[i], result=random.random()))

    ingestion_order = (["r"] * 5 + ["s"] * 5) * int(N/10)
    n_r = 0
    n_s = 0
    ts = time.time()
    for i in range(N):
        # decide based on the ingestion order which stream record is forwarded
        # store as dict of KafkaRecords and a flag whether it was already joined as older sibling
        if ingestion_order[i] == "r":
            # receive the first record from the event stream
            stream_buffer.ingest_left(events_r[n_r])  # instant emit
            n_r += 1
        elif ingestion_order[i] == "s":
            # receive the first record from the event stream
            stream_buffer.ingest_right(events_s[n_s])
            n_s += 1

    events_t = stream_buffer.fetch_results()
    stop_time = time.time()

    print(f"Join time-series with |r| = {n_r}, |s| = {n_s}.")
    print(f"joined {len(events_t)} tuples in {time.time() - ts} s.")
    print(f"that are {int(len(events_t)/(time.time() - ts))} joins per second.")
    assert len(events_t) == 179987
    assert stop_time - ts < 6


def test_unordered():
    # create an instance of the StreamBuffer class
    stream_buffer = StreamBuffer(instant_emit=True, delta_time=sys.maxsize, left="r", buffer_results=True,
                                 verbose=True)

    # Fill the input_stream with randomized
    random.seed(0)
    start_time = 1600000000

    # Test Settings:
    # Create Queues to store the input records
    events_r = list()
    for i in range(10):
        events_r.append(Record(timestamp=i + start_time, quantity="r", result=random.random()))

    ts = time.time()
    # first ingest all Records into R, then all into s
    for event in events_r:
        stream_buffer.ingest_left(event)  # instant emit

    print("Ingest Records into s.")
    stream_buffer.ingest_right(Record(timestamp=start_time - 0.5, quantity="s", result=random.random()))
    stream_buffer.ingest_right(Record(timestamp=start_time + 0.5, quantity="s", result=random.random()))
    stream_buffer.ingest_right(Record(timestamp=start_time + 5.5, quantity="s", result=random.random()))
    stream_buffer.ingest_right(Record(timestamp=start_time + 9.5, quantity="s", result=random.random()))

    events_t = stream_buffer.fetch_results()

    print(f"Join time-series with |r| = {len(events_r)}, |s| = {4}.")
    print(f"joined {len(events_t)} tuples in {time.time() - ts} s.")
    if time.time() - ts > 1e-3:
        print(f"that are {int(len(events_t)/(time.time() - ts))} joins per second.")
    assert len(events_t) == 20
    d = {'r.quantity': 'r', 'r.phenomenonTime': 1600000006, 'r.result': 0.7837985890347726,
         's.quantity': 's', 's.phenomenonTime': 1600000005.5, 's.result': 0.28183784439970383}
    assert d in events_t


def test_randomized():
    # create an instance of the StreamBuffer class
    stream_buffer = StreamBuffer(instant_emit=True, delta_time=sys.maxsize, left="r", buffer_results=True,
                                 verbose=True)

    # Test Settings:
    # Create Queues to store the input streams
    events_r = list()
    events_s = list()

    # Fill the input_stream with randomized
    n_r = n_s = 10
    random.seed(0)
    start_time = 1600000000
    phenomenon_time = start_time
    for i in range(n_r):
        phenomenon_time += random.random()
        events_r.append(Record(timestamp=phenomenon_time, quantity="r", result=random.random()))
    phenomenon_time = start_time
    for i in range(n_s):
        phenomenon_time += random.random()
        events_s.append(Record(timestamp=phenomenon_time, quantity="s", result=random.random()))

    ingestion_order = ["r"] * n_r + ["s"] * n_s
    random.shuffle(ingestion_order)

    n_r = n_s = 0
    ts = time.time()
    for quantity in ingestion_order:
        # decide based on the ingestion order which stream record is forwarded
        # store as dict of KafkaRecords and a flag whether it was already joined as older sibling
        if quantity == "r":
            # receive the first record from the event stream
            stream_buffer.ingest_left(events_r[n_r])  # instant emit
            n_r += 1
        elif quantity == "s":
            # receive the first record from the event stream
            stream_buffer.ingest_right(events_s[n_s])
            n_s += 1

    events_t = stream_buffer.fetch_results()

    print(f"Join time-series with |r| = {n_r}, |s| = {n_s}.")
    print(f"joined {len(events_t)} tuples in {time.time() - ts} s.")
    assert len(events_t) == 20


def test_randomized_many():
    # create an instance of the StreamBuffer class
    stream_buffer = StreamBuffer(instant_emit=True, delta_time=sys.maxsize, left="r", buffer_results=True,
                                 verbose=False)

    # Test Settings:
    # Create Queues to store the input streams
    events_r = list()
    events_s = list()

    # Fill the input_stream with randomized
    n_r = n_s = 10_000
    random.seed(0)
    start_time = 1600000000
    phenomenon_time = start_time
    for i in range(n_r):
        phenomenon_time += random.random()
        events_r.append(Record(timestamp=phenomenon_time, quantity="r", result=random.random()))
    phenomenon_time = start_time
    for i in range(n_s):
        phenomenon_time += random.random()
        events_s.append(Record(timestamp=phenomenon_time, quantity="s", result=random.random()))

    ingestion_order = ["r"] * n_r + ["s"] * n_s
    random.shuffle(ingestion_order)

    n_r = n_s = 0
    ts = time.time()
    for quantity in ingestion_order:
        # decide based on the ingestion order which stream record is forwarded
        # store as dict of KafkaRecords and a flag whether it was already joined as older sibling
        if quantity == "r":
            # receive the first record from the event stream
            stream_buffer.ingest_left(events_r[n_r])  # instant emit
            n_r += 1
        elif quantity == "s":
            # receive the first record from the event stream
            stream_buffer.ingest_right(events_s[n_s])
            n_s += 1

    events_t = stream_buffer.fetch_results()
    stop_time = time.time()

    print(f"Join time-series with |r| = {n_r}, |s| = {n_s}.")
    print(f"joined {len(events_t)} tuples in {time.time() - ts} s.")
    print(f"that are {int(len(events_t)/(time.time() - ts))} joins per second.")
    assert len(events_t) == 23041
    assert stop_time - ts < 1  # we got around 0.4 s


def test_delayed_many():
    imbalance = 100  # additional latency of stream s

    # create an instance of the StreamBuffer class
    stream_buffer = StreamBuffer(instant_emit=True, delta_time=sys.maxsize, left="r", buffer_results=True,
                                 verbose=False)

    # Test Settings:
    # Create Queues to store the input streams
    events_r = list()
    events_s = list()

    # Fill the input_stream with randomized
    N = 10_000
    random.seed(0)
    event_order = (["r"] * 5 + ["s"] * 5) * int(N/10)
    start_time = 1600000000

    for i in range(len(event_order)):
        if event_order[i] == "r":
            events_r.append(Record(timestamp=i + start_time, quantity=event_order[i], result=random.random()))
        elif event_order[i] == "s":
            events_s.append(Record(timestamp=i + start_time, quantity=event_order[i], result=random.random()))

    ingestion_order = ["r"] * imbalance + (["r"] * 5 + ["s"] * 5) * int(N/10)
    n_r = 0
    n_s = 0
    ts = time.time()
    while n_r < len(events_r) and n_s < len(events_s):
        # decide based on the ingestion order which stream record is forwarded
        # store as dict of KafkaRecords and a flag whether it was already joined as older sibling
        if ingestion_order[n_r+n_s] == "r":
            # receive the first record from the event stream
            stream_buffer.ingest_left(events_r[n_r])  # instant emit
            n_r += 1
        elif ingestion_order[n_r+n_s] == "s":
            # receive the first record from the event stream
            stream_buffer.ingest_right(events_s[n_s])
            n_s += 1

    events_t = stream_buffer.fetch_results()

    print(f"Join time-series with |r| = {n_r}, |s| = {n_s}.")
    print(f"joined {len(events_t)} tuples in {time.time() - ts} s.")
    print(f"that are {int(len(events_t)/(time.time() - ts))} joins per second.")
    assert len(events_t) == 13702
    assert time.time() - ts < 1  # we got around 0.2 s


def test_timeout_five_five():
    # create an instance of the StreamBuffer class
    stream_buffer = StreamBuffer(instant_emit=True, delta_time=3, left="r", buffer_results=True,
                                 verbose=True)

    # Test Settings:
    # Create Queues to store the input streams
    events_r = list()
    events_s = list()

    # Fill the input_stream with randomized
    N = 20
    random.seed(0)
    event_order = (["r"] * 5 + ["s"] * 5) * int(N / 10)
    start_time = 1600000000

    for i in range(len(event_order)):
        if event_order[i] == "r":
            events_r.append(Record(timestamp=i + start_time, quantity=event_order[i], result=random.random()))
        elif event_order[i] == "s":
            events_s.append(Record(timestamp=i + start_time, quantity=event_order[i], result=random.random()))

    ingestion_order = (["r"] * 5 + ["s"] * 5) * N
    n_r = n_s = 0
    ts = time.time()
    for i in range(N):
        # decide based on the ingestion order which stream record is forwarded
        # store as dict of KafkaRecords and a flag whether it was already joined as older sibling
        if ingestion_order[i] == "r":
            # receive the first record from the event stream
            stream_buffer.ingest_left(events_r[n_r])  # instant emit
            n_r += 1
        elif ingestion_order[i] == "s":
            # receive the first record from the event stream
            stream_buffer.ingest_right(events_s[n_s])
            n_s += 1

    events_t = stream_buffer.fetch_results()

    print(f"Join time-series with |r| = {n_r}, |s| = {n_s}.")
    print(f"joined {len(events_t)} tuples in {time.time() - ts} s.")
    assert len(events_t) == 13


def test_timeout_randomized():
    # create an instance of the StreamBuffer class with a delta_time of 0.5 seconds.
    stream_buffer = StreamBuffer(instant_emit=True, delta_time=0.5, left="r", buffer_results=True,
                                 verbose=True)

    # Test Settings:
    # Create Queues to store the input streams
    events_r = list()
    events_s = list()

    # Fill the input_stream with randomized
    n_r = n_s = 10
    random.seed(0)
    start_time = 1600000000
    phenomenon_time = start_time
    for i in range(n_r):
        phenomenon_time += random.random()
        events_r.append(Record(timestamp=phenomenon_time, quantity="r", result=random.random()))
    phenomenon_time = start_time
    for i in range(n_s):
        phenomenon_time += random.random()
        events_s.append(Record(timestamp=phenomenon_time, quantity="s", result=random.random()))

    ingestion_order = ["r"] * n_r + ["s"] * n_s
    random.shuffle(ingestion_order)

    n_r = n_s = 0
    ts = time.time()
    for quantity in ingestion_order:
        # decide based on the ingestion order which stream record is forwarded
        # store as dict of KafkaRecords and a flag whether it was already joined as older sibling
        if quantity == "r":
            # receive the first record from the event stream
            stream_buffer.ingest_left(events_r[n_r])  # instant emit
            n_r += 1
        elif quantity == "s":
            # receive the first record from the event stream
            stream_buffer.ingest_right(events_s[n_s])
            n_s += 1

    events_t = stream_buffer.fetch_results()

    print(f"Join time-series with |r| = {n_r}, |s| = {n_s}.")
    print(f"joined {len(events_t)} tuples in {time.time() - ts} s.")
    assert len(events_t) == 16


# to profile via cProfile, run it normally with a python interpreter
if __name__ == "__main__":
    import cProfile

    pr = cProfile.Profile()
    pr.enable()

    # test ordered ingestion
    test_one_one()
    test_five_five()

    print("\n #############################\n")
    print("Testing unordered ingestion:")
    test_unordered()
    test_randomized()

    # test unordered ingestion
    print("\n #############################\n")
    print("Performance tests")
    test_five_five_many()
    test_randomized_many()
    test_delayed_many()

    print("\n #############################\n")
    print("Timeout tests")
    test_timeout_five_five()
    test_timeout_randomized()

    pr.disable()
    # after your program ends
    pr.print_stats(sort="tottime")
    # Back in outer section of code
    # pr.dump_stats('tester_profile.pstat')
