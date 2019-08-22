import logging

import sqlalchemy as db
from dotenv import load_dotenv
from flask import Flask, session, render_template, redirect, url_for

# from .data import Articles

# Import application-specific functions
try:
    from server.views.useful_functions import get_datetime, get_uid, is_logged_in
except ModuleNotFoundError:
    from views.useful_functions import get_datetime, get_uid, is_logged_in

# Import modules
from server.views.auth import auth
from server.views.company import company
from server.views.system import system
from server.create_database import create_tables


# load environment variables automatically from a .env file in the same directory
load_dotenv()

# Create Flask app and load configs
app = Flask(__name__)
# app.config.from_object('config')
app.config.from_envvar('APP_CONFIG_FILE')

# Register modules as blueprint
app.register_blueprint(company)  # url_prefix='/companies')
app.register_blueprint(system)  # url_prefix='/systems')
app.register_blueprint(auth)  # url_prefix='/auth')


@app.route('/')
def home():
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@is_logged_in
def dashboard():
    # Get current user_uuid
    user_uuid = session["user_uuid"]
    msg_systems = msg_companies = None

    # Fetch companies, for which the current user is admin of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()

    # fetch name of user
    query = """SELECT first_name, sur_name FROM users WHERE uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    user = [dict(c.items()) for c in result_proxy.fetchall()][0]
    session["first_name"] = user["first_name"]
    session["sur_name"] = user["sur_name"]

    # fetch dedicated companies
    query = """SELECT company_uuid, domain, enterprise, creator.email AS contact_mail
    FROM companies AS com 
    INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
    INNER JOIN users as admin ON admin.uuid=aof.user_uuid
    INNER JOIN users as creator ON creator.uuid=aof.creator_uuid
    WHERE admin.uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    companies = [dict(c.items()) for c in result_proxy.fetchall()]
    print("Fetched companies: {}".format(companies))
    if companies == list():
        msg_companies = "No companies found."

    # fetch dedicated systems
    query = """SELECT sys.uuid AS system_uuid, domain, enterprise, workcenter, station, agent.email AS contact_mail
    FROM systems AS sys
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    systems = [dict(c.items()) for c in result_proxy.fetchall()]
    print(systems)
    if len(systems) == 0:
        msg_companies = "No companies found."

    return render_template("dashboard.html", companies=companies,  systems=systems, msg_systems=msg_systems,
                           msg_companies=msg_companies, session=session)


@app.route('/about')
def about():
    return render_template('about.html')


if __name__ == '__main__':
    app.logger.setLevel(logging.INFO)
    app.logger.info("Starting the platform.")

    # Create tables to get the data model
    create_tables(app)

    # Run application
    app.run(debug=app.config["DEBUG"], port=5000)
