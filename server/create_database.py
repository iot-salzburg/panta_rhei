import logging

import sqlalchemy as db
from dotenv import load_dotenv
from flask import Flask
# from .data import Articles
from passlib.hash import sha256_crypt

try:
    from server.views.useful_functions import get_datetime, get_uid, is_logged_in
except ModuleNotFoundError:
    # This is needed
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
    DROP TABLE IF EXISTS streams CASCADE;
    DROP TABLE IF EXISTS is_admin_of_com CASCADE;
    DROP TABLE IF EXISTS is_admin_of_sys CASCADE;
    """
    result_proxy = conn.execute(query)
    engine.dispose()


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
        db.Column('enterprise', db.VARCHAR(15), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('description', db.VARCHAR(1024), nullable=True)
    )
    app.config["tables"]["systems"] = db.Table(
        'systems', app.config['metadata'],
        db.Column('uuid', db.VARCHAR(12), primary_key=True, unique=True),
        db.Column('company_uuid', db.ForeignKey('companies.uuid')),
        db.Column('workcenter', db.VARCHAR(30), nullable=False),
        db.Column('station', db.VARCHAR(20), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('description', db.VARCHAR(1024), nullable=True)
    )
    app.config["tables"]["is_admin_of_com"] = db.Table(
        'is_admin_of_com', app.config['metadata'],
        db.Column('user_uuid', db.ForeignKey("users.uuid"), primary_key=True),
        db.Column('company_uuid', db.ForeignKey('companies.uuid'), primary_key=True),
        db.Column('creator_uuid', db.ForeignKey("users.uuid"), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True)
    )
    app.config["tables"]["is_admin_of_sys"] = db.Table(
        'is_admin_of_sys', app.config['metadata'],
        db.Column('user_uuid', db.ForeignKey("users.uuid"), primary_key=True),
        db.Column('system_uuid', db.ForeignKey('systems.uuid'), primary_key=True),
        db.Column('creator_uuid', db.ForeignKey("users.uuid"), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True)
    )
    app.config["tables"]["clients"] = db.Table(
        'clients', app.config['metadata'],
        db.Column('name', db.VARCHAR(25), primary_key=True),
        db.Column('system_uuid', db.ForeignKey('systems.uuid'), primary_key=True),
        db.Column('metadata_name', db.VARCHAR(50), nullable=False),
        db.Column('metadata_uri', db.VARCHAR(256), nullable=False),
        db.Column('keyfile_av', db.BOOLEAN, nullable=False, default=False),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('creator_uuid', db.ForeignKey("users.uuid"), nullable=False),
        db.Column('description', db.VARCHAR(1024), nullable=True)
    )
    app.config["tables"]["streams"] = db.Table(
        'streams', app.config['metadata'],
        db.Column('name', db.VARCHAR(25), primary_key=True),
        db.Column('system_uuid', db.ForeignKey('systems.uuid'), primary_key=True),
        db.Column('source_system', db.VARCHAR(72), nullable=False),
        db.Column('target_system', db.VARCHAR(72), nullable=False),
        db.Column('filter_logic', db.TEXT, nullable=False),
        db.Column('is_multi_source', db.BOOLEAN, nullable=False),
        db.Column('status', db.VARCHAR(20), nullable=False, default="init"),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('creator_uuid', db.ForeignKey("users.uuid"), nullable=False),
        db.Column('description', db.VARCHAR(16*1024), nullable=True)
    )
    # Creates the tables
    app.config['metadata'].create_all(engine)
    engine.dispose()
    app.logger.info("Created tables.")


def insert_sample():
    lorem_ipsum = """Lorem ipsum dolor sit amet, consectetuer adipiscing elit. Aenean commodo ligula eget dolor. 
    Aenean massa. Cum sociis natoque penatibus et magnis dis parturient montes, nascetur ridiculus mus. Donec 
    quam felis, ultricies nec, pellentesque eu, pretium quis, sem. Nulla consequat massa quis enim."""
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
    query = db.insert(app.config["tables"]["users"])
    values_list = [
        {'uuid': uuid_sue,
         'first_name': 'Sue',
         'sur_name': 'Smith',
         'birthdate': '1967-04-01',
         'email': 'sue.smith@example.com',
         'password': sha256_crypt.hash('asdf')},
        {'uuid': uuid_stefan,
         'first_name': 'Stefan',
         'sur_name': 'Gunnarsson',
         'birthdate': '1967-03-01',
         'email': 'stefan.gunnarsson@example.com',
         'password': sha256_crypt.hash('asdf')},
        {'uuid': uuid_peter,
         'first_name': 'Peter',
         'sur_name': 'Novak',
         'birthdate': '1990-02-01',
         'email': 'peter.novak@example.com',
         'password': sha256_crypt.hash('asdf')},
        {'uuid': uuid_anna,
         'first_name': 'Anna',
         'sur_name': 'Gruber',
         'birthdate': '1994-01-01',
         'email': 'anna.gruber@example.com',
         'password': sha256_crypt.hash('asdf')}]
    ResultProxy = conn.execute(query, values_list)

    # Insert companies
    uuid_icecars = get_uid()
    uuid_iceland = get_uid()
    uuid_datahouse = get_uid()
    query = db.insert(app.config["tables"]["companies"])
    values_list = [
        {'uuid': uuid_icecars,
         'domain': 'cz',
         'enterprise': 'icecars',
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'uuid': uuid_iceland,
         'domain': 'is',
         'enterprise': 'iceland',
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'uuid': uuid_datahouse,
         'domain': 'at',
         'enterprise': 'datahouse',
         'description': lorem_ipsum,
         'datetime': get_datetime()}]
    ResultProxy = conn.execute(query, values_list)

    # Insert is_admin_of_com
    query = db.insert(app.config["tables"]["is_admin_of_com"])
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
    uuid_car1 = get_uid()
    uuid_car2 = get_uid()
    uuid_roadanalytics = get_uid()
    uuid_stations = get_uid()
    uuid_services = get_uid()
    query = db.insert(app.config["tables"]["systems"])
    values_list = [
        {'uuid': uuid_car1,
         'company_uuid': uuid_icecars,
         'workcenter': "iot4cps-wp5-CarFleet",
         'station': "Car1",
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'uuid': uuid_car2,
         'company_uuid': uuid_icecars,
         'workcenter': "iot4cps-wp5-CarFleet",
         'station': "Car2",
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'uuid': uuid_stations,
         'company_uuid': uuid_iceland,
         'workcenter': "iot4cps-wp5-WeatherService",
         'station': "Stations",
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'uuid': uuid_services,
         'company_uuid': uuid_iceland,
         'workcenter': "iot4cps-wp5-WeatherService",
         'station': "Services",
         'description': lorem_ipsum,
         'datetime': get_datetime()},
        {'uuid': uuid_roadanalytics,
         'company_uuid': uuid_datahouse,
         'workcenter': "iot4cps-wp5-Analytics",
         'station': "RoadAnalytics",
         'description': lorem_ipsum,
         'datetime': get_datetime()}]
    ResultProxy = conn.execute(query, values_list)

    # Insert is_admin_of_sys
    query = db.insert(app.config["tables"]["is_admin_of_sys"])
    values_list = [
        {'user_uuid': uuid_sue,
         'system_uuid': uuid_car1,
         'creator_uuid': uuid_sue,
         'datetime': get_datetime()},
        {'user_uuid': uuid_peter,
         'system_uuid': uuid_car1,
         'creator_uuid': uuid_sue,
         'datetime': get_datetime()},
        {'user_uuid': uuid_sue,
         'system_uuid': uuid_car2,
         'creator_uuid': uuid_sue,
         'datetime': get_datetime()},
        {'user_uuid': uuid_peter,
         'system_uuid': uuid_car2,
         'creator_uuid': uuid_sue,
         'datetime': get_datetime()},
        {'user_uuid': uuid_stefan,
         'system_uuid': uuid_stations,
         'creator_uuid': uuid_stefan,
         'datetime': get_datetime()},
        {'user_uuid': uuid_stefan,
         'system_uuid': uuid_services,
         'creator_uuid': uuid_stefan,
         'datetime': get_datetime()},
        {'user_uuid': uuid_anna,
         'system_uuid': uuid_roadanalytics,
         'creator_uuid': uuid_anna,
         'datetime': get_datetime()}]
    ResultProxy = conn.execute(query, values_list)

    # Insert client
    query = db.insert(app.config["tables"]["clients"])
    values_list = [
        {'name': "car_1",
         'system_uuid': uuid_car1,
         'metadata_name': "sensorthings",
         'metadata_uri': "http://localhost:8084",
         'creator_uuid': uuid_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "car_2",
         'system_uuid': uuid_car2,
         'metadata_name': "sensorthings",
         'metadata_uri': "http://localhost:8084",
         'creator_uuid': uuid_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "weatherstation_1",
         'system_uuid': uuid_stations,
         'metadata_name': "sensorthings",
         'metadata_uri': "http://localhost:8084",
         'creator_uuid': uuid_stefan,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "weatherstation_2",
         'system_uuid': uuid_stations,
         'metadata_name': "sensorthings",
         'metadata_uri': "http://localhost:8084",
         'creator_uuid': uuid_stefan,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "forecast_service",
         'system_uuid': uuid_services,
         'metadata_name': "sensorthings",
         'metadata_uri': "http://localhost:8084",
         'creator_uuid': uuid_stefan,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "datastack-adapter",
         'system_uuid': uuid_roadanalytics,
         'metadata_name': "sensorthings",
         'metadata_uri': "http://localhost:8084",
         'creator_uuid': uuid_anna,
         'datetime': get_datetime(),
         'description': lorem_ipsum}]
    ResultProxy = conn.execute(query, values_list)

    # Insert streams
    query = db.insert(app.config["tables"]["streams"])
    values_list = [
        {'name': "car1analytics",
         'system_uuid': uuid_car1,
         'source_system': "cz.icecars.iot4cps-wp5-CarFleet.Car1",
         'target_system': "at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics",
         'filter_logic': "",
         'is_multi_source': False,
         'function': "",
         'status': "init",
         'creator_uuid': uuid_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "car2analytics",
         'system_uuid': uuid_car2,
         'source_system': "cz.icecars.iot4cps-wp5-CarFleet.Car2",
         'target_system': "at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics",
         'filter_logic': "",
         'is_multi_source': False,
         'function': "",
         'status': "init",
         'creator_uuid': uuid_sue,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "weather2car1",
         'system_uuid': uuid_stations,
         'source_system': "is.iceland.iot4cps-wp5-WeatherService.Stations",
         'target_system': "cz.icecars.iot4cps-wp5-CarFleet.Car1",
         'filter_logic': "",
         'is_multi_source': False,
         'function': "",
         'status': "init",
         'creator_uuid': uuid_stefan,
         'datetime': get_datetime(),
         'description': lorem_ipsum},
        {'name': "weather2analytics",
         'system_uuid': uuid_stations,
         'source_system': "is.iceland.iot4cps-wp5-WeatherService.Stations",
         'target_system': "at.datahouse.iot4cps-wp5-Analytics.RoadAnalytics",
         'filter_logic': "",
         'is_multi_source': False,
         'function': "",
         'status': "init",
         'creator_uuid': uuid_stefan,
         'datetime': get_datetime(),
         'description': lorem_ipsum}]
    ResultProxy = conn.execute(query, values_list)

    engine.dispose()
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
