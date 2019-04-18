# Digital Twin Stack
### A scalable streaming platform that enables the sharing of IoT data.

This repository is comprised of 3 layers:
* **Digital Twin Messaging Layer** which unifies [Apache Kafka](https://kafka.apache.org/)
 with [SensorThings](http://developers.sensorup.com/docs/) 
* **Digital Twin Client** to easily access the Messaging Layer with only an hand full lines of code
* **Demo Application** to get started as fast as possible 

Example on how to send data using the Digital Twin Client

```python3
from client.digital_twin_client import DigitalTwinClient
config = {"client_name": "demo_station_1",
          "system": "eu.srfg.iot-iot4cps-wp5.car1",
          "gost_servers": "localhost:8084",
          # Use one of the both, bootstrap server is dominating
          "kafka_bootstrap_servers": None,  # "localhost:9092", 
          "kafka_rest_server": "localhost:8082"}
          
client = DigitalTwinClient(**config)
client.register_existing(mappings_file="ds-mappings.json")
client.produce(quantity="demo_temperature", result=23.4)
```

## Contents

1. [Requirements](#requirements)
2. [Quickstart](#quickstart)
3. [Deploy on a Cluster](#deployment-on-a-cluster)


## Requirements

* Install [Docker](https://www.docker.com/community-edition#/download) version **1.10.0+**
* Install [Docker Compose](https://docs.docker.com/compose/install/) version **1.6.0+**
* Clone this Repository


## Quickstart

This is an instruction on how to set up a demo scenario on your own hardware.
Here, we use Ubuntu 18.04.

 
#### Firstly, **Apache Kafka** and some requirements have to be installed:

The Datastack uses Kafka **version 2.1.0** as the communication layer, the installations is done in `/kafka`.

    sudo apt-get update
    sh setup/kafka/install-confluent.sh
    sh setup/kakfa/install-kafka-libs-2v1.sh
    export PATH=/confluent/bin:$PATH
    pip3 install -r setup/requirements.txt

Then, to test the installation:

    confluent start
    confluent status
    > ksql-server is [UP]
    > connect is [UP]
    > kafka-rest is [UP]
    > schema-registry is [UP]
    > kafka is [UP]
    > zookeeper is [UP]

    # Test the installation
    kafka-topics.sh --zookeeper localhost:2181 --list
    kafka-topics.sh --zookeeper localhost:2181 --create --topic test-topic --replication-factor 1 --partitions 1
    kafka-console-producer.sh --broker-list localhost:9092 --topic test-topic
    >Hello Kafka
    > [Ctrl]+C
    kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic test-topic --from-beginning
    Hello Kafka
    
    kafka-topics.sh --zookeeper localhost:2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic eu.srfg.iot-iot4cps-wp5.CarFleet1.data
    kafka-topics.sh --zookeeper localhost:2181 --create --partitions 3 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic eu.srfg.iot-iot4cps-wp5.CarFleet1.external
    kafka-topics.sh --zookeeper localhost:2181 --create --partitions 1 --replication-factor 1 --config min.insync.replicas=1 --config cleanup.policy=compact --config retention.ms=241920000 --topic eu.srfg.iot-iot4cps-wp5.CarFleet1.logging
    # Create analog topics for 'CarFleet2' and 'WeatherService'

Test the confluent kafka platform on [http://localhost:9021/](http://localhost:9021/)

#### Secondly, the **SensorThings Server** GOST is set up to add semantics to Apache Kafka:

    cd setup/gost/
    docker-compose up -d

The flag `-d` stands for `daemon` mode. To check if everything worked well, open
[http://localhost:8084/](http://localhost:8084/) or view the logs:

    docker-compose logs -f


#### Finally, we run the **demo applications** which can be used as starting point:

Now, open new terminals to run the demo applications from the `client` directory:

    python3 demo_applications/CarFleet1/car_1.py
    > INFO:PR Client Logger:init: Initialising Digital Twin Client with name 'demo_car_1' on 'eu.srfg.iot-iot4cps-wp5.CarFleet1'
    ....
    > The air temperature at the demo car 1 is 2.9816131778905497 °C at 2019-03-18T13:54:59.482215+00:00


    python3 demo_applications/CarFleet2/car_2.py
    > INFO:PR Client Logger:init: Initialising Digital Twin Client with name 'demo_car_2' on 'eu.srfg.iot-iot4cps-wp5.CarFleet2'
    ...
    > The air temperature at the demo car 2 is 2.623506013964546 °C at 2019-03-18T12:21:27.177267+00:00
    >   -> Received new external data-point of 2019-03-18T13:54:59.482215+00:00: 'eu.srfg.iot-iot4cps-wp5.CarFleet1.car_1.Air Temperature' = 2.9816131778905497 degC.
    
Then, start the Kafka Stream Apps in `demo_applications/com.github.christophschranz.iot4cps.streamhub/target/classes/com/github/christophschranz/iot4cpshub` to allow the sharing of data across the systems.


#### Run the Datastore

First, some configs have to be set in order to make the datastore work properly:
    
    ulimit -n 65536  # Increase the max file descriptor
    sudo sysctl -w vm.max_map_count=262144  # Increase the virtual memory
    sudo service docker restart  # Restart docker to make the changes work
    
(further information in progress ...)
    
    
#### Track what happens behind the scenes:

Check the created kafka topics:

    kafka-topics.sh --zookeeper localhost:2181 --list
    eu.srfg.iot-iot4cps-wp5.CarFleet1.data
    eu.srfg.iot-iot4cps-wp5.CarFleet1.external
    eu.srfg.iot-iot4cps-wp5.CarFleet1.logging
    eu.srfg.iot-iot4cps-wp5.CarFleet2.data
    eu.srfg.iot-iot4cps-wp5.CarFleet2.external
    eu.srfg.iot-iot4cps-wp5.CarFleet2.logging
    eu.srfg.iot-iot4cps-wp5.WeatherService.data
    eu.srfg.iot-iot4cps-wp5.WeatherService.external
    eu.srfg.iot-iot4cps-wp5.WeatherService.logging
    test-topic

Note that kafka-topics must be created manually as explained in the [Quickstart](#quickstart).

To track the traffic in real time, use the `kafka-consumer-console`: 

    kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic eu.srfg.iot-iot4cps-wp5.CarFleet1.data
    > {"phenomenonTime": "2018-12-04T14:18:11.376306+00:00", "resultTime": "2018-12-04T14:18:11.376503+00:00", "result": 50.05934369894213, "Datastream": {"@iot.id": 2}}

You can use the flag `--from-beginning` to see the whole recordings of the persistence time which are
two weeks by default.
After the tests, stop the services with:

    confluent stop
    cd setup/gost
    docker-compose down

If you want to remove the SensorThings instances from the GOST server, run `docker-compose down -v`.


## Deployment on a Cluster

To deploy Kafka on a local cluster, see the 
[setup/README-Deployment.md](setup/README-Deployment.md) notes.
