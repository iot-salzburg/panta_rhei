# Digital Twin Stack
### An open source platform for IoT data-streaming and metadata management, that reduces the complexity of modern data problems.

![Architecture](/extra/dataflows.png)

An exemplary dataflow as they occur across teams. 

This repository comprises the following parts:

* **Digital Twin Messaging Layer** which unifies [Apache Kafka](https://kafka.apache.org/)
 with [SensorThings](http://developers.sensorup.com/docs/) and can be found in the `setup` directory.
 
* **Digital Twin Client** to easily access the Messaging Layer with only an hand full lines of code, 
    which is in the `client` directory. The usage of the Digital Twin Client is thereby as simple as that:

    ```python
    from client.digital_twin_client import DigitalTwinClient
  
    config = {"client_name": "car_1",
          "system": "at.srfg.iot-iot4cps-wp5.CarFleet",
          "gost_servers": "localhost:8084",
          "kafka_bootstrap_servers": "localhost:9092"}
    client = DigitalTwinClient(**config)
    
    client.register(instance_file="instances.json")
    client.produce(quantity="demo_temperature", result=23.4)
    
    client.subscribe(subscription_file="subscriptions.json")
    received_quantities = client.consume(timeout=1.0)
    ```
  
* **Demo Applications** to get started as fast as possible and change them to your own demands.
    In the demo-scenario there are 3 companies that interchange data via the Digital Twin Platform
    1) The CarFleet is a prosumer (producer and consumer) of data.
    2) The Weather Service Provider produces weather-related data.
    3) The Analytics provider wants to enhance the road quality by analyzing all of the data.
    In `demo_applications/Analytics` there is a DataStack that comes with the 
    [Elastic Stack](https://www.elastic.co/), [Grafana](https://grafana.com/) and a data science environment with a
    [Jupyter](https://jupyter.org/) notebook UI and a connection to the Elasticsearch datasource.
* **Platform User Interface** that deals with the registration of users, companies, systems and client applications.
    It is also possible to deploy so-called *stream-applications* here, that allows to share data between existing
    systems:
    ![System View](/extra/system_view.png) 

***

## Contents

1. [Setup Messaging Layer](#setup-messaging-layer)
2. [Start Demo Applications](#start-demo-applications)
3. [Track what happens behind the scenes](#track-what-happens-behind-the-scenes)
4. [Deployment](#deployment-on-a-cluster)
5. [Platform UI](#platform-ui)


## Setup Messaging Layer

### 1) Requirements

* Install [Docker](https://www.docker.com/community-edition#/download) version **1.10.0+**
* Install [Docker Compose](https://docs.docker.com/compose/install/) version **1.6.0+**
* Clone this Repository
* Install python modules:
    ```bash
    pip3 install -r setup/requirements.txt
    ```


This is an instruction on how to set up a demo scenario on your own hardware.
Here, we use Ubuntu 18.04, for other OS there might have to be made adaptions.

 
### 2) Setup **Apache Kafka** and it's library:

The Datastack uses Kafka **version 2.1.0** as the communication layer, the installations is done in `/kafka`.

```bash
sudo apt-get update
sh setup/kafka/install-kafka-2v1.sh
sh setup/kakfa/install-kafka-libs-2v1.sh
# optional:
export PATH=/kafka/bin:$PATH
```

Then, start Zookeeper and Kafka and test the installation:
```bash
# Start Zookeeper and Kafka Server 
/kafka/bin/zookeeper-server-start.sh -daemon kafka/config/zookeeper.properties
/kafka/bin/kafka-server-start.sh -daemon kafka/config/server.properties

# Test the installation
/kafka/bin/kafka-topics.sh --zookeeper localhost:2181 --list
/kafka/bin/kafka-topics.sh --zookeeper localhost:2181 --create --topic test-topic --replication-factor 1 --partitions 1
/kafka/bin/kafka-console-producer.sh --broker-list localhost:9092 --topic test-topic
>Hello Kafka
> [Ctrl]+C
/kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic test-topic --from-beginning
Hello Kafka
```
If that works as described, you can create the default topics:

 ```bash
sh setup/kafka/create_defaults.sh
/kafka/bin/kafka-topics.sh --zookeeper localhost:2181 --list
```

If multiple topics were generated, everything worked well.


### 3) Setup **SensorThings Server (GOST)** to add semantics:

    docker-compose -f setup/gost/docker-compose.yml up -d

The flag `-d` stands for `daemon` mode. To check if everything worked well, open
[http://localhost:8082/](http://localhost:8082/) or view the logs:

    docker-compose -f setup/gost/docker-compose.yml logs -f



## Start Demo Applications

Now, open new terminals to run the demo applications:

### CarFleet - Prosumer
    python3 demo_applications/CarFleet/Car1/car_1.py
    > INFO:PR Client Logger:init: Initialising Digital Twin Client with name 'demo_car_1' on 'at.srfg.iot-iot4cps-wp5.CarFleet'
    ....
    > The air temperature at the demo car 1 is 2.9816131778905497 °C at 2019-03-18T13:54:59.482215+00:00


    python3 demo_applications/CarFleet/Car2/car_2.py
    > INFO:PR Client Logger:init: Initialising Digital Twin Client with name 'demo_car_2' on 'at.srfg.iot-iot4cps-wp5.CarFleet'
    ...
    > The air temperature at the demo car 2 is 2.623506013964546 °C at 2019-03-18T12:21:27.177267+00:00
    >   -> Received new external data-point of 2019-03-18T13:54:59.482215+00:00: 'at.srfg.iot-iot4cps-wp5.CarFleet.car_1.Air Temperature' = 2.9816131778905497 degC.

### WeatherService - Producer
    
    python3 demo_applications/WeatherService/demo_station_1/demo_station_1.py
    python3 demo_applications/WeatherService/demo_station_2/demo_station_2.py 
    python3 demo_applications/WeatherService/central_service/weather-service.py 

Here, you should see that temperature data is produced by the demo stations and consumed only by the central service.


### Analytics - Consumer and DataStack
The Analytics Provider consumes all data from the stack and pipes it into a Elastic Grafana and Jupyter
Datastack.

First, some configs have to be set in order to make the datastore work properly:
    
    ulimit -n 65536  # Increase the max file descriptor
    sudo sysctl -w vm.max_map_count=262144  # Increase the virtual memory
    sudo service docker restart  # Restart docker to make the changes work
    
For further information, click on this 
[link](https://www.elastic.co/guide/en/elasticsearch/reference/7.2/docker.html#docker-cli-run-prod-mode).
    
Now it can be started:

    sh demo_applications/InfraProvider/start-full-datastack.sh 
    # Wait until Kibana is reachable on localhost:5601
    python3 demo_applications/InfraProvider/datastack_adapter.py 
    
Available Services:
* [localhost:9200](http://localhost:9200) Elasticsearch status
* [localhost:9600](http://localhost:9600) Logstash status
* [localhost:5000](http://localhost:5000) Logstash TCP data input
* **[localhost:5601](http://localhost:5601) Kibana Data Visualisation UI**
* **[localhost:3000](http://localhost:3000) Grafana Data Visualisation UI**
* **[localhost:8888](http://localhost:8888) Jupyterlab DataScience Notebooks**

As no StreamHub application runs for now, no data is consumed by the `datastack-adapter` 
that ingests it into the DataStack. 
Therefore, it is important to start the StreamHub applications as noted in the next section.
   
   
### Stream Hub - Connect the systems

The StreamHub application can be regarded as hub for the streamed data.
Run the built jar file:

```bash
java -jar demo_applications/streamhub_apps/out/artifacts/streamhub_apps_jar/streamhub_apps.jar --stream-name mystream --source-system cz.icecars.iot-iot4cps-wp5.CarFleet target-system at.datahouse.iot-iot4cps-wp5.RoadAnalytics --filter-logic {} --bootstrap-server 127.0.0.1:9092
```
 to share data from the specific tenant to others.

If you want to change the streamhub application itself, modify and rebuild the java project in
`demo_applications/streamhub_apps`. 

It is recommended, to start and stop stream-applications via the [Platform UI](#platform-ui).

    
## Track what happens behind the scenes:

Check the created kafka topics:

    /kafka/bin/kafka-topics.sh --zookeeper localhost:2181 --list
    at.srfg.iot-iot4cps-wp5.CarFleet1.data
    at.srfg.iot-iot4cps-wp5.CarFleet1.external
    at.srfg.iot-iot4cps-wp5.CarFleet1.logging
    at.srfg.iot-iot4cps-wp5.CarFleet2.data
    at.srfg.iot-iot4cps-wp5.CarFleet2.external
    at.srfg.iot-iot4cps-wp5.CarFleet2.logging
    at.srfg.iot-iot4cps-wp5.WeatherService.data
    at.srfg.iot-iot4cps-wp5.WeatherService.external
    at.srfg.iot-iot4cps-wp5.WeatherService.logging
    test-topic

Note that kafka-topics must be created manually as explained in the [Setup](#setup-messaging-layer).

To track the traffic in real time, use the `kafka-consumer-console`: 

    /kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic at.srfg.iot-iot4cps-wp5.CarFleet1.data
    > {"phenomenonTime": "2018-12-04T14:18:11.376306+00:00", "resultTime": "2018-12-04T14:18:11.376503+00:00", "result": 50.05934369894213, "Datastream": {"@iot.id": 2}}

You can use the flag `--from-beginning` to see the whole recordings of the persistence time which are
two weeks by default.
After the tests, stop the services with:

    /kafka/bin/kafka-server-stop.sh
    /kafka/bin/zookeeper-server-stop.sh
    docker-compose -f setup/gost/docker-compose.yml down

If you want to remove the SensorThings instances from the GOST server, run `docker-compose down -v`.


## Deployment on a Cluster

To deploy the Digital Twin Platform on a cluster, see the 
[setup/README-Deployment.md](setup/README-Deployment.md) notes.


## Platform UI

The user interface is the recommended way to create system topics which happens when registering a new client,
and to deploy and stop stream-applications, that forwards selected data from one system to another.

### Starting the platform

Before starting the platform, make sure **postgresql** is installed and the configuration selected in `server/.env`
points to a appropriate config in `server/config`. For instructions on how to install postgres, this 
[site](https://www.digitalocean.com/community/tutorials/how-to-install-and-use-postgresql-on-ubuntu-18-04) may help.

```bash
cd server
sudo pip3 install virtualenv 
virtualenv venv 
source venv/bin/activate

pip3 install -r requirements.txt
sh start-server.sh
```

The platform is then, if the default developer-config is selected, available on [localhost:1908](localhost:1908)


![Platform](/extra/platform_home.png)

There are demo-accounts available for:
* sue.smith@example.com
* stefan.gunnarsson@example.com
* anna.gruber@example.com

The password of each user is `asdf`.

<br>
If you have feedback and ideas, please let me know.

Have fun exploring this project!
