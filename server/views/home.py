import logging
import sqlalchemy as db
from flask import current_app as app
from flask import Blueprint, render_template, flash, redirect, url_for, session, request

from .useful_functions import is_logged_in

home_bp = Blueprint("home", __name__)


@home_bp.route('/')
# @cache.cached(timeout=60)
def index():
    return redirect(url_for("home.dashboard"))


@home_bp.route("/dashboard")
def dashboard():
    # Redirect to home if not logged in
    if 'logged_in' not in session:
        return redirect(url_for("home.home"))

    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Fetch companies, for which the current user is admin of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()

    # fetch name of user
    query = """SELECT first_name, sur_name FROM users WHERE uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    users = [dict(c.items()) for c in result_proxy.fetchall()]
    if users == list():
        flash("Please login.", "danger")
        return redirect(url_for("auth.login"))
    user = users[0]
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

    # fetch dedicated systems
    query = """SELECT sys.uuid AS system_uuid, domain, enterprise, workcenter, station, agent.email AS contact_mail
    FROM systems AS sys
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    systems = [dict(c.items()) for c in result_proxy.fetchall()]

    # Fetch clients, for which systems the current user is agent of
    query = """SELECT sys.uuid AS system_uuid, name, domain, enterprise, workcenter, station, creator.email AS contact_mail
    FROM clients
    INNER JOIN users as creator ON creator.uuid=clients.creator_uuid
    INNER JOIN systems AS sys ON clients.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    clients = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched clients: {}".format(clients))

    # Fetch streams, for which systems the current user is agent of
    query = """
    SELECT sys.uuid AS system_uuid, streams.name, status, source_system, target_system, creator.email AS contact_mail
    FROM streams
    INNER JOIN users as creator ON creator.uuid=streams.creator_uuid
    INNER JOIN systems AS sys ON streams.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    streams = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched streams: {}".format(streams))

    engine.dispose()
    payload = dict()
    payload["SOURCE_URL"] = app.config["SOURCE_URL"]
    return render_template("dashboard.html", companies=companies, systems=systems, clients=clients, streams=streams,
                           session=session, payload=payload)


@home_bp.route('/about')
def about():
    return render_template('about.html')


@home_bp.route('/home')
def home():
    payload = dict()
    payload["SOURCE_URL"] = app.config["SOURCE_URL"]
    return render_template('home.html', payload=payload)


@home_bp.route('/search', methods=['GET', 'POST'])
@is_logged_in
def search():
    search_request = request.args.get('request').strip().lower()
    app.logger.info("Searching for: {}".format(search_request))

    # Get current user_uuid
    user_uuid = session["user_uuid"]
    messages = dict()
    # msg_systems = msg_companies = msg_clients = msg_streamhub = None

    # Fetch companies, for which the current user is admin of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()

    # fetch dedicated companies
    query = """SELECT company_uuid, com.*, creator.email AS contact_mail
    FROM companies AS com 
    INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
    INNER JOIN users as admin ON admin.uuid=aof.user_uuid
    INNER JOIN users as creator ON creator.uuid=aof.creator_uuid
    WHERE admin.uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    companies = [dict(c.items()) for c in result_proxy.fetchall()]
    # Filter systems by term
    companies = [item for item in companies if search_request in str(list(item.values())).lower()]
    # print("Fetched companies: {}".format(companies))
    if companies == list():
        messages["companies"] = "No companies found."

    # fetch dedicated systems
    query = """SELECT sys.uuid AS system_uuid, domain, enterprise, sys.*, agent.email AS contact_mail
    FROM systems AS sys
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    systems = [dict(c.items()) for c in result_proxy.fetchall()]
    # Filter systems by term
    systems = [item for item in systems if search_request in str(list(item.values())).lower()]
    if len(systems) == 0:
        messages["systems"] = "No systems found."

    # fetch dedicated clients
    query = """SELECT sys.uuid AS system_uuid, name, domain, enterprise, workcenter, station, 
    creator.email AS contact_mail, clients.*
    FROM clients
    INNER JOIN users as creator ON creator.uuid=clients.creator_uuid
    INNER JOIN systems AS sys ON clients.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    clients = [dict(c.items()) for c in result_proxy.fetchall()]
    # Filter systems by term
    clients = [item for item in clients if search_request in str(list(item.values())).lower()]
    if len(clients) == 0:
        messages["clients"] = "No clients found."

    # fetch dedicated streams
    query = """
    SELECT sys.uuid AS system_uuid, streams.*, creator.email AS contact_mail
    FROM streams
    INNER JOIN users as creator ON creator.uuid=streams.creator_uuid
    INNER JOIN systems AS sys ON streams.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    streams = [dict(c.items()) for c in result_proxy.fetchall()]
    # Filter systems by term
    streams = [item for item in streams if search_request in str(list(item.values())).lower()]
    if len(streams) == 0:
        messages["streams"] = "No streams found."

    engine.dispose()
    found_count = len(companies) + len(systems) + len(clients) + len(streams)
    if found_count >= 1:
        flash("Received {} results for search request '{}'".format(found_count, search_request), "info")
    else:
        flash("Received no results for search request '{}'".format(found_count, search_request), "danger")
    return render_template("search.html", companies=companies, systems=systems, clients=clients, streams=streams,
                           messages=messages, search_request=search_request)
