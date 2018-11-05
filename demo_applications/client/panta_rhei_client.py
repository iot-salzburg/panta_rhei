import os
import json
import time
import requests


# confluent_kafka is based on librdkafka, details in requirements.txt
#from confluent_kafka import Producer, Consumer, KafkaError
import confluent_kafka


class PantaRheiClient:
    def __init__(self):
        """
        check gost server connection
        check kafka connection
        """
        print("Initialising the Panta Rhei Client.")
        # Load config.json and drop comments
        config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        with open(config_file) as f:
            self.config = json.loads(f.read())
            self.config.pop("_comment")
            print("Configs were loaded successfully.")

        # Check Sensorthings connection
        gost_url = "http://" + self.config["GOST_SERVER"] + ":" + self.config["GOST_PORT"]
        res = requests.get(gost_url + "/v1.0/Things")
        if res.status_code in [200, 201, 202]:
            print("Connected successfully to GOST server {}.".format(gost_url))
        else:
            print("Error, couldn't connect to GOST server: {}, status code: {}, result: {}".format(
                gost_url, res.status_code, res.json()))

        # Init Kafka, test for KAFKA_TOPICS_LOGS with an unique group.id
        conf = {'bootstrap.servers': self.config["BOOTSTRAP_SERVERS"],
                'group.id': self.config["KAFKA_GROUP_ID"] + "_" + str(time.time())}
        consumer = confluent_kafka.Consumer(**conf)
        consumer.subscribe([self.config["KAFKA_TOPIC_LOGS"]])
        while True:
            msg = consumer.poll(1)
            if msg is not None:
                break
        print("Successfully connected to the Kafka Broker: {}".format(self.config["BOOTSTRAP_SERVERS"]))


    def register(self, structure, instances):
        """
        Opens structure and instances.
        check if gost entries exists
        create requests
        check if gost entries exists, return ids in case, make patches if there are differences
        make requests
        return ids into structure
        :param file:
        :return: nothing
        """
        #print("register_structure")
        pass

    def send(self, result):
        pass

    def subscribe(self):
        pass

    def poll(self):
        pass

    def disconnect(self):
        pass
