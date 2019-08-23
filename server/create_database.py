import logging

import sqlalchemy as db
from dotenv import load_dotenv
from flask import Flask
# from .data import Articles
from passlib.hash import sha256_crypt

try:
    from server.views.useful_functions import get_datetime, get_uid, is_logged_in
except ModuleNotFoundError:
    from views.useful_functions import get_datetime, get_uid, is_logged_in

# load environment variables automatically from a .env file in the same directory
load_dotenv()

# Create Flask app and load configs
app = Flask(__name__)
# app.config.from_object('config')
app.config.from_envvar('APP_CONFIG_FILE')


def drop_tables():
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """
    DROP TABLE IF EXISTS users CASCADE;
    DROP TABLE IF EXISTS companies CASCADE;
    DROP TABLE IF EXISTS systems CASCADE;
    DROP TABLE IF EXISTS clients CASCADE;
    DROP TABLE IF EXISTS gost_ds CASCADE;
    DROP TABLE IF EXISTS gost_thing CASCADE;
    DROP TABLE IF EXISTS is_admin_of CASCADE;
    DROP TABLE IF EXISTS is_agent_of CASCADE;
    """
    result_proxy = conn.execute(query)


def create_tables(app):
    # Create context, connection and metadata
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    conn = engine.connect()
    app.config['metadata'] = db.MetaData()

    # Define all entities and relations
    app.config["tables"] = dict()
    app.config["tables"]["users"] = db.Table(
        'users', app.config['metadata'],
        db.Column('uuid', db.VARCHAR(12), primary_key=True, unique=True),
        db.Column('first_name', db.VARCHAR(25), nullable=False),
        db.Column('sur_name', db.VARCHAR(25), nullable=False),
        db.Column('birthdate', db.DATE, nullable=True),
        db.Column('email', db.VARCHAR(35), nullable=False, unique=True),
        db.Column('password', db.VARCHAR(80), nullable=False)
        )
    app.config["tables"]["companies"] = db.Table(
        'companies', app.config['metadata'],
        db.Column('uuid', db.VARCHAR(12), primary_key=True, unique=True),
        db.Column('domain', db.VARCHAR(4), nullable=False),
        db.Column('enterprise', db.VARCHAR(15), nullable=False)
        )
    app.config["tables"]["systems"] = db.Table(
        'systems', app.config['metadata'],
        db.Column('uuid', db.VARCHAR(12), primary_key=True, unique=True),
        db.Column('company_uuid', db.ForeignKey('companies.uuid')),
        db.Column('workcenter', db.VARCHAR(30), nullable=False),
        db.Column('station', db.VARCHAR(20), nullable=False)
        )
    app.config["tables"]["is_admin_of"] = db.Table(
        'is_admin_of', app.config['metadata'],
        db.Column('user_uuid', db.ForeignKey("users.uuid"), primary_key=True),
        db.Column('company_uuid', db.ForeignKey('companies.uuid'), primary_key=True),
        db.Column('creator_uuid', db.ForeignKey("users.uuid"), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True)
        )
    app.config["tables"]["is_agent_of"] = db.Table(
        'is_agent_of', app.config['metadata'],
        db.Column('user_uuid', db.ForeignKey("users.uuid"), primary_key=True),
        db.Column('system_uuid', db.ForeignKey('systems.uuid'), primary_key=True),
        db.Column('creator_uuid', db.ForeignKey("users.uuid"), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True)
        )
    app.config["tables"]["clients"] = db.Table(
        'clients', app.config['metadata'],
        db.Column('name', db.VARCHAR(25), primary_key=True, unique=True),
        db.Column('system_uuid', db.ForeignKey('systems.uuid'), nullable=False),
        db.Column('keyfile', db.TEXT, nullable=True),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('creator_uuid', db.ForeignKey("users.uuid"), nullable=False)
        )
    app.config["tables"]["gost_thing"] = db.Table(
        'gost_thing', app.config['metadata'],
        db.Column('link', db.VARCHAR(50), nullable=False),
        db.Column('system_uuid', db.ForeignKey("systems.uuid"), primary_key=True)
        )
    app.config["tables"]["gost_ds"] = db.Table(
        'gost_ds', app.config['metadata'],
        db.Column('link', db.VARCHAR(50), nullable=False),
        db.Column('client_name', db.ForeignKey("clients.name"), primary_key=True),
        db.Column('system_uuid', db.ForeignKey("systems.uuid"), primary_key=True)
        )

    # Creates the tables
    app.config['metadata'].create_all(engine)
    app.logger.info("Created tables.")


def insert_sample():
    # Create context, connection and metadata
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    conn = engine.connect()

    # Drop Tables befor ingestions
    for tbl in reversed(app.config['metadata'].sorted_tables):
        engine.execute(tbl.delete())

    # Inserting many records at ones in users
    uuid_sue = get_uid()
    uuid_stefan = get_uid()
    uuid_peter = get_uid()
    uuid_anna = get_uid()
    uuid_chris = get_uid()
    query = db.insert(app.config["tables"]["users"])
    values_list = [
        {'uuid': uuid_sue,
        'first_name':'Sue',
        'sur_name': 'Smith',
        'birthdate': '1967-04-01',
        'email': 'sue.smith@gmail.com',
        'password': sha256_crypt.encrypt('asdf')},
       {'uuid': uuid_stefan,
        'first_name': 'Stefan',
        'sur_name': 'Gunnarsson',
        'birthdate': '1967-03-01',
        'email': 'stefan.gunnarsson@gmail.com',
        'password': sha256_crypt.encrypt('asdf')},
       {'uuid': uuid_peter,
        'first_name': 'Peter',
        'sur_name': 'Novak',
        'birthdate': '1990-02-01',
        'email': 'peter.novak@gmail.com',
        'password': sha256_crypt.encrypt('asdf')},
       {'uuid': uuid_anna,
        'first_name': 'Anna',
        'sur_name': 'Gruber',
        'birthdate': '1994-01-01',
        'email': 'anna.gruber@gmail.com',
        'password': sha256_crypt.encrypt('asdf')},
       {'uuid': uuid_chris,
        'first_name': 'Chris',
        'sur_name': 'Schranz',
        'birthdate': '1993-04-23',
        'email': 'christoph.s.23@gmx.at',
        'password': sha256_crypt.encrypt('asdf')}]
    ResultProxy = conn.execute(query, values_list)

    # Insert companies
    uuid_icecars = get_uid()
    uuid_iceland = get_uid()
    uuid_datahouse = get_uid()
    query = db.insert(app.config["tables"]["companies"])
    values_list = [
        {'uuid': uuid_icecars,
         'domain': 'cz',
         'enterprise': 'icecars'},
        {'uuid': uuid_iceland,
         'domain': 'is',
         'enterprise': 'iceland'},
        {'uuid': uuid_datahouse,
         'domain': 'at',
         'enterprise': 'datahouse'}]
    ResultProxy = conn.execute(query, values_list)


    # Insert is_admin_of
    query = db.insert(app.config["tables"]["is_admin_of"])
    values_list = [
        {'user_uuid': uuid_sue,
         'company_uuid': uuid_icecars,
         'creator_uuid': uuid_sue,
         'datetime': get_datetime()},
        {'user_uuid': uuid_stefan,
         'company_uuid': uuid_iceland,
         'creator_uuid': uuid_stefan,
         'datetime': get_datetime()},
        {'user_uuid': uuid_anna,
         'company_uuid': uuid_datahouse,
         'creator_uuid': uuid_anna,
         'datetime': get_datetime()}]
    ResultProxy = conn.execute(query, values_list)

    # Insert systems
    uuid_carfleet = get_uid()
    uuid_infraprov = get_uid()
    uuid_weatherservice = get_uid()
    query = db.insert(app.config["tables"]["systems"])
    values_list = [
        {'uuid': uuid_carfleet,
         'company_uuid': uuid_icecars,
         'workcenter': "iot-iot4cps-wp5",
         'station': "CarFleet"},
        {'uuid': uuid_infraprov,
         'company_uuid': uuid_iceland,
         'workcenter': "iot-iot4cps-wp5",
         'station': "InfraProv"},
        {'uuid': uuid_weatherservice,
         'company_uuid': uuid_datahouse,
         'workcenter': "iot-iot4cps-wp5",
         'station': "WeatherService"},]
    ResultProxy = conn.execute(query, values_list)

    # Insert is_agent_of
    query = db.insert(app.config["tables"]["is_agent_of"])
    values_list = [
        {'user_uuid': uuid_sue,
         'system_uuid': uuid_carfleet,
         'creator_uuid': uuid_sue,
         'datetime': get_datetime()},
        {'user_uuid': uuid_stefan,
         'system_uuid': uuid_infraprov,
         'creator_uuid': uuid_stefan,
         'datetime': get_datetime()},
        {'user_uuid': uuid_anna,
         'system_uuid': uuid_weatherservice,
         'creator_uuid': uuid_anna,
         'datetime': get_datetime()}]
    ResultProxy = conn.execute(query, values_list)

    # Insert client
    query = db.insert(app.config["tables"]["clients"])
    values_list = [
        {'name': "car_1",
         'system_uuid': uuid_carfleet,
         'creator_uuid': uuid_sue,
         'datetime': get_datetime()},
        {'name': "car_2",
         'system_uuid': uuid_carfleet,
         'creator_uuid': uuid_sue,
         'datetime': get_datetime()},
        {'name': "gov_1",
         'system_uuid': uuid_infraprov,
         'creator_uuid': uuid_stefan,
         'datetime': get_datetime()},
        {'name': "weatherstation_1",
         'system_uuid': uuid_weatherservice,
         'creator_uuid': uuid_anna,
         'datetime': get_datetime()},
        {'name': "weatherstation_2",
         'system_uuid': uuid_weatherservice,
         'creator_uuid': uuid_anna,
         'datetime': get_datetime()},
        {'name': "analysis",
         'system_uuid': uuid_weatherservice,
         'creator_uuid': uuid_anna,
         'datetime': get_datetime()}]
    ResultProxy = conn.execute(query, values_list)

    app.logger.info("Ingested data into tables.")


if __name__ == '__main__':
    app.logger.setLevel(logging.INFO)

    app.logger.info("Drop the database.")
    drop_tables()

    # Creating the tables
    app.logger.info("Create the database.")
    create_tables(app)

    # Insert sample for the demo scenario
    app.logger.info("Insert sample data.")
    insert_sample()

    app.logger.info("Finished.")