import logging

from dotenv import load_dotenv
from flask import Flask

# Import application-specific functions
from server.views.useful_functions import get_datetime, get_uid, is_logged_in


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
app.register_blueprint(home_bp)  # url_prefix='/home')
app.register_blueprint(auth)  # url_prefix='/auth')
app.register_blueprint(company)  # url_prefix='/companies')
app.register_blueprint(system)  # url_prefix='/systems')
app.register_blueprint(client)  # url_prefix='/clients')
app.register_blueprint(streamhub_bp)  # url_prefix='/streamhub')


if __name__ == '__main__':
    app.logger.setLevel(logging.INFO)
    app.logger.info("Starting the platform.")

    # Create engine once and held globally
    # The typical usage of create_engine() is once per particular database URL, held globally for the lifetime of a single application process.
    # see: https://docs.sqlalchemy.org/en/13/core/connections.html#basic-usage

    # Create tables to get the data model
    create_tables(app)

    # Run application
    app.run(debug=app.config["DEBUG"], port=5000)

# TODO logout if inactive (with wrapper)
