import os
import sys
import json
import pytz
import random
import logging
import requests
from datetime import datetime

# confluent_kafka is based on librdkafka, details in install_kafka_requirements.sh
import confluent_kafka

from panta_rhei.client.registerHelper import RegisterHelper
from panta_rhei.client.type_mappings import type_mappings


class DigitalTwinClient:
    def __init__(self, client_name, system, gost_servers, kafka_bootstrap_servers=None, kafka_rest_server=None):
        """
        Load config files
        Checks GOST server connection
        Checks and tests kafka broker connection
        """
        # Init logging
        self.logger = logging.getLogger("PR Client Logger")
        self.logger.setLevel(logging.INFO)
        # self.logger.setLevel(logging.DEBUG)
        logging.basicConfig(level='WARNING')
        self.logger.info("init: Initialising Digital Twin Client with name '{}' on '{}'".format(client_name, system))

        # Load config
        self.config = {"client_name": client_name,
                       "system": system,
                       "gost_servers": gost_servers,
                       "kafka_bootstrap_servers": kafka_bootstrap_servers,
                       "kafka_rest_server": kafka_rest_server,
                       # Use a randomized hash for an unique consumer id in an client-wide consumer group
                       "kafka_group_id": "{}.{}".format(system, client_name),
                       "kafka_consumer_id": "consumer_%04x" % random.getrandbits(16)}
        self.logger.debug("Config for client is: {}".format(self.config))

        # Check the connection to the SensorThings server
        self.logger.debug("init: Checking SenorThings server connection")
        self.check_gost_connection()

        # Create a mapping for each datastream of the client
        self.mapping = dict()
        self.mapping["logging"] = {"name": "logging", "@iot.id": -1,
                                   "kafka-topic": self.config["system"] + ".logging",
                                   "observationType": "logging"}

        # Check the connection to Kafka, note that the connection to the brokers are preferred
        self.logger.debug("init: Checking Kafka connection")
        self.producer = None
        self.check_kafka_connection()

        # Init other objects used in later methods
        self.subscribed_datastreams = None
        self.instances = None
        self.consumer = None

    def check_gost_connection(self):
        gost_url = "http://" + self.config["gost_servers"]
        try:
            res = requests.get(gost_url + "/v1.0/Things")
            if res.status_code in [200, 201, 202]:
                self.logger.info("init: Successfully connected to GOST server {}.".format(gost_url))
            else:
                self.logger.error("init: Error, couldn't connect to GOST server: {}, status code: {}, result: {}".
                                  format(gost_url, res.status_code, res.json()))
                raise ConnectionError("init: Error, couldn't connect to GOST server: {}, status code: {}, result: {}".
                                      format(gost_url, res.status_code, res.json()))
        except Exception as e:
            self.logger.error("init: Error, couldn't connect to GOST server: {}".format(gost_url))
            raise e

    def check_kafka_connection(self):
        # distinguish to connect to the kafka_bootstrap_servers (preferred) or to kafka_rest
        if self.config["kafka_bootstrap_servers"]:
            # Create Kafka Producer
            self.producer = confluent_kafka.Producer({'bootstrap.servers': self.config["kafka_bootstrap_servers"],
                                                      'client.id': self.config["client_name"],
                                                      'default.topic.config': {'acks': 'all'}})
            # TODO How to create a topic via the client
            # a = confluent_kafka.admin.AdminClient({'bootstrap.servers': self.config["kafka_bootstrap_servers"]})
            # a.create_topics([confluent_kafka.admin.NewTopic("test.mytopic", 2, 1)])

        else:
            kafka_rest_url = "http://" + self.config["kafka_rest_server"] + "/topics"
            try:
                res = requests.get(kafka_rest_url, headers=dict({"Accecpt": "application/vnd.kafka.v2+json"}))
                if res.status_code == 200 and self.mapping["logging"]["kafka-topic"] in res.json():
                    self.logger.info("init: Successfully connected to kafka-rest {}.".format(kafka_rest_url))
                else:
                    if res.status_code != 200:
                        self.logger.error("init: Error, couldn't connect to kafka-rest: {}, status code: {}, "
                                          .format(kafka_rest_url, res.status_code))
                    else:
                        self.logger.error("init: Error, topic '{}' doesn't exist in Kafka cluster, stopping client, "
                                          "return code {}".format(self.mapping["logging"]["kafka-topic"],
                                                                  res.status_code))
                    raise ConnectionError(
                        "init: Error, couldn't connect to kafka-rest: {}, status code: {}".format(
                            kafka_rest_url, res.status_code))
            except Exception as e:
                self.logger.error("init: Error, couldn't connect to kafka-rest: {}".format(kafka_rest_url))
                raise e

        self.produce("logging", "Started Digital Twin Client with name '{}'".format(self.config["client_name"]))

    def register_existing(self, mappings_file):
        """
        Create a mappings between internal and unique quantity ids
        :param mappings_file. Stores the mapping between internal and external quantity name
        :return:
        """
        try:
            with open(mappings_file) as f:
                mappings = json.loads(f.read())
        except FileNotFoundError:
            self.logger.warning("subscribe: FileNotFound, creating empty mappings file")
            mappings = json.loads('{"Datastreams": {}}')
        # Make structure pretty
        with open(mappings_file, "w") as f:
            f.write(json.dumps(mappings, indent=2))
        self.logger.debug("register: Loaded the datastream mapping: {}".format(mappings["Datastreams"]))

        # Get the datastreams of the form
        # {4: {'@iot.id': 4, 'name': 'Machine Temperature', '@iot.selfLink': 'http://...}, 5: {....}, ...}
        gost_url = "http://" + self.config["gost_servers"]
        # Sort datastreams to pick latest stream datastream in case of duplicates
        gost_datastreams = sorted(requests.get(gost_url + "/v1.0/Datastreams?$expand=Thing").json()["value"],
                                  key=lambda k: k["@iot.id"])

        for key, v in mappings["Datastreams"].items():
            unique_ds_name = self.config["system"] + "." + v["Thing"] + "." + v["name"]
            for ds in gost_datastreams:
                if unique_ds_name == ds["name"]:
                    self.mapping[key] = {"name": ds["name"],
                                         "@iot.id": ds["@iot.id"],
                                         "Thing": ds["Thing"].get("name", ds["Thing"]),
                                         "observationType": ds["observationType"]}

        self.logger.debug("register: Successfully loaded mapping: {}".format(self.mapping))
        msg = "Found registered instances for Digital Twin Client '{}': {}".format(self.config["client_name"],
                                                                                   self.mapping)
        self.produce("logging", msg)
        self.logger.info("register: " + msg)

    def register_new(self, instance_file):
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
        self.logger.debug("register_new: Successfully loaded mapping: {}".format(self.mapping))

        self.produce("logging", "Registered instances for Digital Twin Client '{}': {}".format(
            self.config["client_name"], self.mapping))
        self.logger.info("register_new: Registered instances for Digital Twin Client '{}': {}".format(
            self.config["client_name"], self.mapping))

    def produce(self, quantity, result, timestamp=None):
        """
        Function that sends data of registered datastreams semantically annotated to the Digital Twin Messaging System
        via the bootstrap_server (preferred) or kafka_rest
        :param quantity: Quantity of the Data
        :param result: The actual value without units. Can be boolean, integer, float, category or an object
        :param timestamp: either ISO 8601 or a 10,13,16 or 19 digit unix epoch format. If not given, it will
        be created.
        :return:
        """
        # check, if the quantity is registered
        if quantity not in self.mapping.keys():
            self.logger.error("send: Quantity is not registered: {}".format(quantity))
            raise Exception("send: Quantity is not registered: {}".format(quantity))

        data = dict({"phenomenonTime": self.get_iso8601_time(timestamp),
                     "resultTime": datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat(),
                     "Datastream": {"@iot.id": self.mapping[quantity]["@iot.id"]}})

        # check, if the type of the result is correct
        try:
            data["result"] = type_mappings[self.mapping[quantity]["observationType"]](result)
        except ValueError as e:
            self.logger.error("send: Error, incorrect type was recognized, result: {}, "
                              "result.type: {}, dedicated type (as registered): {}"
                              "".format(result, type(result), self.mapping[quantity]["observationType"]))
            raise e

        # Build the kafka-topic that is used
        # kafka_topic = "{}.{}.".format(self.config["system_prefix"], self.config["system_name"])
        if self.mapping[quantity]["observationType"] == "logging":
            kafka_topic = self.config["system"] + "." + "logging"
        else:
            kafka_topic = self.config["system"] + "." + "data"

        # The key is of the form "thing" or "client-name" (for logging)
        kafka_key = str(self.mapping[quantity].get("Thing", self.config["client_name"]))

        # Either send to kafka bootstrap, or to kafka rest endpoint
        if self.config["kafka_bootstrap_servers"]:
            self.send_to_kafka_bootstrap(kafka_topic, kafka_key, data)
        else:
            self.send_to_kafka_rest(kafka_topic, kafka_key, data)

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
            raise Exception("init: Kafka connection check to brokers '{}' Message delivery failed: {}".format(
                self.config["kafka_bootstrap_servers"], err))
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

    def send_to_kafka_bootstrap(self, kafka_topic, kafka_key, data):
        """
        Function that sends data to the kafka_bootstrap_servers
        :param kafka_topic: topic to which the data will sent
        :param kafka_key: key for the data
        :param data: data that is sent to the kafka bootstrap server
        :return:
        """
        # Trigger any available delivery report callbacks from previous produce() calls
        self.producer.poll(0)

        # Asynchronously produce a message, the delivery report callback
        # will be triggered from poll() above, or flush() below, when the message has
        # been successfully delivered or failed permanently.
        self.producer.produce(kafka_topic, json.dumps(data, separators=(',', ':')).encode('utf-8'),
                              key=json.dumps(kafka_key, separators=(',', ':')).encode('utf-8'),
                              callback=self.delivery_report)
        # Wait for any outstanding messages to be delivered and delivery report
        # callbacks to be triggered.
        self.producer.flush()

    def send_to_kafka_rest(self, kafka_topic, kafka_key, data):
        """
        Function that sends data to the kafka_rest_server
        :param kafka_topic: topic to which the data will sent
        :param kafka_key: key for the data
        :param data: data that is sent to the kafka bootstrap server
        :return:
        """
        # Build the payload
        data = json.dumps({"records": [{"key": kafka_key, "value": data}]}).encode("utf-8")

        # Post the data with headers to kafka-rest
        kafka_url = "http://{}/topics/{}".format(self.config["kafka_rest_server"], kafka_topic)
        try:
            res = requests.post(kafka_url, data=data, headers=dict(
                {'Content-type': 'application/vnd.kafka.json.v2+json',
                 'Accept': 'application/vnd.kafka.v2+json, application/vnd.kafka+json, application/json'}))
            if res.status_code == 200:
                self.logger.debug("produce: sent message to {}".format(kafka_url))
            else:
                self.logger.warning(
                    "produce: Couldn't post message to {}, status code: {}".format(kafka_url, res.status_code))
                raise ConnectionError("Couldn't post message to {}, status code: {}".format(kafka_url, res.status_code))
        except ConnectionError as e:
            self.logger.error("produce: Couldn't post message to {}".format(kafka_url))
            raise e

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

        # Either consume from kafka bootstrap, or to kafka rest endpoint
        if self.config["kafka_bootstrap_servers"]:
            # Create consumer
            conf = {'bootstrap.servers': self.config["kafka_bootstrap_servers"],
                    'session.timeout.ms': 6000,
                    'group.id': self.config["kafka_group_id"]}
            self.consumer = confluent_kafka.Consumer(**conf)

            # Subscribe to topics
            self.consumer.subscribe([self.config["system"] + ".data", self.config["system"] + ".external"])

        else:
            # Create consumer
            data = json.dumps({
                "name": self.config["kafka_consumer_id"],  # consumer name equals consumer group name
                "format": "json",
                "auto.offset.reset": "earliest",
                "auto.commit.enable": "true"}).encode("utf-8")
            kafka_url = "http://{}/consumers/{}".format(self.config["kafka_rest_server"], self.config["kafka_group_id"])
            res = requests.post(kafka_url, data=data, headers=dict({"Content-Type": "application/vnd.kafka.v2+json"}))
            if res.status_code == 200:
                self.logger.debug("subscribe: Created consumer instance '{}'".format(self.config["kafka_consumer_id"]))
            elif res.status_code == 409:
                self.logger.debug("subscribe: already created consumer instance")
            else:
                self.logger.error("subscribe: can't create consumer instance")
                raise Exception("subscribe: can't create consumer instance")

            # Subscribe to topics
            kafka_url = "http://{}/consumers/{}/instances/{}/subscription".format(
                self.config["kafka_rest_server"], self.config["kafka_group_id"], self.config["kafka_consumer_id"])
            data = json.dumps({"topics": [self.config["system"] + ".data", self.config["system"] + ".external"]}
                              ).encode("utf-8")
            res = requests.post(kafka_url, data=data,
                                headers=dict({"Content-Type": "application/vnd.kafka.json.v2+json"}))
            if res.status_code == 204:
                self.logger.debug("subscribe: Subscribed on topics: {}".format(json.loads(data)["topics"]))
            else:
                self.logger.error(
                    "subscribe: can't create consumer instance, status code: {}".format(res.status_code))
                raise Exception(
                    "subscribe: can't create consumer instance, status code: {}".format(res.status_code))

        # Check the subscriptions and create mapping
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

    def consume_via_bootstrap(self, timeout=0.1):
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
                    data["partition"] = msg.partition
                    data["topic"] = msg.topic
                    return data
            else:
                if msg.error().code() != confluent_kafka.KafkaError._PARTITION_EOF:
                    self.logger.error("poll: {}".format(msg.error()))
            msg = self.consumer.poll(0)  # Waits up to 'session.timeout.ms' for a message

    def consume(self, timeout=1):
        """
        Receives data from the Kafka topics directly via a bootstrap server (preferred) or via kafka rest.
        On new data, it checks if it is valid and filters for subscribed datastreams
        and returns a list of messages augmented with datastream metadata.
        :param timeout: duration how long to wait to receive data
        :return: either None or data in SensorThings format and augmented with metadata for each received and
        subscribed datastream. e.g.
        [{"topic": "eu.srfg.iot-iot4cps-wp5.car1.data","key": "eu.srfg.iot-iot4cps-wp5.car1.Demo Car 1",
        "value": {"phenomenonTime": "2019-04-08T09:47:35.408785+00:00","resultTime": "2019-04-08T09:47:35.408950+00:00",
        "Datastream": {"@iot.id": 11},"result": 2.9698054997459593},"partition": 0,"offset": 1},...]
        """
        # msg = self.consumer.poll(timeout)  # Waits up to 'session.timeout.ms' for a message
        if self.config["kafka_bootstrap_servers"]:
            payload = list()
            datapoint = self.consume_via_bootstrap(timeout)
            while datapoint is not None:
                payload.append(datapoint)
                datapoint = self.consume_via_bootstrap(0)
            return payload

        # Consume data via Kafka Rest
        else:
            kafka_url = "http://{}/consumers/{}/instances/{}/records?timeout={}&max_bytes=300000".format(
                self.config["kafka_rest_server"], self.config["kafka_group_id"],
                self.config["kafka_consumer_id"], int(timeout * 1000))

            response = requests.get(url=kafka_url, headers=dict({"Accept": "application/vnd.kafka.json.v2+json"}))
            if response.status_code != 200:
                self.logger.error("consume: can't get messages from {}, status code {}".format(kafka_url,
                                                                                               response.status_code))
                raise Exception("consume: can't get messages from {}".format(kafka_url))
            records = response.json()
            if not records:
                self.logger.debug("consume: got empty list")
                return list()
            payload = list()
            self.logger.debug("get: got {} new message(s)".format(len(records)))
            for record in records:
                iot_id = record.get("value", None).get("Datastream", None).get("@iot.id", None)
                if iot_id in self.subscribed_datastreams.keys():
                    datapoint = record["value"]
                    datapoint["Datastream"] = self.subscribed_datastreams[iot_id]
                    payload.append(datapoint)
                    self.logger.debug("Received new datapoint: '{}'".format(datapoint))
            return payload

    def disconnect(self):
        """
        Disconnect and close Kafka Connections
        :return:
        """
        if self.config["kafka_bootstrap_servers"]:
            try:
                self.producer.flush()
            except AttributeError:
                pass
            try:
                self.consumer.close()
            except AttributeError:
                pass
        else:
            kafka_url = "http://{}/consumers/{}/instances/{}".format(
                self.config["kafka_rest_server"], self.config["kafka_group_id"], self.config["kafka_consumer_id"])
            # try:
            res = requests.delete(kafka_url, headers=dict({"Content-Type": "application/vnd.kafka.v2+json"}))
            if res.status_code == 204:
                self.logger.info("disconnect: Removed consumer instance.")
            else:
                self.logger.error(
                    "subscribe: can't remove consumer instance, status code: {}.".format(res.status_code))
            # except Exception as e:
            #     self.logger.error("subscribe: can't remove consumer instance.")
        self.logger.info("disconnect: Digital Twin Client disconnected")
