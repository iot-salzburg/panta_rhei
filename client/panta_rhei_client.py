import os
import json
import logging
import requests
import sys
import pytz
from datetime import datetime

# confluent_kafka is based on librdkafka, details in requirements.txt
import confluent_kafka


class PantaRheiClient:
    def __init__(self, client_name):
        """
        Load config files
        Checks GOST server connection
        Checks and tests kafka broker connection
        """
        # Init logging
        self.client_name = client_name  # is used as group_id
        self.logger = logging.getLogger("PR Client Logger")
        self.logger.setLevel(logging.INFO)
        logging.basicConfig(level='WARNING')

        self.logger.info("init: Initialising Panta Rhei Client with name: {}".format(client_name))

        # Load config.json and drop comments
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        with open(config_file) as f:
            self.config = json.loads(f.read())
            self.config.pop("_comment", None)
            self.logger.info("init: Successfully loaded configs.")

        type_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "type_mappings.json")
        with open(type_file) as f:
            self.type_mapping = json.loads(f.read())
            self.type_mapping.pop("_comment", None)
            self.logger.info("init: Successfully loaded type mappings.")

        # Check Sensorthings connection
        self.logger.info("init: Checking Sensorthings connection")
        gost_url = "http://" + self.config["GOST_SERVER"] + ":" + self.config["GOST_PORT"]
        res = requests.get(gost_url + "/v1.0/Things")
        if res.status_code in [200, 201, 202]:
            self.logger.info("init: Successfully connected to GOST server {}.".format(gost_url))
        else:
            self.logger.error("init: Error, couldn't connect to GOST server: {}, status code: {}, result: {}".format(
                gost_url, res.status_code, res.json()))
            sys.exit(1)

        # # Init Kafka, test for KAFKA_TOPICS_LOGS with an unique group.id
        #     self.logger.info("Checking Kafka connection")
        # # conf = {'bootstrap.servers': self.config["BOOTSTRAP_SERVERS"], 'group.id': self.client_name}
        # # consumer = confluent_kafka.Consumer(**conf)
        # # TODO Check if that is valid and also return for the first adapter a valid solution.
        # check_group_id = str(hash(self.client_name + "_" + str(time.time())))[-3:]  # Use a 3 digit hash
        # conf = {'bootstrap.servers': self.config["BOOTSTRAP_SERVERS"],
        #         'session.timeout.ms': 6000,
        #         'group.id': check_group_id}
        # consumer = confluent_kafka.Consumer(**conf)
        # consumer.subscribe([self.config["KAFKA_TOPIC_LOGS"]])
        # msg = consumer.poll()  # Waits up to 'session.timeout.ms' for a message
        # if msg is not None:
        #     # print(msg.value().decode('utf-8'))
        #     self.logger.info("init: Successfully connected to the Kafka Broker: {}".format(
        #     self.config["BOOTSTRAP_SERVERS"]))
        # else:
        #     self.logger.warning(init: "Error, couldn't connect to Kafka Broker: {}".format(
        #     self.config["BOOTSTRAP_SERVERS"]))
        # consumer.close()

        self.instances = dict()
        self.mapping = dict()
        self.subscribed_datastreams = None
        self.producer = None
        self.consumer = None

    def register(self, instance_file):
        """
        Opens instance file with Things, Sensors and Datastreams+ObservedProperties
        create requests
        check if gost entries exists each for
            Things
            Sensors
            Datastreams+Obs + Thing + Sensor
        If they exist: make patches
        Else: make posts and create the instance new
        :param instance_file. Stores Things, Sensors and Datastreams+ObservedProperties, it also stores the structure
        :return:
        """
        self.logger.info("register: Loading instances")
        # Things: ['demo_thing']
        # Sensors: ['demo_sensor']
        # Datastreams: ['demo_quantity0', 'demo_quantity1']
        with open(instance_file) as f:
            instances = json.loads(f.read())
        # Make structure pretty
        with open(instance_file, "w") as f:
            f.write(json.dumps(instances, indent=2))

        gost_url = "http://" + self.config["GOST_SERVER"] + ":" + self.config["GOST_PORT"]

        # Register Things. Patch or post
        self.logger.info("register: Register Things")
        gost_things = requests.get(gost_url + "/v1.0/Things").json()
        gost_thing_list = [thing["name"] for thing in gost_things["value"]]
        for thing in instances["Things"].keys():
            name = instances["Things"][thing]["name"]
            self.logger.info("register: Thing: {}, GOST name: {}".format(thing, name))
            # PATCH thing
            if name in gost_thing_list:
                idx = [gost_thing for gost_thing in gost_things["value"] if name == gost_thing["name"]][0]["@iot.id"]
                uri = gost_url + "/v1.0/Things({})".format(idx)
                self.logger.debug("register: Make a patch of: {}".format(json.dumps(instances["Things"][thing]["name"],
                                                                                    indent=2)))
                res = requests.patch(uri, json=instances["Things"][thing])
            # POST thing
            else:
                self.logger.debug("register: Make a post of: {}".format(json.dumps(instances["Things"][thing]["name"],
                                                                                   indent=2)))
                uri = gost_url + "/v1.0/Things"
                res = requests.post(uri, json=instances["Things"][thing])

            # Test if everything worked
            if res.status_code in [200, 201, 202]:
                self.logger.info(
                    "register: Successfully upsert the Thing: {} with the URI: {} and status code: {}".format(
                        name, uri, res.status_code))
                instances["Things"][thing] = res.json()

            else:
                self.logger.warning(
                    "register: Problems in upserting Things on instance: {}, with URI: {}, status code: {}, "
                    "payload: {}".format(name, uri, res.status_code, json.dumps(res.json(), indent=2)))

        # Register Sensors. Patch or post
        self.logger.info("register: Register Sensors")
        gost_sensors = requests.get(gost_url + "/v1.0/Sensors").json()
        gost_sensor_list = [sensor["name"] for sensor in gost_sensors["value"]]
        for sensor in instances["Sensors"].keys():
            name = instances["Sensors"][sensor]["name"]
            self.logger.info("register: Sensor: {}, GOST name: {}".format(sensor, name))
            status_max = 0
            res = None
            # PATCH sensor
            if name in gost_sensor_list:
                idx = [gost_sensor for gost_sensor in gost_sensors["value"]
                       if name == gost_sensor["name"]][0]["@iot.id"]
                uri = gost_url + "/v1.0/Sensors({})".format(idx)
                # Sensors can only be patched line by line
                for arg in list(instances["Sensors"][sensor]):
                    body = dict({arg: instances["Sensors"][sensor][arg]})
                    res = requests.patch(uri, json=body)
                    status_max = max(res.status_code, status_max)  # Show the maximal status

            # POST sensor
            else:
                self.logger.debug("Make a post of: {}".format(json.dumps(instances["Sensors"][sensor]["name"],
                                                                         indent=2)))
                uri = gost_url + "/v1.0/Sensors"
                res = requests.post(uri, json=instances["Sensors"][sensor])
                status_max = max(res.status_code, status_max)
            # Test if everything worked
            if status_max in [200, 201, 202]:
                self.logger.info(
                    "register: Successfully upsert the Sensors: {} with the URI: {} and status code: {}".format(
                        name, uri, status_max))
                instances["Sensors"][sensor] = res.json()
            else:
                self.logger.warning(
                    "register: Problems to upsert Sensors on instance: {}, with URI: {}, status code: {}, "
                    "payload: {}".format(name, uri, status_max, json.dumps(res.json(), indent=2)))

        # TODO Register Observation property extra
        # Register Datastreams with observation. Patch or post
        self.logger.info("register: Register Datastreams")
        gost_datastreams = requests.get(gost_url + "/v1.0/Datastreams").json()
        gost_datastream_list = [datastream["name"] for datastream in gost_datastreams["value"]]
        for datastream in instances["Datastreams"].keys():
            name = instances["Datastreams"][datastream]["name"]
            self.logger.info("register: Datastream: {}, GOST name: {}".format(datastream, name))

            dedicated_thing = instances["Datastreams"][datastream]["Thing"]
            dedicated_sensor = instances["Datastreams"][datastream]["Sensor"]
            body = instances["Datastreams"][datastream]
            body["Thing"] = dict({"@iot.id": instances["Things"][dedicated_thing]["@iot.id"]})
            body["Sensor"] = dict({"@iot.id": instances["Sensors"][dedicated_sensor]["@iot.id"]})

            # Deep patch is not supported, no Thing, Sensor or Observed property
            # PATCH thing
            if name in gost_datastream_list:
                idx = [gost_datastreams for gost_datastreams in gost_datastreams["value"]
                       if name == gost_datastreams["name"]][0]["@iot.id"]
                uri = gost_url + "/v1.0/Datastreams({})".format(idx)
                self.logger.info("register: Make a patch of: {}".format(
                    json.dumps(instances["Datastreams"][datastream]["name"], indent=2)))

                instances["Datastreams"][datastream].pop("Thing", None)
                instances["Datastreams"][datastream].pop("Sensor", None)
                instances["Datastreams"][datastream].pop("ObservedProperty", None)
                res = requests.patch(uri, json=instances["Datastreams"][datastream])
            # POST datastream
            else:
                self.logger.info("register: Make a post of: {}".format(json.dumps(
                    instances["Datastreams"][datastream]["name"], indent=2)))
                uri = gost_url + "/v1.0/Datastreams"
                res = requests.post(uri, json=instances["Datastreams"][datastream])

            # Test if everything worked
            if res.status_code in [200, 201, 202]:
                self.logger.info(
                    "register: Successfully upsert the Datastreams: {} with the URI: {} and status code: {}".format(
                        name, uri, res.status_code))
                instances["Datastreams"][datastream] = res.json()
            else:
                self.logger.warning(
                    "register: Problems to upsert Datastreams on instance: {}, with URI: {}, status code: {}, "
                    "payload: {}".format(name, uri, res.status_code, json.dumps(res.json(), indent=2)))

        self.instances = instances
        self.logger.info("register: Successfully registered instances:")
        for key in list(self.instances.keys()):
            items = [{"name": key, "@iot.id": value["@iot.id"]} for key, value in list(self.instances[key].items())]
            self.logger.info("register: {}".format(items))

        # Create Mapping to send on the correct data type
        for key, value in self.instances["Datastreams"].items():
            self.mapping[key] = {"name": value["name"],
                                 "@iot.id": value["@iot.id"],
                                 "type": self.type_mapping[value["observationType"]]}
        self.logger.info("register: Successfully loaded mapping")

        # Create Kafka Producer
        self.producer = confluent_kafka.Producer({'bootstrap.servers': self.config["BOOTSTRAP_SERVERS"]})
        self.logger.info("register: Successfully created Kafka Producer")

    def send(self, quantity, result, timestamp=None):
        """
        Function that sends data of registered datastreams semantically annotated to the Panta Rhei Messaging System
        :param quantity: Quantity of the Data
        :param result: The actual value without units. Can be boolean, integer, float, category or an object
        :param timestamp: either ISO 8601 or a 10,13,16 or 19 digit unix epoch format. If not given, it will
        be created.
        :return:
        """
        try:
            data_type = self.mapping[quantity]["type"]
        except KeyError:
            self.logger.error("send: Quantity is not registered: {}".format(quantity))
            sys.exit(1)

        # TODO differentiate better, create more topics. View desktop file
        if data_type in ["boolean", "integer", "double", "string", "object"]:
            kafka_topic = self.config["KAFKA_TOPIC_METRIC"]
        elif data_type == "logging":
            kafka_topic = self.config["KAFKA_TOPIC_LOGGING"]
        else:
            kafka_topic = self.config["KAFKA_TOPIC_LOGGING"]

        timestamp = self.get_iso8601_time(timestamp)

        data = dict({"phenomenonTime": timestamp,
                     "resultTime": datetime.utcnow().replace(tzinfo=pytz.UTC).isoformat(),
                     "result": result,
                     "Datastream": {"@iot.id": self.mapping[quantity]["@iot.id"]}})

        # Trigger any available delivery report callbacks from previous produce() calls
        self.producer.poll(0)
        # Asynchronously produce a message, the delivery report callback
        # will be triggered from poll() above, or flush() below, when the message has
        # been successfully delivered or failed permanently.
        self.producer.produce(kafka_topic, json.dumps(data).encode('utf-8'), key=self.client_name,
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
        self.logger.info("subscribe: Subscribing on {}, loading instances".format(subscription_file))
        # {"subscribed_ds": ["ds_1", ... ]}
        try:
            with open(subscription_file) as f:
                subscriptions = json.loads(f.read())
        except FileNotFoundError:
            self.logger.warning("subscribe: FileNotFound, creating empty subscription file")
            subscriptions = json.loads('{"subscribed_ds": []}')
        # Make structure pretty
        with open(subscription_file, "w") as f:
            f.write(json.dumps(subscriptions, indent=2))

        self.logger.info("subscribe: Subscribing to datastreams with names: {}".format(subscriptions["subscribed_ds"]))

        # Create Kafka Consumer instance
        conf = {'bootstrap.servers': self.config["BOOTSTRAP_SERVERS"],
                'session.timeout.ms': 6000,
                'group.id': self.client_name}
        self.consumer = confluent_kafka.Consumer(**conf)
        self.consumer.subscribe([self.config["KAFKA_TOPIC_METRIC"], self.config["KAFKA_TOPIC_LOGGING"]])

        # get subscribed datastreams of the form:
        # {4: {'@iot.id': 4, 'name': 'Machine Temperature', '@iot.selfLink': 'http://...}, 5: {....}, ...}
        gost_url = "http://" + self.config["GOST_SERVER"] + ":" + self.config["GOST_PORT"]
        gost_datastreams = requests.get(gost_url + "/v1.0/Datastreams").json()["value"]
        self.subscribed_datastreams = {ds["@iot.id"]: ds for ds in gost_datastreams if ds["name"]
                                       in subscriptions["subscribed_ds"]}
        # self.subscribed_datastreams_full = dict()
        # TODO augment with Sensor and Thing data
        for key, value in self.subscribed_datastreams.items():
            self.logger.info("subscribe: Subscribed to datastream: id: {}, definition: {}".format(key, value))
        if len(self.subscribed_datastreams.keys()) == 0:
            self.logger.info("subscribe: No subscription matches an existing datastream.")

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

        if msg is None:
            pass
        elif not msg.error():
            data = json.loads(msg.value().decode('utf-8'))
            iot_id = data.get("Datastream", None).get("@iot.id", None)
            if iot_id in self.subscribed_datastreams.keys():
                data["Datastream"] = self.subscribed_datastreams[iot_id]
                return data
        else:
            if msg.error().code() == confluent_kafka.KafkaError._PARTITION_EOF:
                # self.logger.warning("poll: confluent_kafka.KafkaError._PARTITION_EOF exception")
                pass
            else:
                self.logger.error("poll: {}".format(msg.error()))

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
        self.logger.info("disconnect: Panta Rhei Client successfully disconnected")
