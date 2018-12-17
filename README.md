# Digital Twin Stack
### A scalable and high-performance streaming platform with inherent semantic data mapping to enable a digital twin.

This repository comprised 3 parts:
* **Digital Twin Messaging Layer** which unifies [Apache Kafka](https://kafka.apache.org/)
 with [SensorThings](http://developers.sensorup.com/docs/) 
* **Digital Twin Client** to easily access the Messaging Layer with only 4 lines of code
* **Demo Application** to get started as fast as possible 

Example on how to send data using the Digital Twin Client

```python3
from client.digital_twin_client import DigitalTwinClient
client = DigitalTwinClient("demo_app1")
client.register(instance_file="digital_twin_mapping/instances")
client.send(quantity="demo_temperature", result=23.4)
```

## Contents

1. [Requirements](#requirements)
2. [Quickstart](#quickstart)
3. [Deploy on a Cluster](#deploy-on-a-cluster)


## Requirements

* Install [Docker](https://www.docker.com/community-edition#/download) version **1.10.0+**
* Install [Docker Compose](https://docs.docker.com/compose/install/) version **1.6.0+**
* Clone this Repository


## Quickstart

This is an instruction on how to set up a demo scenario on your own hardware.
Here, we use Ubuntu 18.04.

 
#### Firstly, **Apache Kafka** and some requirements have to be installed:

Currently, we use Kafka **version 0.11.0.3** as it seems to be the most reliable version, 
but it is planned to update to version 2.X in the future. All installations are stored in `/kafka`.

    sudo apt-get update
    cd setup
    sh kafka/install-kafka-0v11.sh
    sudo sh kafka/install-kafka-libs-0v11.sh
    pip3 install -r requirements.txt

Then, to test the installation:

    /kafka/bin/zookeeper-server-start.sh -daemon /kafka/config/zookeeper.properties
    /kafka/bin/kafka-server-start.sh -daemon /kafka/config/server.properties
    /kafka/bin/kafka-topics.sh --zookeeper localhost:2181 --create --topic test-topic --replication-factor 1 --partitions 1
    /kafka/bin/kafka-topics.sh --zookeeper localhost:2181 --list
    
    /kafka/bin/kafka-console-producer.sh --broker-list localhost:9092 --topic test-topic
    >Hello Franz
    > [Ctrl]+C
    /kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic test-topic --from-beginning
    Hello Franz
    


#### Secondly, the **SensorThings Server** GOST is set up to add semantics to Apache Kafka:


    cd setup/gost/
    docker-compose up -d


The flag `-d` stands for `daemon` mode. To check if everything worked well, open
[http://localhost:8082/](http://localhost:8082/) or view the logs:

    docker-compose logs -f


#### Finally, we run the **demo applications** which can be used as starting point:

Now, open new terminals to run the demo applications from the `client` directory:

    python3 demo_applications/demo_app1/demo_app1.py 
    > INFO:PR Client Logger:init: Initialising Digital Twin Client with name: demo_app1
    ....
    > The temperature of the demo machine is 42.3 °C at 2018-12-04T14:18:10.375153+00:00


    python3 demo_applications/demo_app2/demo_app2.py 
    > INFO:PR Client Logger:init: Initialising Digital Twin Client with name: demo_app2
    ...
    > Received new data: {'phenomenonTime': ....}
    
    
#### Track what happens behind the scenes:

Check the automatically created kafka topics:

    /kafka/bin/kafka-topics.sh --zookeeper localhost:2181 --list
    pr.demo-system.logging
    pr.demo-system.metric
    test-topic

Two new topics were created automatically. 
To track the traffic in real time, use the `kafka-consumer-console`: 

    /kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic pr.demo-system.metric
    > {"phenomenonTime": "2018-12-04T14:18:11.376306+00:00", "resultTime": "2018-12-04T14:18:11.376503+00:00", "result": 50.05934369894213, "Datastream": {"@iot.id": 2}}

You can use the flag `--from-beginning` to see the whole recordings of the persistence time which are
two weeks by default.
After the tests, stop the services with:

    /kafka/bin/kafka-server-stop.sh 
    /kafka/bin/zookeeper-server-stop.sh 
    cd setup/gost
    docker-compose down

If you want to remove the instances from the GOST server, run `docker-compose down -v`.


## Deploy on a Cluster

The deployment in cluster node requires the following steps:

#### Set up Kafka Cluster

*   Install Kafka without client libraries on each node:
    
        sudo apt-get update
        cd setup
        sh kafka/install-kafka-0v11.sh
     
*   Configure the Kafka Cluster on each node:

    Exemplary, we are using the node with ip 192.168.48.81 as our Kafka leader, 
    on which zookeeper will run:
    
    Copy and change the config file for each broker on  node `[k]`, e.g. k in {1,2,3} :

        cp /kafka/config/server.properties /kafka/config/il08[k].properties
        nano /kafka/config/il08[k].properties

    And set the following properties to:

        broker.id=[k]
        delete.topic.enable=true
        log.dirs=/tmp/kafka-logs-[k]
        zookeeper.connect=192.168.48.81:2181

    Note that zookeeper will run solely on node 192.168.48.81.


* Create Systemd file and enable autostart

    As zookeeper will only run on the node with ip 192.68.48.81, we copy the file `zookeeper.service` 
    from `setup/kafka` into `/etc/systemd/system/` and them adjust the *user* and *group*. 
    (only on 192.68.48.81)

        cp setup/kafka/zookeeper.service /etc/systemd/system/
        sudo nano /etc/systemd/system/zookeeper.service

    Kafka will run on each node, so we copy the file `kafka.service` 
    from `setup/kafka` into `/etc/systemd/system/` and them adjust the *user*, *group* and 
    the node id *[k]* in *ExecStart*. Do that on each node.

        cp setup/kafkakafka.service
        sudo nano /etc/systemd/system/kafka.service
    
    After that, reload the services and enable autostart for each service:
    
        sudo systemctl daemon-reload
        sudo service zookeeper restart  # only on node with ip 192.68.48.81
        sudo service zookeeper status  # only on node with ip 192.68.48.81
        sudo service kafka restart
        sudo service kafka status
        sudo systemctl enable kafka
        sudo systemctl enable zookeeper  # only on node with ip 192.68.48.81

    The status should show that the service run successful. If you are curious, run the 
    tests [here](#firstly-apache-kafka-and-some-requirements-have-to-be-installed).


*   Create Topics for your specific application system, which should be configured in 
    `client/config.json`:  (If not set, the topics in the config.json will be created with
     the default settings of replication-factor 1 and 1 partition). 
    Here zookeeper is available on `192.168.48.81:2181` and there are in total 3 available brokers in
    our Kafka Cluster.
    
    We use the following **topic convention**, which allows us to use the Cluster for different 
    systems in parallel and maintain best performance for metric data even when big objects are sent. 
    
    Topic convention: **pr.[system-name].["metric"|"string"|"object"|"logging"]**
    
        /kafka/bin/kafka-topics.sh --zookeeper 192.168.48.81:2181 --create --topic pr.dtz.metric --replication-factor 2 --partitions 3 --config cleanup.policy=compact --config retention.ms=3628800000 --config retention.bytes=-1
        /kafka/bin/kafka-topics.sh --zookeeper 192.168.48.81:2181 --create --topic pr.dtz.string --replication-factor 2 --partitions 3 --config cleanup.policy=compact --config retention.ms=3628800000 --config retention.bytes=-1
        /kafka/bin/kafka-topics.sh --zookeeper 192.168.48.81:2181 --create --topic pr.dtz.object --replication-factor 2 --partitions 3 --config cleanup.policy=compact --config retention.ms=3628800000 --config retention.bytes=-1
        /kafka/bin/kafka-topics.sh --zookeeper 192.168.48.81:2181 --create --topic pr.dtz.logging --replication-factor 1 --partitions 1 --config cleanup.policy=compact --config retention.ms=3628800000 --config retention.bytes=-1
     
        /kafka/bin/kafka-topics.sh --zookeeper 192.168.48.81:2181 --list
        /kafka/bin/kafka-topics.sh --zookeeper 192.168.48.81:2181 --describe --topic pr.dtz.metric
        > Topic:pr.dtz.metric	PartitionCount:3	ReplicationFactor:2	Configs:retention.ms=3628800000,cleanup.policy=compact,retention.bytes=-1
	    >     Topic: pr.dtz.metric	Partition: 0	Leader: 3	Replicas: 3,2	Isr: 3,2
	    >     Topic: pr.dtz.metric	Partition: 1	Leader: 1	Replicas: 1,3	Isr: 1,3
	    >     Topic: pr.dtz.metric	Partition: 2	Leader: 2	Replicas: 2,1	Isr: 2,1

    To track the traffic in real time, use the `kafka-consumer-console`: 

        /kafka/bin/kafka-console-consumer.sh --bootstrap-server 192.168.48.81:9092 --topic pr.dtz.metric
        > {"phenomenonTime": "2018-12-04T14:18:11.376306+00:00", "resultTime": "2018-12-04T14:18:11.376503+00:00", "result": 50.05934369894213, "Datastream": {"@iot.id": 2}}

    To delete topics, search for topics and then remove the desired directory:
    
        /kafka/bin/zookeeper-shell.sh 192.168.48.81:2181 ls /brokers/topics
        /kafka/bin/zookeeper-shell.sh 192.168.48.81:2181 rmr /brokers/topics/topicname
    
    To stop Kafka or Zookeeper:
    
        sudo service kafka stop
        sudo service zookeeper stop


#### Setup of a Docker Swarm

A nice tutorial on how to set up a docker Swarm can be found on [dataques.io](https://www.dataquest.io/blog/install-and-configure-docker-swarm-on-ubuntu/).

Additionally, some docker images may need  increased virtual memory. Therefore add the following 
line to `/etc/sysctl.conf` on each node and reboot.

    vm.max_map_count=262144
 
 If not already done, add a registry instance to register the image
```bash
docker service create --name registry --publish published=5001,target=5000 registry:2
curl 127.0.0.1:5001/v2/
```
This should output `{}`:

 
#### Deploy SensorThings 

In cluster mode, it is important that the data-backend of the service `gost-db` is never changed,
as it is by default, whenever a service restarts on a different node.
To handle this, there are 2 options: (note, that for each option, the used **docker compose file 
may have to be changed**)

*   **Fixate** each service on the same node forever using `setup/gost/swarm_docker-compose.yml`.
    To deploy, run:
    
        cd ../setup/gost
        ./start-gost.sh

*   Use a **shared filesystem** suited for docker (note that docker only allows to mount 
    subdirectories by default).
    In this example, we are using **GlusterFS**, find tutorials on how to set it up 
    [here](https://www.howtoforge.com/tutorial/high-availability-storage-with-glusterfs-on-ubuntu-1804/) 
    and [here](http://embaby.com/blog/using-glusterfs-docker-swarm-cluster/). 
    To deploy with an existing shared GlusterFS in `/mnt/glusterfs for each node` and create the 
    appropriate subdirectories, e.g. `/mnt/glusterfs/dtz/gost/postgis/`.
    Then, run the compose file with the name `swarm_docker-compose-with-glusterfs.yml` on the 
    swarm manager, which will **deploy each service with 2 replicas**.:
    
        cd ../setup/gost
        ./start-gost-with-glusterfs.sh

In either case the services should be available on [http://hostname:8082](http://hostname:8082)
To check for more details and to stop the services stack:

    ./show-gost.sh
    ./stop-gost.sh
 
 
#### Configure the client
  Which is done in `client/config.json`. An example of how this config can look like is
  in `client/swarm-config.json`, where the lines are changed as shown here:
  
  ```json
  {
  "_comment": "Kafka Config",
  "BOOTSTRAP_SERVERS": "192.168.48.81:9092,192.168.48.82:9092,192.168.48.83:9092",
  
  "_comment": "SensorThings Config: check in setup/gost/docker-compose.yml for the settings",
  "GOST_SERVER": "192.168.48.81:8082",
  
  "_comment": "SensorThings Type Mapping: These types must fit with the kafka topic in config.json of the client.",
  "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_TruthObservation": "pr.dtz.metric",
  "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_CountObservation": "pr.dtz.metric",
  "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Measurement": "pr.dtz.metric",
  "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_CategoryObservation": "pr.dtz.string",
  "http://www.opengis.net/def/observationType/OGC-OM/2.0/OM_Observation": "pr.dtz.object",
  "panta-rhei/Logging": "pr.dtz.logging"
}
  ```
  
  


#### Deploy your application in cluster mode

This needs a well configured `docker-compose.yml` for your specific application.
See this compatible [MQTT-Adapter](https://github.com/iot-salzburg/dtz_mqtt-adapter) 
for more information.
