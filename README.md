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


This is an instruction on how to set up a demo scenario on your own hardware.
Here, we use Ubuntu 18.04, for other OS there might have to be made adaptions.

 
### 2) Setup **Apache Kafka** and it's library:

The easiest way to set up a cluster for Apache Kafka is via Docker and docker-compose. 
Deploy each three instances of Kafka and its underlying Zookeeper on the same node via:

cd setup/kafka
docker-compose up -d

The flag -d stands for daemon mode. The containers can be investigated (stopped) 
via docker-compose logs (down). Three instances of Kafka are then available, each 
on the ports 9092, 9093 and 9094. Therefore, a replication factor of up to three is 
possible using this setup.


In case one doesn’t want to install Kafka via Docker (as it is suggested for production), 
the installation can also be done directly. The Datastack uses Kafka version 2.3.1 as the 
communication layer, the installation is done in `/kafka`.

```bash
sudo apt-get update
sh setup/kafka/install-kafka-2v1.sh
sh setup/kakfa/install-kafka-libs-2v1.sh
# optional:
export PATH=/kafka/bin:$PATH
sudo chown -R user.group /tmp/kafka-logs/
sudo chown -R user.group /tmp/zookeeper/
```

Then, start Zookeeper and Kafka and test the installation: 
(If the setup was done using Docker one can skip the Start-step)

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
If that works as described, you can create the default topics for the platform using:

 ```bash
bash setup/kafka/create_defaults.sh
/kafka/bin/kafka-topics.sh --zookeeper localhost:2181 --list
```

If multiple topics were generated, everything worked well.


### 3) Setup **SensorThings Server (GOST)** to add semantics:

    docker-compose -f setup/gost/docker-compose.yml up -d

The flag `-d` stands for `daemon` mode. To check if everything worked well, open
[http://localhost:8082/](http://localhost:8082/) or view the logs:

    docker-compose -f setup/gost/docker-compose.yml logs -f




### 3) Postgres setup

Before starting the platform, make sure postgreSQL is installed and the configuration 
selected in `server/.env` points to an appropriate config in `server/config`. 
For instructions on how to install postgres, various tutorials can be found in the Internet.

```bash
sudo apt install libpq-dev
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get install postgresql

sudo -u postgres psql
postgres=# CREATE ROLE iot4cps LOGIN PASSWORD 'iot4cps';
postgres=# CREATE DATABASE iot4cps OWNER iot4cps;
```

### 5) Install the pip packages and start the platform

Make sure to start a new virtual env for this setup! Then, install the python modules via:

```bash
pip3 install -r setup/requirements.txt
```


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
    python3 demo_applications/WeatherService/forecast_service/forecast-service.py 

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
   
   
### Streaming Applications

As there are two different types of stream apps that are based on different technologies, 
we have to distinguish:

#### Single-Source streaming applications

Single-Source streaming applications are implemented in Java using the Kafka Streams library. A pre- built jar file to share data from a specific tenant to others can be started with:

    java -jar server/StreamHub/target/streamApp-1.1-jar-with-dependencies.jar --stream-name mystream --source-system is.iceland.iot4cps-wp5-WeatherService.Stations is.iceland.iot4cps-wp5-WeatherService.Services --filter-logic “SELECT * FROM * WHERE result < 4;” --bootstrap-server 127.0.0.1:9092

If you want to change the streamhub application itself, modify and rebuild the java project in 
`server/StreamHub/src/main/java/com/github/christophschranz/iot4cpshub/StreamAppEngine.java`.
It is recommended, to start and stop the stream-applications via the Platform UI, that provides 
the same functionality as the command line interface.

#### Multi-Source streaming applications

Multi-Source streaming applications are implemented in Python, plain Apache Kafka and is based 
on the Time-Series join that is implemented using the LocalStreamBuffer algorithm. The stream 
app can be started using:

    python3 server/TimeSeriesJoiner/stream_join_engine.py


This script uses the customization set in `server/TimeSeriesJoiner/customization/custom_fct.py` 
which contains all required constants and two functions *ingest_fct* and *on_join* that suffice 
to customize the stream app’s behaviour. 
For more information read the README file in the `server/TimeSeriesJoiner/` sub-project or
view the customization-file `custom_fct.py`.


    
## Track what happens behind the scenes:

Check the created kafka topics:

    /kafka/bin/kafka-topics.sh --zookeeper localhost:2181 --list
    at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics.ext
    at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics.int
    at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics.log
    at.mfc.iot4cps-wp5-WeatherService.Stations.ext
    at.mfc.iot4cps-wp5-WeatherService.Stations.int
    at.mfc.iot4cps-wp5-WeatherService.Stations.log
    cz.icecars.iot4cps-wp5-CarFleet.Car1.ext
    cz.icecars.iot4cps-wp5-CarFleet.Car1.int
    cz.icecars.iot4cps-wp5-CarFleet.Car1.log
    cz.icecars.iot4cps-wp5-CarFleet.Car2.ext
    cz.icecars.iot4cps-wp5-CarFleet.Car2.int
    cz.icecars.iot4cps-wp5-CarFleet.Car2.log
    is.iceland.iot4cps-wp5-WeatherService.Services.ext
    is.iceland.iot4cps-wp5-WeatherService.Services.int
    is.iceland.iot4cps-wp5-WeatherService.Services.log
    is.iceland.iot4cps-wp5-WeatherService.Stations.ext
    is.iceland.iot4cps-wp5-WeatherService.Stations.int
    is.iceland.iot4cps-wp5-WeatherService.Stations.log
    test-topic

Note that kafka-topics must be created manually as explained in the [Setup](#setup-messaging-layer).

To track the traffic in real time, use the `kafka-consumer-console`: 

    /kafka/bin/kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic cz.icecars.iot4cps-wp5-CarFleet.Car1.int
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


## Known issues

* No authorization in Kafka

* Security risk for multi-source stream-apps


## TODO

* Secure data streaming via Kafka SSL, TLS.
	It should be possible, that only a client with the correct secrets/keys can publish and 
	consume data.

* Registration of Assets (including metadata), sensors, datastreams, …
	Based on the GOST server at the moment (maybe later i-Asset registry or KSQL)
	It should be possible to register all instances on the platform with a GOST backend. 
	(that is already done within the gost dashboard..)

* Update client applications for SSL and TLS.
	Make the setup work for existing Kafka Topics and ACL.

* Add ACL (access list) management
	Update the ACL when a system is created and removed.
	
	
* Make client-side communication exactly-once (requires broker replicas) and 
the producers even idempotent.

* Abstract the custom_fct of the multi-source stream apps to a SQL-like filter logic 
with minimal permissions and unify it with that from the singe-source stream app. 
(see [QCL](https://de.wikipedia.org/wiki/Continuous_Query_Language))

* Close the multi-source stream-app security leak. Any stream can be subscribed in it, 
this needs an update of the platform data-model with added viewers or a stream-app grant policy.

* Use the pr_client in the multi-source stream-app or extract the name id. 
This is only needed if the message key is not the name.

* Use the unique datastream namespace as message key. 
Replace Sensorthings by an alternative or by i-Asset's registry.

* Handle logging, publish states of clients and enable to subscribe to logs.

* Add Client-Adapter-Hub for bidirectional MQTT-Platform communication either in Docker container
within the platform, or as installation on the user side.

* Consideration of Kafka Registry usage in the platform to describe the payload semantic.


<br>
If you have feedback and ideas, please let me know.

Have fun exploring this project!
