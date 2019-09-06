import os
import logging

# Statement for enabling the development environment
DEBUG = True
LOGLEVEL = logging.DEBUG

# Define the application directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Define the database - we are working with
# Set up SQLAlchemy
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://iot4cps:iot4cps@localhost/iot4cps'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Secret key for signing cookies
SECRET_KEY = "changeme"

# Bootstrap servers for Kafka
KAFKA_BOOTSTRAP_SERVER = "localhost:9092"
