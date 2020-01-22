import sys
import logging

from dotenv import load_dotenv
from flask import Flask

from server.create_database import create_tables
# Import modules
from server.views.auth import auth
from server.views.clients import client
from server.views.company import company
from server.views.home import home_bp

# Import application-specific functions
from server.views.kafka_interface import check_kafka, create_default_topics, KafkaHandler
from server.views.kafka_interface import create_system_topics, delete_system_topics
from server.views.streamhub import streamhub_bp
from server.views.system import system

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
    app.logger.setLevel(app.config["LOGLEVEL"])
    app.logger.info("Preparing the platform.")

    # Check the connection to Kafka and create new tables if not already done
    if check_kafka(app):
        app.logger.debug("Connected to the Kafka Bootstrap Servers '{}'.".format(app.config["KAFKA_BOOTSTRAP_SERVER"]))
    else:
        app.logger.error("The connection to the Kafka Bootstrap Servers couldn't be established.")
        sys.exit(1)

    # Adding a KafkaHandler to the logger, ingests messages into kafka
    kh = KafkaHandler(app)
    app.logger.addHandler(kh)

    app.logger.info("Starting the platform.")
    app.logger.info("Connection to Kafka Servers are okay.")

    # Create postgres tables to get the data model
    create_tables(app)
    create_default_topics(app)

    # Test the Kafka Interface by creating and deleting a test topic
    create_system_topics(app, "test.test.test.test")
    delete_system_topics(app, "test.test.test.test")

    # Run application
    app.run(debug=app.config["DEBUG"], port=1908)
