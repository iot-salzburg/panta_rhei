# Local Stream Buffer

This project based on developments further explained in [StatefulStreamProcessor](https://github.com/ChristophSchranz/StatefulStreamProcessor), 
where it is part of an end-to-end example to demonstrate 
stateful stream processing on very high throughput of 
machine data. The core component is the *LocalStreamBuffer*
located in `LocalStreamBuffer`, that enables deterministic and
exactly-once time-series joins of streaming data at a high sample rate
of around 15000 joins per second and low latency.
This solution is tested against a the time-series join within
Apache Flink, that is window-based.


![flink-architecture](docs/flink_architecture.png)

## Requirements

* Up and running Digital Twin Platform

---

<br>


## Time-Series Join with the Local Stream Buffer

The LocalStreamBuffer is an algorithm for the deterministic join of two streams of time-series. It is optimised for
high throughput and ensures both minimal latency and to join each candidate. The pre-assumption is that the records 
within each stream comes in order, as it is guaranteed by Streaming Platforms as Apache Kafka if each quantity has a 
dedicated message key. A global order across streams is not required. More information will be published in a 
work-in-progress paper with the title "Deterministic Time-Series Joins for Asynchronous
High-Throughput Data Streams".

**In a nutshell, a time-series join matches each record within one time-series with its previous and subsequent 
complement from the other time-series.**
This property should pertain **independent of the record's ingestion time** 
(the records should be ingested in order within a stream but not across them, as it is
 guaranteed by e.g. Apache kafka).
In the following figure, for two different ingestion orders, the three join cases are depicted:

![localstreambuffer_join-cases](docs/localstreambuffer_joins.png)

A demo-implementation including a short test script is available
 in `05_LocalStreamBuffer/local_stream_buffer.py`. To run it, start:

```bash
cd 05_LocalStreamBuffer
python local_stream_buffer.py
#> New ingest into 's' with timestamp: 1600000000.3101475
#> New ingest into 's' with timestamp: 1600000001.2089858
#> New ingest into 'r' with timestamp: 1600000000.8444219
#>  join case JR2:	 {'r.quantity': 'r', 'r.phenomenonTime': 1600000000.8444219, 'r.result': 0.7579544029403025, 's.quantity': 's', 's.phenomenonTime': 1600000000.3101475, 's.result': 0.7298317482601286}.
#>  join case JS2:	 {'r.quantity': 'r', 'r.phenomenonTime': 1600000000.8444219, 'r.result': 0.7579544029403025, 's.quantity': 's', 's.phenomenonTime': 1600000001.2089858, 's.result': 0.6839839319154413}.
#> ...
#> Join time-series with |r| = 10, |s| = 10.
#> joined 20 tuples in 0.001998424530029297 s.
``` 

Various functionality tests are implemented in `tester.py`, and tests including Kafka
are in `test_kafka_eos_joiner.py` (which needs the `events.json` file). 

Using the LocalStreamBuffer approach, one can join up to **100000 records per second**
from a list and around **15000 records per seconds from Kafka** on localhost 
with **exactly-once processing**.
That is three times more than the 5000 in Flink Java.
As the Confluent Kafka Python client is limited to around 20000 published records per second 
and it also has to consume from Kafka, the time-series join itself makes up only a minor 
amount of time.  In addition to the 
increased performance, the LocalStreamBuffer method ensures that all join
candidates are **joined deterministically**, **exactly-once** and with **minimal latency**.


The joiner script that is the actual pendent of the solution in Apache Flink is 
`ts_join_with_kafka_eos.py`. This solution joins the time-series with 15000 joins per second (vs. 5000 in Flink), 
with a exactly-once processing and with minimal latency as it is not window-based.
Therefore, the proposed algorithm is better for this use-case compared to the standard solution in Apache Flink.

Further steps to even improve the *LocalStreamBuffer* algorithm:
- [ ] use batched production with linger times.
- [ ] implement time triggered joins in cases the partner's succeeder
 has a too high latency.
 - [ ] handle more timeout policies, e.g., join even older or discard.
