import os
import logging
import psycopg2
import sqlalchemy as db

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, flash , redirect, url_for, session, request

# from .data import Articles
from functools import wraps
from passlib.hash import sha256_crypt
from wtforms import Form, StringField, TextAreaField, PasswordField, validators

# load environment variables automatically from a .env file in the same directory
load_dotenv()

app = Flask(__name__)

# Set up SQLAlchemy
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI',
                                                  'postgresql+psycopg2://user:passwd@host/database')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


def create_tables():
    # Create context, connection and metadata
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
    app.config["companies"] = db.Table(
        'companies', metadata,
        db.Column('uuid', db.CHAR(36), primary_key=True, unique=True),
        db.Column('domain', db.VARCHAR(4), nullable=False),
        db.Column('enterprise', db.VARCHAR(15), nullable=False)
        )
    app.config["systems"] = db.Table(
        'systems', metadata,
        db.Column('uuid', db.CHAR(36), primary_key=True, unique=True),
        db.Column('company_uuid', db.ForeignKey('companies.uuid')),
        db.Column('workcenter', db.VARCHAR(30), nullable=False),
        db.Column('station', db.VARCHAR(20), nullable=False)
        )
    app.config["is_admin_of"] = db.Table(
        'is_admin_of', metadata,
        db.Column('user_uuid', db.ForeignKey("users.uuid"), primary_key=True),
        db.Column('company_uuid', db.ForeignKey('companies.uuid'), primary_key=True),
        db.Column('creator_uuid', db.ForeignKey("users.uuid"), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True)
        )
    app.config["is_agent_of"] = db.Table(
        'is_agent_of', metadata,
        db.Column('user_uuid', db.ForeignKey("users.uuid"), primary_key=True),
        db.Column('system_uuid', db.ForeignKey('systems.uuid'), primary_key=True),
        db.Column('creator_uuid', db.ForeignKey("users.uuid"), nullable=False),
        db.Column('datetime', db.DateTime, nullable=True)
        )
    app.config["clients"] = db.Table(
        'clients', metadata,
        db.Column('name', db.VARCHAR(25), primary_key=True, unique=True),
        db.Column('keyfile', db.LargeBinary, nullable=False),
        db.Column('datetime', db.DateTime, nullable=True),
        db.Column('creator_uuid', db.ForeignKey("users.uuid"), nullable=False),
        db.Column('system_uuid', db.ForeignKey('systems.uuid'), nullable=False)
        )
    app.config["gost_ds"] = db.Table(
        'gost_ds', metadata,
        db.Column('link', db.VARCHAR(50), primary_key=True),
        db.Column('client_name', db.ForeignKey("clients.name"), nullable=False)
        )
    app.config["gost_thing"] = db.Table(
        'gost_thing', metadata,
        db.Column('link', db.VARCHAR(50), primary_key=True),
        db.Column('client_name', db.ForeignKey("clients.name"), nullable=False)
        )

    emp = db.Table('emp', metadata,
                  db.Column('Id', db.Integer()),
                  db.Column('name', db.String(255), nullable=False),
                  db.Column('salary', db.Float(), default=100.0),
                  db.Column('active', db.Boolean(), default=True)
                  )

    # Creates the tables
    metadata.create_all(engine)

    #Inserting many records at ones
    query = db.insert(emp)
    values_list = [{'Id':'2', 'name':'ram', 'salary':80000, 'active':False},
                   {'Id':'3', 'name':'ramesh', 'salary':70000, 'active':True}]
    ResultProxy = connection.execute(query,values_list)
    results = connection.execute(db.select([emp])).fetchall()
    print(results)

    # db = SQLAlchemy(app)
    app.logger.info("Created tables.")

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
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
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
        name = request.form["name"]  # form.name.data
        email = request.form["email"]  # form.email.data
        username = request.form["username"]  # form.username.data
        password = sha256_crypt.encrypt(str(request.form["password"]))  # form.password.data))

        # Create cursor
        conn = psycopg2.connect(dbname='myflaskapp', user='chris', host='localhost', password='postgres')
        cur = conn.cursor()

        cur.execute("INSERT INTO users(name, email, username, password) "
                    "VALUES(%s,%s,%s,%s)", (name, email, username, password))
        conn.commit()
        # Commit to postgres
        cur.close()

        flash("You are now registered and can log in", "success")

        return redirect(url_for('login'))

    return render_template('register.html', form=form)

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']

        # Create cursor
        conn = psycopg2.connect(dbname='myflaskapp', user='chris', host='localhost', password='postgres')
        cur = conn.cursor()

        # Get user by username
        cur.execute("SELECT * FROM users WHERE username = %s", [username])
        result = cur.fetchone()
        # Close connection
        cur.close()

        if result is not None:
            data = dict()
            s = ("id", "name", "email", "username", "password")
            for i, k in enumerate(s):
                data[k] = result[i]
            # Get stored hash
            password = data['password']

            # Compare Passwords
            if sha256_crypt.verify(password_candidate, password):
                # Passed
                session['logged_in'] = True
                session['username'] = username

                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')


# Check if user is logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("Unauthorized, Please login", "danger")
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

    # app.secret_key = "1234"
    # app.run(debug=True, port=5000)

