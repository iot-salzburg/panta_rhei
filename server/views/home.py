import logging
import sqlalchemy as db
from flask import current_app as app
from flask import Blueprint, render_template, flash, redirect, url_for, session, request

home_bp = Blueprint("home", __name__)


@home_bp.route('/')
def index():
    return redirect(url_for("home.dashboard"))


@home_bp.route("/dashboard")
def dashboard():
    # Redirect to home if not logged in
    if 'logged_in' not in session:
        flash("You are not logged in yet. Let's start here!", "info")
        return redirect(url_for("home.home"))

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
    # print("Fetched companies: {}".format(companies))
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
    if len(systems) == 0:
        msg_companies = "No companies found."

    return render_template("dashboard.html", companies=companies, systems=systems, msg_systems=msg_systems,
                           msg_companies=msg_companies, session=session)


@home_bp.route('/about')
def about():
    return render_template('about.html')


@home_bp.route('/home')
def home():
    return render_template('home.html')
