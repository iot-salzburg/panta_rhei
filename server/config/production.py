# Statement for enabling the development environment
DEBUG = False

# Define the application directory
import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Define the database - we are working with
# Set up SQLAlchemy
SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg2://user:passwd@host/database'
SQLALCHEMY_TRACK_MODIFICATIONS = False

CSRF_SESSION_KEY = "secret"

# Secret key for signing cookies
SECRET_KEY = "changeme"
