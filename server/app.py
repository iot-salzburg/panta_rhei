import os
import uuid
import logging
import psycopg2
import sqlalchemy as db
from sqlalchemy import exc as sqlalchemy_exc

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, flash , redirect, url_for, session, request

# from .data import Articles
from functools import wraps
from passlib.hash import sha256_crypt
import wtforms
from wtforms import Form, StringField, TextField, TextAreaField, PasswordField, validators

# load environment variables automatically from a .env file in the same directory
load_dotenv()

app = Flask(__name__)

# Set up SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI',
                                                  'postgresql+psycopg2://user:passwd@host/database')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "changeme"


def create_tables():
    # Create context, connection and metadata
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    conn = engine.connect()
    metadata = db.MetaData()

    # Define all entities and relations
    app.config["tables"] = dict()
    app.config["tables"]["users"] = db.Table(
        'users', metadata,
        db.Column('uuid', db.VARCHAR(12), primary_key=True, unique=True),
        db.Column('first_name', db.VARCHAR(25), nullable=False),
        db.Column('sur_name', db.VARCHAR(25), nullable=False),
        db.Column('birthdate', db.DATE, nullable=True),
        db.Column('email', db.VARCHAR(35), nullable=False, unique=True),
        db.Column('password', db.VARCHAR(80), nullable=False)
        )
    app.config["tables"]["companies"] = db.Table(
        'companies', metadata,
        db.Column('uuid', db.VARCHAR(12), primary_key=True, unique=True),
        db.Column('domain', db.VARCHAR(4), nullable=False),
        db.Column('enterprise', db.VARCHAR(15), nullable=False)
        )
    app.config["tables"]["systems"] = db.Table(
        'systems', metadata,
        db.Column('uuid', db.VARCHAR(12), primary_key=True, unique=True),
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
    app.config["tables"]["gost_thing"] = db.Table(
        'gost_thing', metadata,
        db.Column('link', db.VARCHAR(50), nullable=False),
        db.Column('system_uuid', db.ForeignKey("systems.uuid"), primary_key=True)
        )
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
    conn = engine.connect()

    # Inserting many records at ones in users
    uuid_sue = get_uid()
    uuid_stefan = get_uid()
    uuid_peter = get_uid()
    uuid_anna = get_uid()
    query = db.insert(app.config["tables"]["users"])
    values_list = [
        {'uuid': uuid_sue,
        'first_name':'Sue',
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
    ResultProxy = conn.execute(query, values_list)
    results = ResultProxy.fetchall()

    # uuid_icecars = get_uid()
    # uuid_iceland = get_uid()
    # uuid_datahouse = get_uid()
    # # Inserting many records at ones in company
    # query = db.insert(app.config["tables"]["companies"])
    # values_list = [
    #     {'uuid': get_uid(),
    #      'domain': 'cz',
    #      'enterprise': 'icecars'},
    #     {'uuid': get_uid(),
    #      'domain': 'is',
    #      'enterprise': 'iceland'},
    #     {'uuid': get_uid(),
    #      'domain': 'at',
    #      'enterprise': 'datahouse'}]
    # ResultProxy = conn.execute(query, values_list)
    # results = ResultProxy.fetchall()

    app.logger.info("Ingested data into tables.")


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/about')
def about():
    return render_template('about.html')


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

# Register Form Class
class RegisterForm(Form):
    first_name = StringField('First Name', [validators.Length(min=1, max=50)])
    name = StringField('Name', [validators.Length(min=1, max=50)])
    birthdate = wtforms.DateField("Birthdate", format='%Y-%m-%d')
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
        # Create cursor
        engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        conn = engine.connect()

        query = db.insert(app.config["tables"]["users"])
        values_list = [{'uuid': get_uid(),
                        'first_name': request.form["first_name"],
                        'sur_name': request.form["name"],
                        'birthdate': request.form["birthdate"],
                        'email': request.form["email"],
                        'password': sha256_crypt.encrypt(str(request.form["password"]))}]
        try:
            ResultProxy = conn.execute(query, values_list)
            flash("You are now registered and can log in", "success")
            return redirect(url_for('login'))

        except sqlalchemy_exc.IntegrityError:
            flash("You are already registered with this email. Please log in", "danger")
            return render_template('register.html', form=form)

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
        conn = engine.connect()

        query = "SELECT * FROM users WHERE email = '{}'".format(email)
        ResultProxy = conn.execute(query)
        results = ResultProxy.fetchall()

        data = list()
        for row in results:
            data.append({results[0].keys()[i]: row[i] for i in range(0, len(row))})

        if len(data) == 0:
            error = 'Username not found.'
            return render_template('login.html', error=error)
        # elif len(data) != 1:
        #     error = 'Username was found twice. Error'
        #     return render_template('login.html', error=error)
        else:
            password = data[0]['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['email'] = email

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login.'
                return render_template('login.html', error=error)

    return render_template('login.html')


# Check if user is logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("Unauthorized. Please login", "danger")
            return redirect(url_for("login"))

    return wrap


# User logout
@app.route("/logout")
@is_logged_in
def logout():
    session.clear()
    flash("You are now logged out", "success")
    return redirect(url_for("login"))


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

        # insert article
        cur.execute("UPDATE articles SET title=%s, body=%s WHERE id=%s", (title,body,id))
        conn.commit()

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

    # app.secret_key = "1234"
    app.run(debug=True, port=5000)
