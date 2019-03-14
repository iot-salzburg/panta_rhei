import os
import sys
import json
import pytz
import logging
import requests
from datetime import datetime

# confluent_kafka is based on librdkafka, details in install_kafka_requirements.sh
import confluent_kafka
from client.registerHelper import RegisterHelper
from client.type_mappings import type_mappings


class DigitalTwinClient:
    def __init__(self, client_name, system_prefix, system_name, kafka_bootstrap_servers, gost_servers):
        """
        Load config files
        Checks GOST server connection
        Checks and tests kafka broker connection
        """
        # Init logging
        self.logger = logging.getLogger("PR Client Logger")
        self.logger.setLevel(logging.INFO)
        logging.basicConfig(level='WARNING')
        self.logger.info("init: Initialising Digital Twin Client with name '{}' on '{}'".format(
            client_name, system_prefix+"."+system_name))

        # Load config
        self.config = {"client_name": client_name,
                       "system_prefix": system_prefix,
                       "system_name": system_name,
                       "kafka_bootstrap_servers": kafka_bootstrap_servers,
                       "gost_servers": gost_servers}

        # Check SensorThings connection
        self.logger.debug("init: Checking SensorThings connection")
        gost_url = "http://" + self.config["gost_servers"]
        res = requests.get(gost_url + "/v1.0/Things")
        if res.status_code in [200, 201, 202]:
            self.logger.info("init: Successfully connected to GOST server {}.".format(gost_servers))
        else:
            self.logger.error("init: Error, couldn't connect to GOST server: {}, status code: {}, result: {}".format(
                gost_servers, res.status_code, res.json()))
            sys.exit(10)

        # Create Kafka Producer
        self.logger.debug("init: Checking Kafka connection")
        self.mapping = dict()
        self.mapping["logging"] = {"name": "logging", "@iot.id": -1,
                                   "kafka-topic": "{}.{}.logging".format(self.config["system_prefix"],
                                                                         self.config["system_name"]),
                                   "observationType": "logging"}
        self.producer = confluent_kafka.Producer({'bootstrap.servers': self.config["kafka_bootstrap_servers"],
                                                  'client.id': self.config["client_name"],
                                                  'default.topic.config': {'acks': 'all'}})
        # Check if the topic exists
        if self.mapping["logging"]["kafka-topic"] not in self.producer.list_topics().topics.keys():
            self.logger.error("init: Error, topic '{}' doesn't exist in Kafka cluster, stopping client".format(
                self.mapping["logging"]["kafka-topic"]))
            sys.exit(20)
            # TODO How to create a topic via the client
            # a = confluent_kafka.admin.AdminClient({'bootstrap.servers': self.config["kafka_bootstrap_servers"]})
            # a.create_topics([confluent_kafka.admin.NewTopic("test.mytopic", 2, 1)])

        # Trigger any available delivery report callbacks from previous produce() calls
        self.producer.poll(0)
        data = dict({"phenomenonTime": datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat(),
                     "resultTime": datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat(),
                     "result": "Started Digital Twin Client with name '{}'".format(self.config["client_name"]),
                     "Datastream": {"@iot.id": self.mapping["logging"]["@iot.id"]}})
        self.producer.produce(self.mapping["logging"]["kafka-topic"], json.dumps(data).encode('utf-8'),
                              key=self.config["client_name"], callback=self.delivery_report_connection_check)
        # Wait for any outstanding messages to be delivered and delivery report
        # callbacks to be triggered.
        self.producer.flush()

        # Init other objects used in later methods
        self.subscribed_datastreams = None
        self.instances = None
        self.consumer = None

    def register(self, instance_file):
        """
        Post or path instances using the RegisterHanlder class.
        Create mapping to use the correct kafka topic for each datastream type.
        Create Kafka Producer instance.
        :param instance_file. Stores Things, Sensors and Datastreams+ObservedProperties, it also stores the structure
        :return:
        """
        # The RegisterHelper class does the whole register workflow
        register_helper = RegisterHelper(self.logger, self.config)
        self.instances = register_helper.register(instance_file)

        # Create Mapping to send on the correct data type: Generic logger and one for each datastream
        # value dict_keys(['@iot.id', 'name', 'description', 'unitOfMeasurement', 'observationType', 'Thing', 'Sensor'])
        for key, value in self.instances["Datastreams"].items():
            self.mapping[key] = {"name": value["name"],
                                 "@iot.id": value["@iot.id"],
                                 "Thing": value["Thing"],
                                 "observationType": value["observationType"]}
        self.logger.debug("register: Successfully loaded mapping: {}".format(self.mapping))

        self.send("logging", "Registered instances for Digital Twin Client '{}': {}".format(
            self.config["client_name"], self.mapping))
        self.logger.info("register: Registered instances for Digital Twin Client '{}': {}".format(
            self.config["client_name"], self.mapping))

    def send(self, quantity, result, timestamp=None):
        """
        Function that sends data of registered datastreams semantically annotated to the Digital Twin Messaging System
        :param quantity: Quantity of the Data
        :param result: The actual value without units. Can be boolean, integer, float, category or an object
        :param timestamp: either ISO 8601 or a 10,13,16 or 19 digit unix epoch format. If not given, it will
        be created.
        :return:
        """
        # check, if the quantity is registered
        if quantity not in self.mapping.keys():
            self.logger.error("send: Quantity is not registered: {}".format(quantity))
            sys.exit(30)

        data = dict({"phenomenonTime": self.get_iso8601_time(timestamp),
                     "resultTime": datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat(),
                     "Datastream": {"@iot.id": self.mapping[quantity]["@iot.id"]}})

        # check, if the type of the result is correct
        try:
            data["result"] = type_mappings[self.mapping[quantity]["observationType"]](result)
        except ValueError:
            self.logger.error("send: Error, incorrect type was recognized, result: {}, "
                              "result.type: {}, dedicated type (as registered): {}"
                              "".format(result, type(result), self.mapping[quantity]["observationType"]))
            sys.exit(31)

        # Trigger any available delivery report callbacks from previous produce() calls
        self.producer.poll(0)
        # Asynchronously produce a message, the delivery report callback
        # will be triggered from poll() above, or flush() below, when the message has
        # been successfully delivered or failed permanently.
        kafka_topic = "{}.{}.".format(self.config["system_prefix"], self.config["system_name"])
        if self.mapping[quantity]["observationType"] == "logging":
            kafka_topic += "logging"
        else:
            kafka_topic += "data"

        # The key is of the form "thing.data-type" or "client-name.logging"
        kafka_key = self.mapping[quantity].get("Thing", self.config["client_name"])
        kafka_key += "." + self.mapping[quantity].get("observationType", "logging")

        self.producer.produce(kafka_topic, json.dumps(data).encode('utf-8'), key=kafka_key,
                              callback=self.delivery_report)
        # Wait for any outstanding messages to be delivered and delivery report
        # callbacks to be triggered.
        self.producer.flush()

    @staticmethod
    def get_iso8601_time(timestamp):
        """
        This function converts multiple standard timestamps to ISO 8601 UTC datetime.
        The output is strictly in the following style: 2018-12-03T15:55:39.054752+00:00
        :param timestamp: either ISO 8601 or a 10,13,16 or 19 digit unix epoch format.
        :return: ISO 8601 format. e.g. 2018-12-03T15:55:39.054752+00:00
        """
        if timestamp is None:
            return datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat()
        if isinstance(timestamp, str):
            if timestamp.endswith("Z"):  # Expects the timestamp in the form of 2018-11-06T13:57:55.088294Z
                return datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=pytz.UTC).isoformat()
            else:  # Expects the timestamp in the form of  2018-11-06T13:57:55.088294+00:00
                return datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%f+00:00').replace(tzinfo=pytz.UTC).isoformat()

        if isinstance(timestamp, float):  # Expects the timestamp in the form of 1541514377.497349 (s)
            return datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.UTC).isoformat()

        if isinstance(timestamp, int):
            if timestamp < 1e12:  # Expects the timestamp in the form of 1541514377 (s)
                return datetime.utcfromtimestamp(timestamp).replace(tzinfo=pytz.UTC).isoformat()
            elif timestamp < 1e15:  # Expects the timestamp in the form of 1541514377497 (ms)
                return datetime.utcfromtimestamp(timestamp / 1e3).replace(tzinfo=pytz.UTC).isoformat()
            elif timestamp < 1e15:  # Expects the timestamp in the form of 1541514377497 (us)
                return datetime.utcfromtimestamp(timestamp / 1e6).replace(tzinfo=pytz.UTC).isoformat()
            else:  # Expects the timestamp in the form of 1541514377497349 (ns)
                return datetime.utcfromtimestamp(timestamp / 1e9).replace(tzinfo=pytz.UTC).isoformat()

    def delivery_report_connection_check(self, err, msg):
        """ Called only once to check the connection to kafka.
            Triggered by poll() or flush()."""
        if err is not None:
            self.logger.error("init: Kafka connection check to brokers '{}' Message delivery failed: {}".format(
                self.config["kafka_bootstrap_servers"], err))
            sys.exit(40)
        else:
            self.logger.info(
                "init: Successfully connected to the Kafka bootstrap server: {} with topic: '{}', partitions: [{}]"
                "".format(self.config["kafka_bootstrap_servers"], msg.topic(), msg.partition()))

    def delivery_report(self, err, msg):
        """ Called once for each message produced to indicate delivery result.
            Triggered by poll() or flush()."""
        if err is not None:
            self.logger.warning('delivery_report: Message delivery failed: {}'.format(err))
        else:
            self.logger.debug("delivery_report: Message delivered to topic: '{}', partitions: [{}]".format(
                msg.topic(), msg.partition()))

    def subscribe(self, subscription_file=None):
        """
        Create a Kafka consumer instance
        Subscribe to datastream names which are stored in the subscription_file. If not subscription file is found,
        and empty one is created
        Load metadata for subscribed datastreams from the GOST server and store in attributes
        :param subscription_file:
        :return:
        """
        self.logger.debug("subscribe: Subscribing on {}, loading instances".format(subscription_file))
        # {"subscribed_datastreams": ["domain.enterprise...system.thing.ds_1", ... ]}
        try:
            with open(subscription_file) as f:
                subscriptions = json.loads(f.read())
        except FileNotFoundError:
            self.logger.warning("subscribe: FileNotFound, creating empty subscription file")
            subscriptions = json.loads('{"subscribed_datastreams": []}')
        # Make structure pretty
        with open(subscription_file, "w") as f:
            f.write(json.dumps(subscriptions, indent=2))

        self.logger.info("subscribe: Subscribing to datastreams with names: {}".format(
            subscriptions["subscribed_datastreams"]))

        # Create Kafka Consumer instance
        conf = {'bootstrap.servers': self.config["kafka_bootstrap_servers"],
                'session.timeout.ms': 6000,
                'group.id': "{}.{}.{}".format(self.config["system_prefix"], self.config["system_name"],
                                              self.config["client_name"])}

        self.consumer = confluent_kafka.Consumer(**conf)
        self.consumer.subscribe([
            "{}.{}.data".format(self.config["system_prefix"], self.config["system_name"]),
            "{}.{}.external".format(self.config["system_prefix"], self.config["system_name"])])

        # get subscribed datastreams of the form:
        # {4: {'@iot.id': 4, 'name': 'Machine Temperature', '@iot.selfLink': 'http://...}, 5: {....}, ...}
        gost_url = "http://" + self.config["gost_servers"]
        # Sort datastreams to pick latest stream datastream in case of duplicates
        gost_datastreams = sorted(requests.get(gost_url + "/v1.0/Datastreams?$expand=Sensors,Thing,ObservedProperty")
                                  .json()["value"], key=lambda k: k["@iot.id"])
        self.subscribed_datastreams = {ds["@iot.id"]: ds for ds in gost_datastreams if ds["name"]
                                       in subscriptions["subscribed_datastreams"]}

        for key, value in self.subscribed_datastreams.items():
            self.logger.info("subscribe: Subscribed to datastream: id: {} and metadata: {}".format(key, value))
        if len(self.subscribed_datastreams.keys()) == 0:
            self.logger.warning("subscribe: No subscription matches an existing datastream.")
        for stream in subscriptions["subscribed_datastreams"]:
            if stream not in [subscribed_ds["name"] for subscribed_ds in self.subscribed_datastreams.values()]:
                self.logger.warning("subscribe: Couldn't subscribe to {}, may not be registered".format(stream))

    def poll(self, timeout=0.1):
        """
        Receives data from the Kafka topics. On new data, it checks if it is valid, filters for subscribed datastreams
        and returns the message augmented with datastream metadata.
        :param timeout: duration how long to wait to reveive data
        :return: either None or data in SensorThings format and augmented with metadata for each received and
        subscribed datastream. e.g.
        {'phenomenonTime': '2018-12-03T16:08:03.366855+00:00', 'resultTime': '2018-12-03T16:08:03.367045+00:00',
        'result': 50.44982168968592, 'Datastream': {'@iot.id': 4, ...}
        """
        msg = self.consumer.poll(timeout)  # Waits up to 'session.timeout.ms' for a message

        while msg is not None:
            if not msg.error():
                data = json.loads(msg.value().decode('utf-8'))
                iot_id = data.get("Datastream", None).get("@iot.id", None)
                if iot_id in self.subscribed_datastreams.keys():
                    data["Datastream"] = self.subscribed_datastreams[iot_id]
                    return data
            else:
                if msg.error().code() != confluent_kafka.KafkaError._PARTITION_EOF:
                    self.logger.error("poll: {}".format(msg.error()))

            msg = self.consumer.poll(0)  # Waits up to 'session.timeout.ms' for a message

    def disconnect(self):
        """
        Disconnect and close Kafka Connections
        :return:
        """
        try:
            self.producer.flush()
        except AttributeError:
            pass
        try:
            self.consumer.close()
        except AttributeError:
            pass
        self.logger.info("disconnect: Digital Twin Client disconnected")
