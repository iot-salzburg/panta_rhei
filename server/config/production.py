import os
import logging

# Statement for enabling the development environment
DEBUG = False
LOGLEVEL = logging.INFO

# Define the application directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Define the database - we are working with
# Set up SQLAlchemy
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://docker:docker@postgresdb/docker'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Secret key for signing cookies
SECRET_KEY = "changeme"

# Bootstrap servers for Kafka
# KAFKA_BOOTSTRAP_SERVER = "localhost:9092"  # Change to test server
#KAFKA_BOOTSTRAP_SERVER = "192.168.48.71:9092,192.168.48.71:9093,192.168.48.71:9094"
KAFKA_BOOTSTRAP_SERVER = "kafka1:9092,kafka2:9093,kafka3:9094"
#GOST_SERVER = "192.168.48.71:8082"
GOST_SERVER = "gost:8082"

SOURCE_URL = "https://github.com/iot-salzburg/panta_rhei"
