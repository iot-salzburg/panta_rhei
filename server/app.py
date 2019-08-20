import os
import uuid
import json
import logging
import psycopg2
import sqlalchemy as db
from sqlalchemy import exc as sqlalchemy_exc

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint, Flask, render_template, flash , redirect, url_for, session, request

# from .data import Articles
from functools import wraps
from passlib.hash import sha256_crypt
import wtforms
from wtforms import Form, StringField, TextField, TextAreaField, PasswordField, validators

from server.views.useful_functions import get_datetime, get_uid, is_logged_in

# load environment variables automatically from a .env file in the same directory
load_dotenv()

# Create Flask app and load configs
app = Flask(__name__)
# app.config.from_object('config')
app.config.from_envvar('APP_CONFIG_FILE')

from server.views.company import company
app.register_blueprint(company)  # url_prefix='/comp')

from server.views.auth import auth
app.register_blueprint(auth)  # url_prefix='/comp')


def create_tables():
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
        db.Column('keyfile', db.LargeBinary, nullable=False),
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
        'password': sha256_crypt.encrypt('12345678')},
       {'uuid': uuid_stefan,
        'first_name': 'Stefan',
        'sur_name': 'Gunnarsson',
        'birthdate': '1967-03-01',
        'email': 'stefan.gunnarsson@gmail.com',
        'password': sha256_crypt.encrypt('12345678')},
       {'uuid': uuid_peter,
        'first_name': 'Peter',
        'sur_name': 'Novak',
        'birthdate': '1990-02-01',
        'email': 'peter.novak@gmail.com',
        'password': sha256_crypt.encrypt('12345678')},
       {'uuid': uuid_anna,
        'first_name': 'Anna',
        'sur_name': 'Gruber',
        'birthdate': '1994-01-01',
        'email': 'anna.gruber@gmail.com',
        'password': sha256_crypt.encrypt('12345678')},
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
    # try:
    query = db.insert(app.config["tables"]["is_admin_of"])
    values_list = [
        {'user_uuid': uuid_sue,
         'company_uuid': uuid_icecars,
         'creator_uuid': uuid_sue},
        {'user_uuid': uuid_stefan,
         'company_uuid': uuid_iceland,
         'creator_uuid': uuid_stefan},
        {'user_uuid': uuid_anna,
         'company_uuid': uuid_datahouse,
         'creator_uuid': uuid_anna}]
    ResultProxy = conn.execute(query, values_list)


    app.logger.info("Ingested data into tables.")


@app.route('/')
def index():
    return render_template('dashboard.html')


@app.route('/about')
def about():
    return render_template('about.html')



@app.route("/dashboard")
@is_logged_in
def dashboard():
    # Create cursor
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    conn = engine.connect()

    # Get articles
    ResultProxy = conn.execute("SELECT * FROM companies;")
    result = ResultProxy.fetchall()

    if result is not None:
        data = list()
        s = ("uuid", "domain", "enterprise")
        for line in result:
            entry = dict()
            for i, k in enumerate(s):
                entry[k] = line[i]
            data.append(entry)
            # print(data)
        return render_template("dashboard.html", articles=data)
    msg = "No articles found"

    return render_template("dashboard.html", msg=msg)




# Article Form Class
class ArticleForm(Form):
    title = StringField('Title', [validators.Length(min=1, max=50)])
    body = TextAreaField('Body', [validators.Length(min=30)])


@app.route('/articles')
def articles():
    # Create cursor
    conn = psycopg2.connect(dbname='myflaskapp', user='chris', host='localhost', password='postgres')
    cur = conn.cursor()

    # Get articles
    cur.execute("SELECT * FROM articles;")
    result = cur.fetchall()
    # Close connection
    cur.close()

    if result is not None:
        data = list()
        s = ("id", "title", "author", "body", "create_date")
        for line in result:
            entry = dict()
            for i, k in enumerate(s):
                entry[k] = line[i]
            data.append(entry)
            # print(data)
        return render_template("articles.html", articles=data)
    msg = "No articles found"

    return render_template("articles.html", msg=msg)


@app.route('/article/<string:id>')
def article(id):
    # Create cursor
    conn = psycopg2.connect(dbname='myflaskapp', user='chris', host='localhost', password='postgres')
    cur = conn.cursor()

    # Get articles
    cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    result = cur.fetchone()
    # Close connection
    cur.close()

    if result is not None:
        s = ("id", "title", "author", "body", "create_date")
        entry = dict()
        for i, k in enumerate(s):
            entry[k] = result[i]
            # print(data)
        return render_template("article.html", article=entry)

# Add article
@app.route("/add_article", methods=["GET", "POST"])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method == 'POST' and form.validate():
        title = form.title.data
        body = form.body.data

        # Create cursor
        conn = psycopg2.connect(dbname='myflaskapp', user='chris', host='localhost', password='postgres')
        cur = conn.cursor()

        # Insert article
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s,%s,%s)", (title,body,session["username"]))
        conn.commit()

        # Close connection
        cur.close()

        flash("Article Created", "success")

        return redirect(url_for("dashboard"))

    return render_template("add_article.html", form=form)


# Edit article
@app.route("/edit_article/<string:id>", methods=["GET", "POST"])
@is_logged_in
def edit_article(id):
    # Create cursor
    conn = psycopg2.connect(dbname='myflaskapp', user='chris', host='localhost', password='postgres')
    cur = conn.cursor()

    # Get article by id
    cur.execute("SELECT * FROM articles WHERE id = %s", [id])
    result = cur.fetchone()

    data = dict()
    s = ("id", "title", "author", "body", "create_date")
    for i, k in enumerate(s):
        data[k] = result[i]

    # Get form
    form = ArticleForm(request.form)

    # Populate article form fields
    form.title.data = data["title"]
    form.body.data = data["body"]

    if request.method == "POST" and form.validate():
        title = request.form['title']
        body = request.form['body']

        # # insert article
        # cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title,body,id))
        # conn.commit()

        # Close connection
        cur.close()

        flash("Article Updated", "success")

        return redirect(url_for("dashboard"))

    return render_template("edit_article.html", form=form)


# Delete article
@app.route("/delete_article/<string:id>", methods=["POST"])
@is_logged_in
def delete_article(id):
    # Create cursor
    conn = psycopg2.connect(dbname='myflaskapp', user='chris', host='localhost', password='postgres')
    cur = conn.cursor()

    # Get article by id
    cur.execute("DELETE FROM articles WHERE id = %s", [id])
    conn.commit()
    conn.close()

    flash("Article Deleted", "success")
    return redirect(url_for("dashboard"))


if __name__ == '__main__':
    app.logger.setLevel(logging.INFO)
    app.logger.info("Starting the platform.")

    # Creating the tables
    create_tables()

    # Insert sample for the demo scenario
    # insert_sample()

    # Run application
    app.run(debug=app.config["DEBUG"], port=5000)
