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

from marshmallow_jsonapi.flask import Schema
from marshmallow_jsonapi import fields

# Create data abstraction layer
class ArtistSchema(Schema):
    class Meta:
        type_ = 'artist'
        self_view = 'artist_one'
        self_view_kwargs = {'id': '<id>'}
        self_view_many = 'artist_many'

    id = fields.Integer()
    name = fields.Str(required=True)
    birth_year = fields.Integer(load_only=True)
    genre = fields.Str()


# Define a class for the Artist table
class Artist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    birth_year = db.Column(db.Integer)
    genre = db.Column(db.String)

# Create resource managers and endpoints
from flask_rest_jsonapi import Api, ResourceDetail, ResourceList

class ArtistMany(ResourceList):
    schema = ArtistSchema
    data_layer = {'session': db.session,
                  'model': Artist}

class ArtistOne(ResourceDetail):
    schema = ArtistSchema
    data_layer = {'session': db.session,
                  'model': Artist}

api = Api(app)
api.route(ArtistMany, 'artist_many', '/artists')
api.route(ArtistOne, 'artist_one', '/artists/<int:id>')


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

import os
import sqlalchemy as db

app = Flask(__name__)
# Set up SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI',
                                                  'postgresql+psycopg2://user:passwd@host/database')
engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
connection = engine.connect()
metadata = db.MetaData()

# Define all entities and relations
app.config["users"] = db.Table(
    'users', metadata,
    db.Column('uuid', db.CHAR(36), primary_key=True, unique=True),
    db.Column('first_name', db.VARCHAR(25), nullable=False),
    db.Column('sur_name', db.VARCHAR(25), nullable=False),
    db.Column('birthdate', db.DATE, nullable=True),
    db.Column('email', db.VARCHAR(35), nullable=False),
    db.Column('password', db.VARCHAR(40), nullable=False)
)
# Creates the tables
metadata.create_all(engine)