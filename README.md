# Digital Twin Stack
### A scalable and high-performance streaming platform with inherent semantic data mapping to enable a digital twin.

This repository comprised 3 parts:
* **Digital Twin Messaging Layer** which unifies [Apache Kafka](https://kafka.apache.org/)
 with [SensorThings](http://developers.sensorup.com/docs/) 
* **Digital Twin Client** to easily access the Messaging Layer with only an hand full lines of code
* **Demo Application** to get started as fast as possible 

Example on how to send data using the Digital Twin Client

```python3
from client.digital_twin_client import DigitalTwinClient
config = {"client_name": "demo_app1", "system_name": "demo-system",
          "kafka_bootstrap_servers": "localhost:9092", "gost_servers": "localhost:8082"}
client = DigitalTwinClient(**config)
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

The Datastack uses Kafka **version 2.1.0** as the communication layer, the installations is done in `/kafka`.

    sudo apt-get update
    cd setup
    sh kafka/install-kafka-2v1.sh
    sudo sh kafka/install-kafka-libs-2v1.sh
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
    

##### Run the Datastore

First, some configs have to be set in order to make the datastore work properly:
    
    ulimit -n 65536  # Increase the max file descriptor
    sudo sysctl -w vm.max_map_count=262144  # Increase the virtual memory
    sudo service docker restart  # Restart docker to make the changes work
    
    
    
    
#### Track what happens behind the scenes:

Check the automatically created kafka topics:

    /kafka/bin/kafka-topics.sh --zookeeper localhost:2181 --list
    eu.demo-system.logging
    eu.demo-system.metric
    test-topic

Two new topics were created automatically. 
To track the traffic in real time, use the `kafka-consumer-console`: 

    /kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic eu.demo-system.metric
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
        sh kafka/install-kafka-2v1.sh


*   Configure the Zookeeper and Kafka on each node:

    In this example, we set up a small cluster of nodes with the ips `192.168.48.81`,
    `192.168.48.82` and `192.168.48.83`. For simplicity, we use the term
    `[k]` as a variable for the last number of the node ip, e.g. k in {1,2,3}
    
    
    Copy and change the config file for each broker on  node `[k]`:
    
        sudo mkdir /var/lib/zookeeper
        sudo echo "[k]" > /var/lib/zookeeper/myid
        sudo chown -R user.group /var/lib/zookeeper/
        nano /kafka/config/zookeeper.properties
        
    And set the following properties to:
    
        tickTime=2000
        dataDir=/var/lib/zookeeper/
        clientPort=2181
        initLimit=5
        syncLimit=2
        server.1=192.168.48.81:2888:3888
        server.2=192.168.48.82:2888:3888
        server.3=192.168.48.83:2888:3888
        autopurge.snapRetainCount=3
        autopurge.purgeInterval=24

    
    Copy and change the config file for each broker on  node `[k]`:

        cp /kafka/config/server.properties /kafka/config/il08[k].properties
        nano /kafka/config/il08[k].properties

    And set the following properties to:

        broker.id=[k]
        log.retention.hours=720
        zookeeper.connect=192.168.48.81:2181,192.168.48.82:2181,192.168.48.83:2181

    Note that both zookeeper and Kafka will run on the nodes with their ips 
    ending with 81, 82 and 83.


* Create Systemd file and enable autostart

    Copy the files `zookeeper.service` and `kafka.service`
    from `setup/kafka` into `/etc/systemd/system/` and adjust the *user* and *group*. 

    
    ```bash
    cp setup/kafka/zookeeper.service /etc/systemd/system/
    sudo nano /etc/systemd/system/zookeeper.service

    cp setup/kafka/kafka.service /etc/systemd/system/
    sudo nano /etc/systemd/system/kafka.service
    ```

    
    After that, reload the services on each node and enable autostart for each service:
    
    
    ```bash
    sudo systemctl daemon-reload
    sudo systemctl restart zookeeper
    sudo systemctl status --no-pager zookeeper
    sudo systemctl restart kafka
    sudo systemctl status --no-pager kafka
    sudo systemctl enable kafka
    sudo systemctl enable zookeeper
    ```
    
    The status should show that the service run successful. If you are curious, run the 
    tests [here](#firstly-apache-kafka-and-some-requirements-have-to-be-installed).


*   Create Topics which uses the system-name, which is set in the Client config parameter:  
    If the topics are not set before, the topics will be created with
     the default settings with replication-factor 1 and 1 partition). 
    Here zookeeper is available on `192.168.48.81:2181` and there are in total 3 available brokers in
    our Kafka Cluster.
    
    We use the following **topic convention**, which allows us to use the Cluster for different 
    systems in parallel and maintain best performance for metric data even when big objects are sent. 
    
    Topic convention: **eu.[system-name].["metric"|"string"|"object"|"logging"]**
    
        /kafka/bin/kafka-topics.sh --zookeeper 192.168.48.81:2181 --create --topic eu.dtz.metric --replication-factor 2 --partitions 3 --config cleanup.policy=compact --config retention.ms=3628800000 --config retention.bytes=-1
        /kafka/bin/kafka-topics.sh --zookeeper 192.168.48.81:2181 --create --topic eu.dtz.string --replication-factor 2 --partitions 3 --config cleanup.policy=compact --config retention.ms=3628800000 --config retention.bytes=-1
        /kafka/bin/kafka-topics.sh --zookeeper 192.168.48.81:2181 --create --topic eu.dtz.object --replication-factor 2 --partitions 3 --config cleanup.policy=compact --config retention.ms=3628800000 --config retention.bytes=-1
        /kafka/bin/kafka-topics.sh --zookeeper 192.168.48.81:2181 --create --topic eu.dtz.logging --replication-factor 1 --partitions 1 --config cleanup.policy=compact --config retention.ms=3628800000 --config retention.bytes=-1
     
        /kafka/bin/kafka-topics.sh --zookeeper 192.168.48.81:2181 --list
        /kafka/bin/kafka-topics.sh --zookeeper 192.168.48.81:2181 --describe --topic eu.dtz.metric
        > Topic:eu.dtz.metric	PartitionCount:3	ReplicationFactor:2	Configs:retention.ms=3628800000,cleanup.policy=compact,retention.bytes=-1
	    >     Topic: eu.dtz.metric	Partition: 0	Leader: 3	Replicas: 3,2	Isr: 3,2
	    >     Topic: eu.dtz.metric	Partition: 1	Leader: 1	Replicas: 1,3	Isr: 1,3
	    >     Topic: eu.dtz.metric	Partition: 2	Leader: 2	Replicas: 2,1	Isr: 2,1

    To track the traffic in real time, use the `kafka-consumer-console`: 

        /kafka/bin/kafka-console-consumer.sh --bootstrap-server 192.168.48.81:9092 --topic eu.dtz.metric
        > {"phenomenonTime": "2018-12-04T14:18:11.376306+00:00", "resultTime": "2018-12-04T14:18:11.376503+00:00", "result": 50.05934369894213, "Datastream": {"@iot.id": 2}}

    To delete topics, search for topics and then remove the desired directory:
    
        /kafka/bin/zookeeper-shell.sh 192.168.48.81:2181 ls /brokers/topics
        /kafka/bin/zookeeper-shell.sh 192.168.48.81:2181 rmr /brokers/topics/topicname
    
    To stop Kafka or Zookeeper:
    
        sudo service kafka stop
        sudo service zookeeper stop


#### Setup of a Docker Swarm

A nice tutorial on how to set up a docker Swarm can be found on [dataquest.io](https://www.dataquest.io/blog/install-and-configure-docker-swarm-on-ubuntu/).

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
  Which is done by creating a client instance. An example of how this config can look like 
  for a distributed kafka system is shown here:
  
  ```json
{
      "client_name": "demo_app1",
      "system_name": "dtz",
      "kafka_bootstrap_servers": "192.168.48.81:9092,192.168.48.82:9092,192.168.48.83:9092",
      "gost_servers": "192.168.48.81:8082"
}
  ```


#### Deploy your application in cluster mode

This needs a well configured `docker-compose.yml` for your specific application.
See this compatible [MQTT-Adapter](https://github.com/iot-salzburg/dtz_mqtt-adapter) 
for more information.
