# A collection of useful functions for handling kafka
import logging

# confluent_kafka is based on librdkafka, details in install_kafka_requirements.sh
import os
import subprocess

import confluent_kafka
import confluent_kafka.admin as kafka_admin
from confluent_kafka import cimpl

PLATFORM_TOPIC = "platform.logger"


def check_kafka(app):
    app.logger.debug("Connecting to Kafka Bootstrap servers '{}'.".format(app.config["KAFKA_BOOTSTRAP_SERVER"]))
    kac = kafka_admin.AdminClient({'bootstrap.servers': app.config["KAFKA_BOOTSTRAP_SERVER"]})
    try:
        topics = kac.list_topics(timeout=3.0).topics
        app.logger.debug("Connected to {}.".format(PLATFORM_TOPIC))

        # Create topic if not already done and return True
        if PLATFORM_TOPIC in topics.keys():
            return True
        else:
            kac.create_topics([confluent_kafka.admin.NewTopic(PLATFORM_TOPIC, 3, 1)])
            app.logger.info("Created new topic with name {}.".format(PLATFORM_TOPIC))
            return True
    except cimpl.KafkaException:
        app.logger.error("Couldn't connect to Kafka Bootstrap servers. Check manually if the servers are reachable!")
        return False


def create_system_topics(app, system_name):
    if check_kafka(app):
        # Create system topics
        kac = kafka_admin.AdminClient({'bootstrap.servers': app.config["KAFKA_BOOTSTRAP_SERVER"]})
        kac.create_topics([confluent_kafka.admin.NewTopic(system_name + ".log", 3, 1),
                           confluent_kafka.admin.NewTopic(system_name + ".int", 3, 1),
                           confluent_kafka.admin.NewTopic(system_name + ".ext", 3, 1)])
        app.logger.debug("Created system topics for '{}'".format(system_name))


def create_default_topics(app):
    if check_kafka(app):
        # Create default system topics
        for system_name in ["cz.icecars.iot-iot4cps-wp5.CarFleet",
                            "is.iceland.iot-iot4cps-wp5.InfraProv",
                            "at.datahouse.iot-iot4cps-wp5.WeatherService"]:
            kac = kafka_admin.AdminClient({'bootstrap.servers': app.config["KAFKA_BOOTSTRAP_SERVER"]})
            kac.create_topics([confluent_kafka.admin.NewTopic(system_name + ".log", 3, 1),
                               confluent_kafka.admin.NewTopic(system_name + ".int", 3, 1),
                               confluent_kafka.admin.NewTopic(system_name + ".ext", 3, 1)])
            app.logger.debug("Created system topics for '{}'".format(system_name))


def delete_system_topics(app, system_name):
    # Delete system topics
    if check_kafka(app):
        try:
            for ktype in [".log", ".int", ".ext"]:
                # TODO use subprocess
                cmd = "/kafka/bin/kafka-topics.sh --bootstrap-server {} --delete --topic {}".format(
                    app.config["KAFKA_BOOTSTRAP_SERVER"], system_name + ktype)
                with open(os.devnull, "w") as devnull:
                    res = subprocess.call(cmd.split(), stdout=devnull, stderr=devnull)
        except Exception as e:
            app.logger.warning("System topics were already deleted.")
        app.logger.debug("Deleted topics for system '{}'.".format(system_name))
    # That doesn't work now
    # kac = kafka_admin.AdminClient({'bootstrap.servers': app.config["KAFKA_BOOTSTRAP_SERVER"]})
    # kac.delete_topics([system_name + ktype for ktype in [".log", ".int", ".ext"])


class KafkaHandler(logging.Handler):
    """Class to instantiate the kafka logging facility."""

    def __init__(self, app, tls=None):
        """Initialize an instance of the kafka handler."""
        logging.Handler.__init__(self)
        self.producer = confluent_kafka.Producer({'bootstrap.servers': app.config["KAFKA_BOOTSTRAP_SERVER"],
                                                  'client.id': "platform.logger",
                                                  'default.topic.config': {'acks': 'all'}})
        self.topic = PLATFORM_TOPIC

    def emit(self, record):
        """Emit the provided record to the kafka_client producer."""
        # drop kafka logging to avoid infinite recursion
        if 'kafka.' in record.name:
            return

        try:
            # apply the logger formatter
            msg = self.format(record)
            self.producer.produce(self.topic, msg)
            self.flush(timeout=1.0)
        except Exception:
            logging.Handler.handleError(self, record)

    def flush(self, timeout=1.0):
        """Flush the objects."""
        self.producer.flush(timeout=timeout)

    def close(self):
        """Close the producer and clean up."""
        self.acquire()
        try:
            if self.producer:
                self.producer.flush()

            logging.Handler.close(self)
        finally:
            self.release()
