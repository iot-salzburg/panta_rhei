import os
import uuid
import logging
import psycopg2
import sqlalchemy as db

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, flash, redirect, url_for, session, request

# from .data import Articles
from functools import wraps
from passlib.hash import sha256_crypt
import wtforms
from wtforms import Form, StringField, TextField, TextAreaField, PasswordField, validators
from flask_bootstrap import Bootstrap

# load environment variables automatically from a .env file in the same directory
load_dotenv()

app = Flask(__name__)
Bootstrap(app)

# Set up SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI',
                                                  'postgresql+psycopg2://user:passwd@host/database')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "changeme"


def create_tables():
    # Create context, connection and metadata
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    connection = engine.connect()
    metadata = db.MetaData()

    # Define all entities and relations
    app.config["tables"] = dict()
    app.config["tables"]["users"] = db.Table(
        'users', metadata,
        db.Column('uuid', db.CHAR(36), primary_key=True, unique=True),
        db.Column('first_name', db.VARCHAR(25), nullable=False),
        db.Column('sur_name', db.VARCHAR(25), nullable=False),
        db.Column('birthdate', db.DATE, nullable=True),
        db.Column('email', db.VARCHAR(35), nullable=False, unique=True),
        db.Column('password', db.VARCHAR(80), nullable=False)
    )
    app.config["tables"]["companies"] = db.Table(
        'companies', metadata,
        db.Column('uuid', db.CHAR(36), primary_key=True, unique=True),
        db.Column('domain', db.VARCHAR(4), nullable=False),
        db.Column('enterprise', db.VARCHAR(15), nullable=False)
    )
    app.config["tables"]["systems"] = db.Table(
        'systems', metadata,
        db.Column('uuid', db.CHAR(36), primary_key=True, unique=True),
        db.Column('company_uuid', db.ForeignKey('companies.uuid')),
        db.Column('workcenter', db.VARCHAR(30), nullable=False),
        db.Column('station', db.VARCHAR(20), nullable=False)
    )
    app.config["tables"]["is_admin_of"] = db.Table(
        'is_admin_of', metadata,
        db.Column('user_uuid', db.ForeignKey("users.uuid"), primary_key=True),
        db.Column('company_uuid', db.ForeignKey('companies.uuid'), primary_key=True),
        db.Column('creator_uuid', db.ForeignKey("users.uuid"), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True)
    )
    app.config["tables"]["is_agent_of"] = db.Table(
        'is_agent_of', metadata,
        db.Column('user_uuid', db.ForeignKey("users.uuid"), primary_key=True),
        db.Column('system_uuid', db.ForeignKey('systems.uuid'), primary_key=True),
        db.Column('creator_uuid', db.ForeignKey("users.uuid"), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True)
    )
    app.config["tables"]["clients"] = db.Table(
        'clients', metadata,
        db.Column('name', db.VARCHAR(25), primary_key=True, unique=True),
        db.Column('system_uuid', db.ForeignKey('systems.uuid'), nullable=False),
        db.Column('keyfile', db.LargeBinary, nullable=False),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('creator_uuid', db.ForeignKey("users.uuid"), nullable=False)
    )
    metadata.create_all(engine)
    app.config["tables"]["gost_thing"] = db.Table(
        'gost_thing', metadata,
        db.Column('link', db.VARCHAR(50), nullable=False),
        db.Column('system_uuid', db.ForeignKey("systems.uuid"), primary_key=True)
    )
    metadata.create_all(engine)
    app.config["tables"]["gost_ds"] = db.Table(
        'gost_ds', metadata,
        db.Column('link', db.VARCHAR(50), nullable=False),
        db.Column('client_name', db.ForeignKey("clients.name"), primary_key=True),
        db.Column('system_uuid', db.ForeignKey("systems.uuid"), primary_key=True)
    )

    # Creates the tables
    metadata.create_all(engine)
    app.logger.info("Created tables.")


def get_uid():
    return str(uuid.uuid4()).split("-")[-1]


def insert_sample():
    # Create context, connection and metadata
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    connection = engine.connect()

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
         'email': 'sue.smith@gmail.com',
         'password': '12345678'},
        {'uuid': uuid_stefan,
         'first_name': 'Stefan',
         'sur_name': 'Gunnarsson',
         'birthdate': '1967-03-01',
         'email': 'stefan.gunnarsson@gmail.com',
         'password': '12345678'},
        {'uuid': uuid_peter,
         'first_name': 'Peter',
         'sur_name': 'Novak',
         'birthdate': '1990-02-01',
         'email': 'peter.novak@gmail.com',
         'password': '12345678'},
        {'uuid': uuid_anna,
         'first_name': 'Anna',
         'sur_name': 'Gruber',
         'birthdate': '1994-01-01',
         'email': 'anna.gruber@gmail.com',
         'password': '12345678'}]
    ResultProxy = connection.execute(query, values_list)
    results = connection.execute(db.select([app.config["tables"]["users"]])).fetchall()

    app.logger.info("Ingested data into tables.")


@app.route('/')
def index():
    return render_template('home.html')


# Register Form Class
class RegisterForm(Form):
    first_name = StringField('First Name', [validators.Length(min=1, max=50)])
    name = StringField('Name', [validators.Length(min=1, max=50)])
    # birthdate = wtforms.DateField("Birthdate")  #, format='%Y-%m-%d')
    # username = StringField('Username', [validators.Length(min=3, max=25)])
    email = StringField('Email', [validators.Email(message="The given email seems to be wrong")])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


# Register user
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        first_name = request.form["first_name"]  # form.name.data
        name = request.form["name"]  # form.name.data
        email = request.form["email"]  # form.email.data
        password = sha256_crypt.encrypt(str(request.form["password"]))  # form.password.data))

        # Create cursor
        engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        connection = engine.connect()

        query = db.insert(app.config["tables"]["users"])
        values_list = [{'uuid': get_uid(),
                        'first_name': first_name,
                        'sur_name': name,
                        'email': email,
                        'password': password}]
        ResultProxy = connection.execute(query, values_list)
        results = connection.execute(db.select([app.config["tables"]["users"]])).fetchall()

        flash("You are now registered and can log in", "success")
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        email = request.form['email']
        password_candidate = request.form['password']

        # Create cursor
        engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        connection = engine.connect()

        query = db.sql.text("SELECT * FROM users WHERE email = '{}'".format(email))

        connection.execute(query)

        ResultProxy = connection.execute(query)
        results = connection.execute(db.select([app.config["tables"]["users"]])).fetchall()
        print(results)

        if results is None:
            error = 'Username not found'
            return render_template('login.html', error=error)
        else:
            data = dict()
            s = ("uid", "name", "email", "password")
            for i, k in enumerate(s):
                data[k] = results[i]
            # Get stored hash
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['email'] = email

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)

    return render_template('login.html')


if __name__ == '__main__':
    app.logger.setLevel(logging.INFO)
    app.logger.info("Testing the platform.")

    # Creating the tables
    create_tables()

    # Insert sample for the demo scenario
    # insert_sample()

    # Create cursor
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    connection = engine.connect()

    query = "SELECT * FROM users"  #" WHERE email = '{}'".format("christoph.s.23@gmx.at")

    ResultProxy = connection.execute(query)
    results = ResultProxy.fetchall()
    data = list()
    for row in results:
        data.append({results[0].keys()[i]: row[i] for i in range(0, len(row))})
    print(results)
    print(data)
