import logging
import psycopg2
from sqlalchemy import create_engine
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

prefix = "/0v1"
app = Flask(__name__)

# Set up SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://iot4cps:iot4cps@localhost/iot4cps'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Define a class for the Artist table
class Artist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    birth_year = db.Column(db.Integer)
    genre = db.Column(db.String)


@app.route(prefix+'/')
def example():
   return '{"name":"Bob"}'


if __name__ == '__main__':
    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    # Create the table
    db.create_all()
    logging.info("Created tables.")

    app.run(debug=True)
