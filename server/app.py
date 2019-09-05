import sys
import logging

from dotenv import load_dotenv
from flask import Flask

# Import application-specific functions
from server.views.useful_functions import get_datetime, get_uid, is_logged_in
from server.views.kafka_interface import check_kafka, create_system_topics, delete_system_topics, \
    create_default_topics, KafkaHandler


# Import modules
from server.views.auth import auth
from server.views.home import home_bp
from server.views.company import company
from server.views.system import system
from server.views.clients import client
from server.views.streamhub import streamhub_bp
from server.create_database import create_tables

# load environment variables automatically from a .env file in the same directory
load_dotenv()

# Create Flask app and load configs
app = Flask(__name__)
# app.config.from_object('config')
app.config.from_envvar('APP_CONFIG_FILE')

# Register modules as blueprint
app.register_blueprint(home_bp)
app.register_blueprint(auth)
app.register_blueprint(company)
app.register_blueprint(system)
app.register_blueprint(client)
app.register_blueprint(streamhub_bp)


if __name__ == '__main__':
    app.logger.setLevel(logging.INFO)
    app.logger.info("Preparing the platform.")

    # Check the connection to Kafka and create new tables if not already done
    if check_kafka(app):
        app.logger.debug("Connected to with bootstrap servers '{}'.".format(app.config["KAFKA_BOOTSTRAP_SERVER"]))
    else:
        app.logger.error("The connection to Kafka Servers couldn't be established.")
        sys.exit(1)

    # Adding a KafkaHandler to the logger, ingests messages into kafka
    kh = KafkaHandler(app)
    app.logger.addHandler(kh)

    app.logger.info("Starting the platform.")
    app.logger.info("Connection to Kafka Servers are okay.")

    # Create postgres tables to get the data model
    create_tables(app)
    create_default_topics(app)

    # Test creation and deletion of topics
    create_system_topics(app, "test.test.test.test")
    delete_system_topics(app, "test.test.test.test")

    # Run application
    app.run(debug=app.config["DEBUG"], port=5000)


# Create engine once and held globally
# The typical usage of create_engine() is once per particular database URL,
# held globally for the lifetime of a single application process.
# see: https://docs.sqlalchemy.org/en/13/core/connections.html#basic-usage

# TODO logout if inactive (with wrapper)
