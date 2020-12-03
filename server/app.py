import os
import sys

from dotenv import load_dotenv
from flask import Flask

# Import modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__name__)), os.pardir)))
from server.create_database import create_tables
from server.views.auth import auth
from server.views.clients import client
from server.views.company import company
from server.views.home import home_bp

# Import application-specific functions
from server.views.kafka_interface import KafkaHandler, KafkaInterface
from server.views.streamhub import streamhub_bp
from server.views.system import system



def create_app():
    # load environment variables automatically from a .env file in the same directory
    load_dotenv()

    # Create Flask app and load configs
    app = Flask(__name__)

    # Register modules as blueprint
    app.register_blueprint(home_bp)
    app.register_blueprint(auth)
    app.register_blueprint(company)
    app.register_blueprint(system)
    app.register_blueprint(client)
    app.register_blueprint(streamhub_bp)

    # app.config.from_object('config')
    app.config.from_envvar('APP_CONFIG_FILE')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=app.config["DEBUG"], host="0.0.0.0", port=1908)
