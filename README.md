# Panta Rhei
### A scalable and high-performance streaming platform with inherent semantic data mapping.

This repository comprised 3 parts:
* **Panta Rhei Messaging Layer** which unifies [Apache Kafka](https://kafka.apache.org/)
 with [SensorThings](http://developers.sensorup.com/docs/) 
* **Panta Rhei Client** to easily access the Messaging Layer with only 4 lines of code
* **Demo Application** to get started as fast as possible 

Example on how to send data using the Panta Rhei Client

```python
from client.panta_rhei_client import PantaRheiClient
client = PantaRheiClient("demo_app1")
client.register(instance_file="panta_rhei_mapping/instances.json")
client.send(quantity="demo_temperature", result=23.4)
```

## Contents

1. [Requirements](#requirements)
2. [Quickstart](#quickstart)
3. [Deploy on a Cluster](#deployment)
4. [Trouble-Shooting](#trouble-shooting)


## Requirements

* Install [Docker](https://www.docker.com/community-edition#/download) version **1.10.0+**
* Install [Docker Compose](https://docs.docker.com/compose/install/) version **1.6.0+**
* Clone the Repository

## Quickstart

Here, a demo scenario will be set up on a single node.

  
#### First, **Apache Kafka** has to be installed:

Currently, we use Kafka **version 0.11.0.3** as it seems to be the most reliable on, 
but it is planned to update to version 2.X in the future. 

    cd setup
    sudo sh /kafka/install-kafka-0v11.sh
    sudo sh /kafka/install-kafka-libs-0v11.sh
    sudo pip install -r requirements.txt

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

Now, open new terminals to run the demo applications from the `panta_rhei` directory:

    python3 demo_applications/demo_app1/demo_app1.py 
    > INFO:PR Client Logger:init: Initialising Panta Rhei Client with name: demo_app1
    ....
    > The temperature of the demo machine is 42.3 °C at 2018-12-04T14:18:10.375153+00:00


    python3 demo_applications/demo_app2/demo_app2.py 
    > INFO:PR Client Logger:init: Initialising Panta Rhei Client with name: demo_app2
    ...
    > Received new data: {'phenomenonTime': ....}
    
    
#### Track what happens behind the szenes:

Check the automatically created kafka topics:

    /kafka/bin/kafka-topics.sh --zookeeper localhost:2181 --list
    pr.demo-system.logging
    pr.demo-system.metric
    test-topic

Track the traffic in real time via the Kafka-consumer-console:

    /kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic demo-system.metric --from-beginning
    > {"phenomenonTime": "2018-12-04T14:18:11.376306+00:00", "resultTime": "2018-12-04T14:18:11.376503+00:00", "result": 50.05934369894213, "Datastream": {"@iot.id": 2}}

After the tests, close the services with:

    /kafka/bin/kafka-server-stop.sh 
    /kafka/bin/zookeeper-server-stop.sh 
    cd gost
    docker-compose down





## Deploy on a Cluster

The deployment in cluster node needs the following steps:

#### Set up Kafka Cluster

* Install Kafka on each node with configured zookeeper property file

    Exemplary for our test broker with leader ip 192.168.48.81:
    
    Make a config file  for each broker on  node [k] :

        cp /kafka/config/server.properties /kafka/config/il08[k].properties

    And change the following properties:

        broker.id=[k]
        delete.topic.enable=true
        log.dirs=/tmp/kafka-logs-[k]
        zookeeper.connect=192.168.48.81:2181

    Note that zookeeper will run solely on node 192.168.48.81.


* Create Systemd file and enable autostart

    In order to handle the services properly, we create service in systemd.

        sudo nano /etc/systemd/system/kafka.service
        sudo nano /etc/systemd/system/zookeeper.service

    And create the files analog to `setup/kafka/kafka.service` and `setup/kafka/zookeeper.service` 
    (Note that the appropriate hostname is in brackets)



* Create Topics for your specific application system

    

#### Setup of a Docker Swarm

A nice tutorial on how to set up a docker Swarm can be found [here](https://www.dataquest.io/blog/install-and-configure-docker-swarm-on-ubuntu/).

Additionaly, some docker images like need  increased virtual memory. Therefore add the following 
line to `/etc/sysctl.conf` on each node and reboot.

    vm.max_map_count=262144
 
 
#### (optional) Deploy SensorThings 
  In Cluster mode, but fixed on one node (in this case node il082, but everything can done
  from any docker manager):

Using `docker stack`:

If not already done, add a registry instance to register the image
```bash
docker service create --name registry --publish published=5001,target=5000 registry:2
curl 127.0.0.1:5001/v2/
```
This should output `{}`:


If running with docker-coTrouble-shootingmpose works, push the image in
order to make the customized image runnable in the stack and deploy it:

```bash
cd ../setup/gost
./gost_start.sh
```

Watch if everything worked well with:

```bash
./gost_show.sh
```
And stop the service with:
    ./gost_stop.sh
     
 
#### Configure the client
  Which is done in `client/config.json`


#### Deploy your application in cluster mode

This needs a well configured `docker-compose.yml` for your specific application.
See this compatible [MQTT-Adapter](https://github.com/iot-salzburg/dtz_mqtt-adapter) 
for more information.
