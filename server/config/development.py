import os
import logging
import subprocess

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

# Bootstrap servers for Kafka: get ip of the local machine
try:
    proc = subprocess.Popen("hostname -I | cut -d' ' -f1", shell=True, stdout=subprocess.PIPE)
    HOST_IP = proc.communicate()[0].decode().strip()
except:
    HOST_IP = "localhost"
KAFKA_BOOTSTRAP_SERVER = "{}:9092".format(HOST_IP)

SOURCE_URL = "https://git-service.ait.ac.at/im-IoT4CPS/WP5-lifecycle-mgmt"
