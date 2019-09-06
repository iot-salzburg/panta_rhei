import os

# Statement for enabling the development environment
DEBUG = False

# Define the application directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Define the database - we are working with
# Set up SQLAlchemy
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://iot4cps:iot4cps@localhost/iot4cps'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Secret key for signing cookies
SECRET_KEY = "changeme"

# Bootstrap servers for Kafka
# KAFKA_BOOTSTRAP_SERVER = "localhost:9092"  # Change to test server
KAFKA_BOOTSTRAP_SERVER = "192.168.48.81:9092,192.168.48.82:9092,192.168.48.83:9092"
