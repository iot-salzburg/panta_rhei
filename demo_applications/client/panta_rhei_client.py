import os
import json
import time
import logging
import requests
import sys
import pytz
from datetime import datetime

# confluent_kafka is based on librdkafka, details in requirements.txt
import confluent_kafka


class PantaRheiClient:
    def __init__(self):
        """
        Inits logger and configs
        Checks gost server connection
        Checks and tests kafka broker connection
        """
        # Init logging
        self.logger = logging.getLogger("PR Client Logger")
        self.logger.setLevel(logging.INFO)
        logging.basicConfig(level='WARNING')

        self.logger.info("Initialising Panta Rhei Client.")

        # Load config.json and drop comments
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        with open(config_file) as f:
            self.config = json.loads(f.read())
            self.config.pop("_comment", None)
            self.logger.info("Successfully loaded configs.")

        type_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "type_mappings.json")
        with open(type_file) as f:
            self.type_mapping = json.loads(f.read())
            self.type_mapping.pop("_comment", None)
            self.logger.info("Successfully loaded type mappings.")

        # Check Sensorthings connection
            self.logger.info("Checking Sensorthings connection")
        gost_url = "http://" + self.config["GOST_SERVER"] + ":" + self.config["GOST_PORT"]
        res = requests.get(gost_url + "/v1.0/Things")
        if res.status_code in [200, 201, 202]:
            self.logger.info("Successfully connected to GOST server {}.".format(gost_url))
        else:
            self.logger.error("Error, couldn't connect to GOST server: {}, status code: {}, result: {}".format(
                gost_url, res.status_code, res.json()))

        # # Init Kafka, test for KAFKA_TOPICS_LOGS with an unique group.id
        #     self.logger.info("Checking Kafka connection")
        # # conf = {'bootstrap.servers': self.config["BOOTSTRAP_SERVERS"], 'group.id': self.config["KAFKA_GROUP_ID"]}
        # # consumer = confluent_kafka.Consumer(**conf)
        # # TODO Check if that is valid and also return for the first adapter a valid solution.
        # check_group_id = str(hash(self.config["KAFKA_GROUP_ID"] + "_" + str(time.time())))[-3:]  # Use a 3 digit hash
        # conf = {'bootstrap.servers': self.config["BOOTSTRAP_SERVERS"],
        #         'session.timeout.ms': 6000,
        #         'group.id': check_group_id}
        # consumer = confluent_kafka.Consumer(**conf)
        # consumer.subscribe([self.config["KAFKA_TOPIC_LOGS"]])
        # msg = consumer.poll()  # Waits up to 'session.timeout.ms' for a message
        # if msg is not None:
        #     # print(msg.value().decode('utf-8'))
        #     self.logger.info("Successfully connected to the Kafka Broker: {}".format(self.config["BOOTSTRAP_SERVERS"]))
        # else:
        #     self.logger.warning("Error, couldn't connect to Kafka Broker: {}".format(self.config["BOOTSTRAP_SERVERS"]))
        # consumer.close()

        self.instances = dict()
        self.mapping = dict()

    def register(self, instance_file):
        """
        Opens structure and instances.
        create requests
        check if gost entries exists
            Things
            Sensors
            Datastreams+Obs + Thing + Sensor
        make patches if they exist
        make posts

        return ids into structure
        :param instance_file, it also holds the structure
        :return:
        """
        self.logger.info("Loading instances")
        # Things: ['demo_thing']
        # Sensors: ['demo_sensor']
        # Datastreams: ['demo_quantity0', 'demo_quantity1']
        with open(instance_file) as f:
            instances = json.loads(f.read())
        # Make structure pretty
        with open(instance_file, "w") as f:
            f.write(json.dumps(instances, indent=2))

        self.logger.info("")
        self.logger.info("Register structure")
        gost_url = "http://" + self.config["GOST_SERVER"] + ":" + self.config["GOST_PORT"]

        # Register Things. Patch or post
        gost_things = requests.get(gost_url + "/v1.0/Things").json()
        gost_thing_list = [thing["name"] for thing in gost_things["value"]]
        for thing in instances["Things"].keys():
            name = instances["Things"][thing]["name"]
            self.logger.info("Register: {}, GOST name: {}".format(thing, name))
            # PATCH thing
            if name in gost_thing_list:
                idx = [gost_thing for gost_thing in gost_things["value"] if name == gost_thing["name"]][0]["@iot.id"]
                uri = gost_url + "/v1.0/Things({})".format(idx)
                self.logger.debug("Make a patch of: {}".format(json.dumps(instances["Things"][thing]["name"], indent=2)))
                res = requests.patch(uri, json=instances["Things"][thing])
            # POST thing
            else:
                self.logger.debug("Make a post of: {}".format(json.dumps(instances["Things"][thing]["name"], indent=2)))
                uri = gost_url + "/v1.0/Things"
                res = requests.post(uri, json=instances["Things"][thing])

            # Test if everything worked
            if res.status_code in [200, 201, 202]:
                self.logger.info(
                    "Successfully upsert the Thing: {} with the URI: {} and status code: {}".format(
                        name, uri, res.status_code))
                instances["Things"][thing] = res.json()

            else:
                self.logger.warning(
                    "Problems to upsert Things on instance: {}, with URI: {}, status code: {}, payload: {}".format(
                        name, uri, res.status_code, json.dumps(res.json(), indent=2)))

        # Register Sensors. Patch or post
        gost_sensors = requests.get(gost_url + "/v1.0/Sensors").json()
        gost_sensor_list = [sensor["name"] for sensor in gost_sensors["value"]]
        for sensor in instances["Sensors"].keys():
            name = instances["Sensors"][sensor]["name"]
            self.logger.info("Register: {}, GOST name: {}".format(sensor, name))
            status_max = 0
            # PATCH sensor
            if name in gost_sensor_list:
                idx = [gost_sensor for gost_sensor in gost_sensors["value"] if name == gost_sensor["name"]][0]["@iot.id"]
                uri = gost_url + "/v1.0/Sensors({})".format(idx)
                # Sensors can only be patched line by line
                for arg in list(instances["Sensors"][sensor]):
                    body = dict({arg: instances["Sensors"][sensor][arg]})
                    res = requests.patch(uri, json=body)
                    status_max = max(res.status_code, status_max)  # Show the maximal status
            # POST sensor
            else:
                self.logger.debug("Make a post of: {}".format(json.dumps(instances["Sensors"][sensor]["name"], indent=2)))
                uri = gost_url + "/v1.0/Sensors"
                res = requests.post(uri, json=instances["Sensors"][sensor])
                status_max = max(res.status_code, status_max)
            # Test if everything worked
            if status_max in [200, 201, 202]:
                self.logger.info(
                    "Successfully upsert the Sensors: {} with the URI: {} and status code: {}".format(
                        name, uri, status_max))
                instances["Sensors"][sensor] = res.json()
            else:
                self.logger.warning(
                    "Problems to upsert Sensors on instance: {}, with URI: {}, status code: {}, payload: {}".format(
                        name, uri, status_max, json.dumps(res.json(), indent=2)))

        # TODO Register Oberservation property extra

        # Register Datastreams with observation. Patch or post
        gost_datastreams = requests.get(gost_url + "/v1.0/Datastreams").json()
        gost_datastream_list = [datastream["name"] for datastream in gost_datastreams["value"]]
        for datastream in instances["Datastreams"].keys():
            name = instances["Datastreams"][datastream]["name"]
            self.logger.info("Register: {}, GOST name: {}".format(datastream, name))

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
                self.logger.info("Make a patch of: {}".format(
                    json.dumps(instances["Datastreams"][datastream]["name"], indent=2)))

                instances["Datastreams"][datastream].pop("Thing", None)
                instances["Datastreams"][datastream].pop("Sensor", None)
                instances["Datastreams"][datastream].pop("ObservedProperty", None)
                res = requests.patch(uri, json=instances["Datastreams"][datastream])
            # POST datastream
            else:
                self.logger.info("Make a post of: {}".format(json.dumps(instances["Datastreams"][datastream]["name"], indent=2)))
                uri = gost_url + "/v1.0/Datastreams"
                res = requests.post(uri, json=instances["Datastreams"][datastream])

            # Test if everything worked
            if res.status_code in [200, 201, 202]:
                self.logger.info(
                    "Successfully upsert the Datastreams: {} with the URI: {} and status code: {}".format(
                        name, uri, res.status_code))
                instances["Datastreams"][datastream] = res.json()
            else:
                self.logger.warning(
                    "Problems to upsert Datastreams on instance: {}, with URI: {}, status code: {}, payload: {}".format(
                        name, uri, res.status_code, json.dumps(res.json(), indent=2)))

        self.instances = instances
        self.logger.info("Successfully registered instances:")
        for key in list(self.instances.keys()):
            items = [{"name": key, "@iot.id": value["@iot.id"]} for key, value in list(self.instances[key].items())]
            self.logger.info(items)

        for key, value in self.instances["Datastreams"].items():
            self.mapping[key] = {"name": value["name"],
                                 "@iot.id": value["@iot.id"],
                                 "type": self.type_mapping[value["observationType"]]}
        self.logger.info("Successfully loaded mapping")
        # print(self.mapping)

        # Create Kafka Producer
        self.producer = confluent_kafka.Producer({'bootstrap.servers': self.config["BOOTSTRAP_SERVERS"]})
        self.logger.info("Successfully created Kafka Producer")

    def send(self, quantity, result, timestamp=None):
        data_type = self.mapping[quantity]["type"]
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
        self.producer.produce(kafka_topic, json.dumps(data).encode('utf-8'), callback=self.delivery_report)
        # Wait for any outstanding messages to be delivered and delivery report
        # callbacks to be triggered.
        self.producer.flush()

    def get_iso8601_time(self, timestamp):
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
            Triggered by poll() or flush(). """
        if err is not None:
            self.logger.warning('Message delivery failed: {}'.format(err))
        else:
            self.logger.info('Message delivered to {} [{}]'.format(msg.topic(), msg.partition()))

    def subscribe(self, subscription_file):
        self.logger.info("Loading instances")
        # subscripted_ds: ['ds0', 'ds1']
        with open(subscription_file) as f:
            subscriptions = json.loads(f.read())
        # Make structure pretty
        with open(subscription_file, "w") as f:
            f.write(json.dumps(subscriptions, indent=2))

        self.logger.info("Subscribed to datastreams: {}".format(subscriptions["subscripted_ds"]))

        conf = {'bootstrap.servers': self.config["BOOTSTRAP_SERVERS"],
                'session.timeout.ms': 6000,
                'group.id': self.config["KAFKA_GROUP_ID"]}

        self.consumer = confluent_kafka.Consumer(**conf)
        self.consumer.subscribe([self.config["KAFKA_TOPIC_METRIC"], self.config["KAFKA_TOPIC_LOGGING"]])

        gost_url = "http://" + self.config["GOST_SERVER"] + ":" + self.config["GOST_PORT"]
        gost_datastreams = requests.get(gost_url + "/v1.0/Datastreams").json()["value"]
        self.subscribed_datastream_ids = [ds["@iot.id"] for ds in gost_datastreams if ds["name"] in subscriptions["subscripted_ds"]]
        print(self.subscribed_datastream_ids)

    def poll(self, datastream, timeout=0.1):
        msg = self.consumer.poll(timeout)  # Waits up to 'session.timeout.ms' for a message

        if msg is None:
            pass
        elif not msg.error():
            return msg.value().decode('utf-8')
        else:
            if msg.error().code() == confluent_kafka.KafkaError._PARTITION_EOF:
                self.logger.info("confluent_kafka.KafkaError._PARTITION_EOF")
            else:
                self.logger.error(msg.error())

    def disconnect(self):
        self.producer.flush()
        self.consumer.close()
