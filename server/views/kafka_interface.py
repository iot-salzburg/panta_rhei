# A collection of useful functions for handling kafka
import logging

# confluent_kafka is based on librdkafka, details in install_kafka_requirements.sh
import os
import subprocess
import time
import sqlalchemy as db

import confluent_kafka
import confluent_kafka.admin as kafka_admin
from confluent_kafka import cimpl

PLATFORM_TOPIC = "platform.logger"
KAFKA_TOPICS_SUBFIXES = [".log", ".int", ".ext"]


class KafkaInterface:
    def __init__(self, app):
        self.app = app
        self.system_topics = None
        self.bootstrap_server = app.config["KAFKA_BOOTSTRAP_SERVER"]
        # Create kafka admin client if there is a connection
        if not self.bootstrap_server:
            self.k_admin_client = None

        self.k_admin_client = kafka_admin.AdminClient({'bootstrap.servers': self.bootstrap_server})
        # the system_topics are updated in the get_connection method
        self.get_connection()

    def get_connection(self):
        if not self.bootstrap_server:
            self.app.logger.info("The connection to Kafka is disabled. Check the '.env' file!")
            return None
        try:
            # Check the connectivity and update kafka topics
            self.system_topics = self.k_admin_client.list_topics(timeout=3.0).topics
            # create PLATFORM_TOPIC if not already done
            if not self.system_topics.get(PLATFORM_TOPIC, None):
                self.k_admin_client.create_topics([kafka_admin.NewTopic(PLATFORM_TOPIC, 3, 1)])
                self.app.logger.info("Created platform logging topic with name '{}'.".format(PLATFORM_TOPIC))

            self.app.logger.debug("Connected to Kafka Bootstrap Servers '{}'.".format(self.bootstrap_server))
            return True
        except cimpl.KafkaException:
            self.app.logger.error("Couldn't connect to Kafka Bootstrap servers.")
            self.app.logger.error("Check the Kafka Bootstrap Servers '{}'!".format(self.bootstrap_server))
            return False

    def recreate_lost_topics(self):
        self.app.logger.info("Recreating lost system topics.")
        # recreate lost system topics. Load the list from the database and topic list and create missing.
        if self.get_connection():
            # Fetch systems from DB, for which the current user is agent of
            engine = db.create_engine(self.app.config["SQLALCHEMY_DATABASE_URI"])
            conn = engine.connect()
            query = """SELECT  domain, enterprise, workcenter, station
                FROM systems AS sys
                INNER JOIN companies AS com ON sys.company_uuid=com.uuid
                ORDER BY domain, com, workcenter, station;"""
            result_proxy = conn.execute(query)
            engine.dispose()
            res = [dict(c.items()) for c in result_proxy.fetchall()]
            db_system_names = ["{}.{}.{}.{}".format(s["domain"], s["enterprise"],s["workcenter"], s["station"]) for s in res]
            self.app.logger.debug("Found {} systems in database.".format(len(db_system_names)))

            if self.system_topics is None:  # Load topics if not already done
                self.get_connection()
                # Recreate Kafka Topics for each system if one topic is missing (create is costly and idempotent)
            for system_name in db_system_names:
                all_in = True
                for sub_fix in KAFKA_TOPICS_SUBFIXES:
                    if not self.system_topics.get(system_name + sub_fix, False):
                        all_in = False
                if not all_in:
                    self.create_system_topics(system_name)
            # Update kafka topics
            self.system_topics = self.k_admin_client.list_topics(timeout=3.0).topics

    def create_system_topics(self, system_name):
        # Create the set of Kafka topics for system_name
        if self.bootstrap_server is None:
            self.app.logger.warning("Skipped to create system topics as the platform-only mode is used.")
            return None
        else:
            self.app.logger.debug("Creating Kafka Topic for new system.")
            # Create system topics
            self.k_admin_client.create_topics([  # TODO: set num_partitions to 1
                kafka_admin.NewTopic(system_name + ".log", num_partitions=3, replication_factor=1),
                kafka_admin.NewTopic(system_name + ".int", num_partitions=3, replication_factor=1),
                kafka_admin.NewTopic(system_name + ".ext", num_partitions=3, replication_factor=1)])
            self.app.logger.info("Created system topics for '{}'".format(system_name))

    def create_default_topics(self):
        if self.bootstrap_server is None:
            self.app.logger.warning("Skipped to create default system topics as the platform-only mode is used.")
            return None
        # Create default system topics
        for system_name in ["cz.icecars.iot-iot4cps-wp5.CarFleet",
                            "is.iceland.iot-iot4cps-wp5.WeatherService",
                            "at.datahouse.iot-iot4cps-wp5.RoadAnalytics"]:
            self.create_system_topics(system_name)

    def delete_system_topics(self, system_name):
        if not self.bootstrap_server:
            self.app.logger.warning("Skipped to delete topics for '{}' as the platform-only mode is used".format(
                system_name))
            return None
        # multiple trials to delete the system topics
        max_trials = 3
        for trial in range(max_trials):
            if self.delete_system_topics_try(system_name, trial=trial):
                self.app.logger.info("System topics for '{}' were successfully deleted.".format(system_name))
                return True
        self.app.logger.warning("System topics for '{}' were not successfully deleted.".format(system_name))
        return False

    def delete_system_topics_try(self, system_name, trial):
        # Delete system topics
        self.k_admin_client.delete_topics([system_name + k_type for k_type in KAFKA_TOPICS_SUBFIXES])
        # the system_topics are updated in the get_connection method, may needs some time to update, hence more trials
        time.sleep(1+2*trial)  # increasing waiting time, trial starts with 0.
        self.get_connection()
        # check if each system topic was removed, this procedure has linear complexity.
        all_out = True
        for sub_fix in KAFKA_TOPICS_SUBFIXES:
            if self.system_topics.get(system_name + sub_fix, False):
                all_out = False
        if not all_out:
            return False
        return True


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
