#!/usr/bin/env python3

# script to test the algorithm for the local stream buffering approach.
import sys
import time
import random

try:
    from .doublylinkedlist import Node, LinkedList
except ImportError:
    from doublylinkedlist import Node, LinkedList
    # import importlib
    # LinkedList = importlib.import_module('05_LocalStreamBuffer.doublylinkedlist.LinkedList')


# Record is a record as streamed via Kafka, each record contains a set of fixed attributes
def record_from_dict(record_dict):
    """Creates a Record from a record dictionary

    :param record_dict: dict
        a dictionary storing all the necessary attributes
    """
    quantity = record_dict.pop("quantity", None)
    timestamp = record_dict.pop("timestamp", None)
    phenomenon_time = record_dict.pop("phenomenonTime", None)
    result = record_dict.pop("result", None)
    record = Record(quantity, timestamp=timestamp, phenomenon_time=phenomenon_time, result=result, kwargs=record_dict)
    return record


class Record:
    """Time-Series Records of Measurements or Events"""

    def __init__(self, quantity, timestamp=None, phenomenon_time=None, result=None, **kwargs):
        """
        :param quantity: string
            specifies the observed property by an unique string identifier
        :param timestamp: int, float, str (iso-8601), optional
            point in time in the unix format in seconds (preferred, others will be parsed),
            only one of timestamp or phenomenonTime has to be set
        :param phenomenon_time:  int, float, str (iso-8601), optional
            point in time in the unix format in seconds (preferred, others will be parsed),
            only one of timestamp or phenomenonTime has to be set
        :param result: float, int, string, object, optional
            result value of the measurement of event, default = None
        :param kwargs:
            appends more arguments into class.meta
        """
        if timestamp is not None:
            self.phenomenonTime = self.extract_time(timestamp)
        elif phenomenon_time is not None:
            self.phenomenonTime = self.extract_time(phenomenon_time)
        else:
            raise Exception("Error, Either 'timestamp' or 'phenomenon_time' has to be set!")
        self.quantity = str(quantity)
        self.result = result
        self.metadata = kwargs

    def set_quantity(self, quantity):
        self.quantity = quantity

    def get_quantity(self):
        return self.quantity

    def get(self, attribute):
        return self.metadata.get(attribute)

    def extract_time(self, timestamp):
        """
        Recursively divides a timestamp by 1000 until the time is in seconds and not in ms, µs or ns
        :param timestamp: int, float, str (iso-8601)
            timestamp, a metric format is preferred
        :return: a unix timestamp that is normalized
        """
        if not isinstance(timestamp, (int, float)):
            import dateutil.parser
            return float(dateutil.parser.parse(timestamp).strftime("%s"))
        if timestamp >= 1e11:
            timestamp /= 1000
            return self.extract_time(timestamp)
        return timestamp

    def get_time(self):
        return self.phenomenonTime

    def get_result(self):
        return self.result

    def get_metadata(self):
        return self.metadata

    def __str__(self):
        """to String method

        :return: str
            A readable representation of the record
        """
        tail = f", meta={self.metadata}}}" if self.metadata != dict() else "}}"
        return f"{{phenomenonTime={self.phenomenonTime}, quantity={self.quantity}, result={self.result}" \
               + tail


class StreamBuffer:
    """Stream Buffer class

    A class for deterministic, low-latency, high-throughput time-series joins of records within the continuous streams
    'r' (left) and 's' (right join partner).
    """
    def __init__(self, instant_emit=True, delta_time=sys.maxsize, max_latency=sys.maxsize, left="r", right="s",
                 buffer_results=True, join_function=None, commit_function=None, verbose=False):
        """

        :param instant_emit: boolean, default=True
            Emit (join and reduce) on each new record in the buffer
        :param delta_time: float, int, default=sys.maxsize
            Sets the maximum allowed time difference of two join candidates
        :param max_latency: float, int, default=sys.maxsize
            Join rule waits up to max_latency for new Records before joining them anyway. Breaks the determinism
            guarantee.
        :param left: str, optional
            Sets the stream's quantity name that is joined as left record
        :param right: str, optional
            Sets the stream's quantity name that is joined as right record
        :param buffer_results: boolean, default=True
            Whether or not to buffer resulting join records
        :param join_function: function(record_left, record_right), default=None
            A function for merging the two join tuples, can be seen as projection in terms of relational algebra.
            The default is None, that inherits all attributes of both records, the function can look as follows:

            def join_fct(record_left, record_right):
                record = Record(quantity=self.result_quantity,  # default 't'
                                result=record_left.get_result() * record_right.get_result(),
                                timestamp=(record_left.get_time() + record_right.get_time()) / 2)
                # produce resulting record in Kafka or a pipeline
                return record
        :param commit_function: function(record_to_commit), default=None
            A function that enables a streaming-platform specific commit, e.g. for Apache Kafka.
            This enables an at-least-once delivery and replay capability in case of a failure.
            The default is None, that inherits all attributes a record, the function can look as follows:

            def commit_fct(record_to_commit):
                # Commits message’s offset+1
                kafka_consumer.commit(record_to_commit.get("msg"))
        """
        # unload the input and stream the messages based on the order into the buffer queues
        self.buffer_left = LinkedList(side="left")
        self.buffer_right = LinkedList(side="right")
        self.buffer_out = LinkedList()
        self.counter_left = 0
        self.counter_right = 0
        self.counter_joins = 0
        self.instant_emit = instant_emit
        if not instant_emit:
            raise NotImplementedError("implement trigger_emit method.")
        self.delta_time = delta_time
        self.left_quantity = left  # is not used anywhere
        self.right_quantity = right  # is not used anywhere
        self.buffer_results = buffer_results
        self.join_function = join_function
        self.commit_function = commit_function
        self.max_latency = max_latency
        if self.max_latency != sys.maxsize:
            raise Exception("Maximum latency is not implemented yet.")
        self.verbose = verbose

    def get_left_buffer(self):
        """Get buffer r

        :return: the buffer r
        """
        return self.buffer_left

    def get_right_buffer(self):
        """Get buffer s

        :return: the buffer s
        """
        return self.buffer_right

    def fetch_results(self):
        """Fetch the buffer for the resulting join records. The buffer is emptied when fetched

        :return: a list of resulting join records
        """
        res = self.buffer_out.items()
        self.buffer_out = LinkedList()
        return res

    def get_left_counter(self):
        """Get the number of ingested Records in the left buffer

        :return: the number of left ingested Records
        """
        return self.counter_left

    def get_right_counter(self):
        """Get the number of ingested Records in the right buffer

        :return: the number of right ingested Records
        """
        return self.counter_right

    def get_join_counter(self):
        """Get the number of joined Records of the LocalStreamBuffer

        :return: the number of joins
        """
        return self.counter_joins

    def ingest_left(self, record):
        """
        Ingests a record into the left side of the StreamBuffer instance. Emits instantly join partners if not unset.
        :param record: object
            A Measurement or Event object.
        """
        self.buffer_left.append({"ts": record.get_time(), "record": record, "was_older": False})
        self.counter_left += 1
        if self.instant_emit:
            self.buffer_left, self.buffer_right = self.emit(buffer_pivotal=self.buffer_left,
                                                            buffer_exterior=self.buffer_right)

    def ingest_right(self, record):
        """
        Ingests a record into the right side of the StreamBuffer instance. Emits instantly join partners if not unset.
        :param record: object
            A Measurement or Event object.
        """
        self.buffer_right.append({"ts": record.get_time(), "record": record, "was_older": False})
        self.counter_right += 1
        if self.instant_emit:
            self.buffer_right, self.buffer_left = self.emit(buffer_pivotal=self.buffer_right,
                                                            buffer_exterior=self.buffer_left)

    def emit(self, buffer_pivotal, buffer_exterior):
        """
        This function is called if a new (pivotal) Record is received and tries to find join partners within two
        buffers and reduces them. If one of the buffers is empty, it is returned immediately.
        Otherwise, four cases are checked that can lead to a join:
        # Join-case JR1: the pivotal buffer has the leading Record and the pivotal's predecessor finds partners
        # Join-case JR2: the pivotal buffer has the leading Record and the pivotal Record finds partners
        # Join-case JS2: the external buffer has the leading Record and the pivotal Record finds one partner

        :param buffer_pivotal: list of Records
            The buffer with a pivotal record, i.e., the most recently received one that is checked for partners.
        :param buffer_exterior: list of Records
            The other buffer.
        :return: tuple of two Lists of Records
            A tuple of the same buffers in same order, but reduced if join partners where found
        """
        if self.verbose:
            print(f"New ingest into '{buffer_pivotal.tail.data.get('record').get_quantity()}' with timestamp: "
                  f"{buffer_pivotal.tail.data.get('record').get_time()}")
        # Check if one of the Buffers is empty
        if buffer_exterior.size == 0 or buffer_pivotal.size == 0:
            return buffer_pivotal, buffer_exterior

        # Join-case JR1: the pivotal buffer has the leading Record and the pivotal's predecessor finds partners
        # joins r_t1--s_j, if r_t1.time < s_j.time <= r_t0.time and r_t1.time < s_j.prev.time. Otherwise, they would
        # already have been joined as JR2.
        r_t0 = buffer_pivotal.tail  # the latest and therefore most recent Record
        r_t1 = r_t0.prev
        s_j = buffer_exterior.head  # the first and therefore oldest Record
        if r_t1 is not None:
            # steps s_j forward until r_t1.time < s_j.time (trivially holds if r_t1 is None)
            while s_j is not None and s_j.data.get("record").get_time() <= r_t1.data.get("record").get_time():
                s_j = s_j.next
            # steps one ahead, as r_t1--s_j are already joined as JR1
            if s_j is not None:
                s_j = s_j.next
                # joins as long as s_j.time <= r_t0.time
                while s_j is not None and s_j.data.get("record").get_time() <= r_t0.data.get("record").get_time():
                    self.join(r_t1, s_j, case="JR1")
                    if not r_t1.data.get("was_older"):
                        r_t1.data["was_older"] = True
                    s_j = s_j.next

        # Join-case JR2: the pivotal buffer has the leading Record and the pivotal Record finds partners
        # joins r_t0--s_j, if r_t1.time < s_j.time <= r_t0.time
        r_t0 = buffer_pivotal.tail  # the latest and therefore most recent Record
        r_t1 = r_t0.prev
        s_j = buffer_exterior.head
        # steps s_j forward until r_t1.time < s_j.time (trivially holds if r_t1 is None)
        if r_t1 is not None:
            while s_j is not None and s_j.data.get("record").get_time() <= r_t1.data.get("record").get_time():
                s_j = s_j.next
        # join r_t0--s_j until the s_j is None or r_t0.time < s_j.time which does not occur in this case
        while s_j is not None and s_j.data.get("record").get_time() <= r_t0.data.get("record").get_time():
            self.join(r_t0, s_j, case="JR2")
            if not s_j.data.get("was_older"):
                s_j.data["was_older"] = True
            s_j = s_j.next

        # Join-case JS2: the external buffer has the leading Record and the pivotal Record finds one partner
        # joins r_t0--s_j, if s_j is the Record in buffer_exterior with the subsequent timestamp:
        # formally: s_j = min_t({s_k in s with r_t0.time <= s_k.time})
        r_t0 = buffer_pivotal.tail  # the latest and therefore most recent Record
        s_j = buffer_exterior.head
        # steps s_j forward until r_t0.time < s_j.time
        while s_j is not None and s_j.data.get("record").get_time() < r_t0.data.get("record").get_time():
            s_j = s_j.next
        # r_t0.time <= s_k.time so join them and continue
        if s_j is not None:
            self.join(r_t0, s_j, case="JS2")
            if not r_t0.data.get("was_older"):
                r_t0.data["was_older"] = True

        # Strip the buffers: try to commit & remove deprecated records based on a record criteria (cases, B and E)
        buffer_pivotal = self.strip_buffers(buffer_pivotal, buffer_exterior)
        buffer_exterior = self.strip_buffers(buffer_exterior, buffer_pivotal)

        # it is necessary to return the two modified buffers and overwrite the instance variables
        return buffer_pivotal, buffer_exterior

    def strip_buffers(self, buffer_trim, buffer_current):
        """
        Trims one buffer if the record is outdated, that is if a more recent record exists or a record's
        timestamp exceeds a certain threshold compared to this of the exterior buffer.
        :param buffer_trim: List of Records
            A buffer that is about to get trimmed, based on the two cases.
        :param buffer_current: List of Records
            The comparision buffer that remains unchanged.
        :return: List of Records
            The trimmed buffer
        """
        # Return if one of them is empty
        if buffer_current.size == 0 or buffer_trim.size == 0:
            return buffer_trim

        # # Case JT1: Iteratively join and trim outdated Records if they have never been the older join partner
        # # This helps to join Records that
        # s_1 = None if len(buffer_current) < 1 else buffer_current[-1]  # load the latest (newest) entry of s
        # s_idx = 0
        # s_0 = buffer_current[s_idx]
        # r_1 = buffer_trim[0]
        # r_2 = None if len(buffer_trim) < 2 else buffer_trim[1]
        # while r_2 is not None \
        #         and r_1.get("record").get_time() < r_2.get("record").get_time() <= s_1.get("record").get_time():
        #     # commit r_2 in the data streaming framework
        #     # remove r_2 from the buffer r
        #     # some records r_1 are not joined so far as older sibling
        #     if not r_1.get("was_older"):
        #         # forward to the first s, with event time r_1 < s_0
        #         while s_0 is not None and s_0.get("record").get_time() <= r_1.get("record").get_time():
        #             s_idx += 1
        #             s_0 = buffer_current[s_idx]
        #         self.join(r_1, s_0, case="4")
        #     # remove r_1 from buffer
        #     buffer_trim = buffer_trim[1:]
        #     r_1 = buffer_trim[0]
        #     r_2 = None if len(buffer_trim) < 2 else buffer_trim[1]

        # Remove Records from buffer_trim that can't find any join partners any more
        s_0 = buffer_current.tail  # the latest and therefore most recent Record
        r_i0 = buffer_trim.head
        r_i1 = r_i0.next
        while r_i1 is not None and r_i1.data.get("record").get_time() <= s_0.data.get("record").get_time():
            if self.verbose:
                print(f"  removing superseded record {r_i0.data.get('record')}, leader: {s_0.data.get('record')}")
            buffer_trim.delete(r_i0.data)
            if self.commit_function:
                self.commit_function(record_to_commit=r_i0)
            r_i0 = r_i1
            r_i1 = r_i0.next

        return buffer_trim

    def join(self, node_u, node_v, case="undefined"):
        """Joins two Node objects 'u' and 'v' if the time constraint holds and produces a resulting record.
            .data - holds their data object
            .side - marks the side of the buffer ("left", "right" or None)
        The join_function and commit_function can be set arbitrary, see __init__()

        :param case: String
            Specifies the case that leads to the join
        :param node_u: Node object that holds a record regardless if it is a left or right join partner
        :param node_v: Node object that holds a record regardless if it is a left or right join partner
        """
        u = node_u.data
        v = node_v.data
        # check the delta time constraint, don't join if not met
        if abs(u.get('record').get_time() - v.get('record').get_time()) > self.delta_time:
            return None

        # decide based on the defined left_quantity, which record is joined as left join partner
        if node_v.side == "left":
            record_left = v.get('record')
            record_right = u.get('record')
        else:
            # select them from the normal order, default
            record_left = u.get('record')
            record_right = v.get('record')

        # apply an arbitrary join function to merge both records, if set
        if self.join_function:
            record = self.join_function(record_left=record_left, record_right=record_right)
        else:
            # apply the default join that is a merge using the records' quantity names as prefix
            record = {"r.quantity": record_left.get_quantity(), "r.phenomenonTime": record_left.get_time(),
                      "r.result": record_left.get_result(), "s.quantity": record_right.get_quantity(),
                      "s.phenomenonTime": record_right.get_time(), "s.result": record_right.get_result()}
            if record_left.get_metadata() != dict():
                record["r.metadata"] = record_left.get_metadata()
            if record_right.get_metadata() != dict():
                record["s.metadata"] = record_right.get_metadata()

        self.counter_joins += 1
        # print join to stdout and/or append to resulting buffer
        if self.verbose:
            print(f" join case {case}:\t {record}.")
        if self.buffer_results and record is not None:
            self.buffer_out.append(record)


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


# Test script for the classes.
if __name__ == "__main__":
    # create an instance of the StreamBuffer class
    stream_buffer = StreamBuffer(instant_emit=True, delta_time=100, left="r", buffer_results=True,
                                 verbose=True)

    # create Lists to store the input streams
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
