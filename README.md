# Panta Rhei
### A scalable and high-performance streaming platform with inherent semantic data mapping.

This repository comprised 3 parts:
* **Panta Rhei Messaging Layer** which unifies [Apache Kafka](https://kafka.apache.org/)
 with [SensorThings](http://developers.sensorup.com/docs/) 
* **Panta Rhei Client** to easily access the Messaging Layer in only only 4 lines of code
* **Demo Application** to get started as fast as possible 



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

    sudo apt-get update && sudo apt-get install openjdk-8-jre wget -y
    export kafka_version=0.11.0.3
    wget https://archive.apache.org/dist/kafka/${kafka_version}/kafka_2.11-${kafka_version}.tgz
    tar -xvzf kafka_2.11-${kafka_version}.tgz
    rm kafka_2.11-${kafka_version}.tgz
    sudo mv kafka_2.11-${kafka_version} /kafka
    sudo chmod +x /kafka/bin/*


Then, to start Kafka and test the installation:

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

Now, open new terminals to run the demo applications:

    python3 demo_applications/demo_app1/demo_app1.py 
    > INFO:PR Client Logger:init: Initialising Panta Rhei Client with name: demo_app1
    ....
    > The temperature of the demo machine is 42.3 °C at 2018-12-04T14:18:10.375153+00:00


    python3 demo_applications/demo_app2/demo_app2.py 
    > INFO:PR Client Logger:init: Initialising Panta Rhei Client with name: demo_app2
    ...
    > Received new data: {'phenomenonTime': ....}
    
    
Track the traffic in real time via the Kafka-consumer-console:

    /kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic test-topic --from-beginning
    > {"phenomenonTime": "2018-12-04T14:18:11.376306+00:00", "resultTime": "2018-12-04T14:18:11.376503+00:00", "result": 50.05934369894213, "Datastream": {"@iot.id": 2}}



## Deploy on a Cluster

The gost server uses shared data on the samba share. This
volume must be in the Docker directory due to reasons discussed
in this [thread](https://github.com/moby/moby/issues/2745)

Hence, to get started, do this steps on each node first: (including backup)

```bash
sudo cp /etc/fstab /etc/fstab.save
sudo sh -c 'echo "" >> /etc/fstab'
sudo sh -c 'echo "# Adding this line for docker swarm sensorthings" >> /etc/fstab'
sudo sh -c 'echo "//192.168.48.60/samba-share/il08X/PantaRhei/gost-db /srv/panta-rhei/gost_server/samba-mount cifs auto,password=,uid=1000,gid=0 0 0" >> /etc/fstab'
sudo mkdir -p /srv/panta-rhei/gost_server/samba-mount
sudo mount -a
```


schreib a systemd service. des wird im gost-db eine kopiert und synchronisiert
zwischen ./samba-data und/var/lib/postgres/data
