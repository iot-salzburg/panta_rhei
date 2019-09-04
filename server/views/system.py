import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request
# Must be imported to use the app config
from flask import current_app as app
from sqlalchemy import exc as sqlalchemy_exc
from wtforms import Form, StringField, validators, TextAreaField

from .useful_functions import get_datetime, get_uid, is_logged_in, valid_level_name

system = Blueprint("system", __name__)  # url_prefix="/comp")


@system.route("/systems")
@is_logged_in
def show_all_systems():
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Set url (is used in system.delete_system)
    session["last_url"] = "/systems"

    # Fetch systems, for which the current user is agent of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT sys.uuid AS system_uuid, domain, enterprise, workcenter, station, agent.email AS contact_mail
    FROM systems AS sys
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    engine.dispose()
    systems = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched companies: {}".format(companies))

    return render_template("/systems/systems.html", systems=systems)


@system.route("/show_system/<string:system_uuid>")
@is_logged_in
def show_system(system_uuid):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Fetch all agents for the requested system
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """
    SELECT sys.uuid AS system_uuid, domain, enterprise, sys.description, workcenter, station, sys.datetime AS sys_datetime,
    agent.uuid AS agent_uuid, agent.first_name, agent.sur_name, agent.email AS agent_mail, creator.email AS creator_mail
    FROM systems AS sys
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    INNER JOIN users as creator ON creator.uuid=agf.creator_uuid 
    WHERE sys.uuid='{}';""".format(system_uuid)
    result_proxy = conn.execute(query)
    agents = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched agents: {}".format(agents))

    # Check if the system exists and has agents
    if len(agents) == 0:
        engine.dispose()
        flash("It seems that this system doesn't exist.", "danger")
        return redirect(url_for("system.show_all_systems"))

    # Check if the current user is agent of the system
    if user_uuid not in [c["agent_uuid"] for c in agents]:
        engine.dispose()
        flash("You are not permitted see details this system.", "danger")
        return redirect(url_for("system.show_all_systems"))

    # Fetch clients of the system, for with the user is agent
    query = """SELECT sys.uuid AS system_uuid, name, domain, enterprise, workcenter, station, creator.email AS contact_mail
    FROM clients
    INNER JOIN users as creator ON creator.uuid=clients.creator_uuid
    INNER JOIN systems AS sys ON clients.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}'
    AND sys.uuid='{}';""".format(user_uuid, system_uuid)
    result_proxy = conn.execute(query)
    engine.dispose()
    clients = [dict(c.items()) for c in result_proxy.fetchall()]

    # if not, agents has at least one item
    payload = agents[0]
    return render_template("/systems/show_system.html", agents=agents, payload=payload, clients=clients)


# System Form Class
class SystemForm(Form):
    workcenter = StringField("Workcenter", [validators.Length(min=2, max=30), valid_level_name])
    station = StringField("Station", [validators.Length(min=2, max=20), valid_level_name])
    description = TextAreaField("Description", [validators.Length(max=16*1024)])

# Add system in system view, redirect to companies
@system.route("/add_system")
@is_logged_in
def add_system():
    # redirect to companies
    flash("Specify the company to which a system should be added.", "info")
    return redirect(url_for("company.show_all_companies"))

# Add system in company view
@system.route("/add_system/<string:company_uuid>", methods=["GET", "POST"])
@is_logged_in
def add_system_for_company(company_uuid):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # The basic company form is used
    form = SystemForm(request.form)
    form.workcenter.label = "Workcenter short-name"

    # Get payload
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """
    SELECT company_uuid, domain, enterprise, admin.uuid AS admin_uuid, admin.first_name, admin.sur_name, admin.email 
    FROM companies AS com 
    INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
    INNER JOIN users as admin ON admin.uuid=aof.user_uuid 
    INNER JOIN users as creator ON creator.uuid=aof.creator_uuid 
    WHERE company_uuid='{}';""".format(company_uuid)
    result_proxy = conn.execute(query)
    admins = [dict(c.items()) for c in result_proxy.fetchall()]

    # Check if the company exists and you are an admin
    if len(admins) == 0:
        engine.dispose()
        flash("It seems that this company doesn't exist.", "danger")
        return redirect(url_for("company.show_all_companies"))

    # Check if the current user is admin of the company
    if user_uuid not in [c["admin_uuid"] for c in admins]:
        engine.dispose()
        flash("You are not permitted to add systems for this company.", "danger")
        return redirect(url_for("company.show_all_companies"))

    # if not, admins has at least one item
    payload = admins[0]

    # Create a new system and agent-relation using the form"s input
    if request.method == "POST" and form.validate():
        # Create system and check if either the system_uuid or the system exists
        system_uuids = ["init"]
        system_uuid = get_uid()
        while system_uuids != list():
            system_uuid = get_uid()
            query = """SELECT uuid FROM systems WHERE uuid='{}';""".format(system_uuid)
            result_proxy = conn.execute(query)
            system_uuids = result_proxy.fetchall()

        query = """SELECT domain, enterprise FROM systems
                INNER JOIN companies ON systems.company_uuid=companies.uuid
                WHERE domain='{}' AND enterprise='{}' AND workcenter='{}' AND station='{}';
                """.format(payload["domain"], payload["enterprise"], form.workcenter.data, form.station.data)
        result_proxy = conn.execute(query)
        if len(result_proxy.fetchall()) == 0:
            query = db.insert(app.config["tables"]["systems"])
            values_list = [{"uuid": system_uuid,
                            "company_uuid": payload["company_uuid"],
                            "workcenter": form.workcenter.data,
                            "station": form.station.data,
                            "datetime": get_datetime(),
                            "description": form.description.data}]
            conn.execute(query, values_list)
        else:
            engine.dispose()
            flash("The system {}.{}.{}.{} already exists.".format(
                payload["domain"], payload["enterprise"], form.workcenter.data, form.station.data), "danger")
            return redirect(url_for("company.show_company", company_uuid=company_uuid))

        # Create new is_admin_of instance
        query = db.insert(app.config["tables"]["is_agent_of"])
        values_list = [{"user_uuid": user_uuid,
                        "system_uuid": system_uuid,
                        "creator_uuid": user_uuid,
                        "datetime": get_datetime()}]
        try:
            conn.execute(query, values_list)
            engine.dispose()
            msg = "The system {}.{} within the company {}.{} was created.".format(
                form.workcenter.data, form.station.data, payload["domain"], payload["enterprise"])
            app.logger.info(msg)
            flash(msg, "success")
            return redirect(url_for("company.show_company", company_uuid=company_uuid))

        except sqlalchemy_exc.IntegrityError as e:
            engine.dispose()
            print("An Integrity Error occured: {}".format(e))
            flash("An unexpected error occured.", "danger")
            return render_template("login.html")

    return render_template("/systems/add_system.html", form=form, payload=payload)


# Delete system
# TODO restrict deleting if clients exist
@system.route("/delete_system/<string:system_uuid>", methods=["GET"])
@is_logged_in
def delete_system(system_uuid):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Check if you are agent of this system
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT company_uuid, domain, enterprise, workcenter, station
        FROM companies AS com
        INNER JOIN systems AS sys ON com.uuid=sys.company_uuid
        INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid
        WHERE agf.user_uuid='{}'
        AND agf.system_uuid='{}';""".format(user_uuid, system_uuid)
    result_proxy = conn.execute(query)
    permitted_systems = [dict(c.items()) for c in result_proxy.fetchall()]
    print(user_uuid)
    print(system_uuid)
    print("permitted systems: {}".format(permitted_systems))

    if permitted_systems == list():
        engine.dispose()
        flash("You are not permitted to delete this system.", "danger")
        return redirect(url_for("system.show_all_systems"))

    # Check if you are the last agent of the system
    query = """SELECT company_uuid, domain, enterprise, workcenter, station
        FROM companies AS com
        INNER JOIN systems AS sys ON com.uuid=sys.company_uuid
        INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid
        AND agf.system_uuid='{}';""".format(system_uuid)
    result_proxy = conn.execute(query)

    if len(result_proxy.fetchall()) >= 2:
        engine.dispose()
        flash("You are not permitted to delete a system which has multiple agents.", "danger")
        return redirect(url_for("system.show_system", system_uuid=system_uuid))

    # Check if there are client applications for that system
    query = """SELECT system_uuid, clients.name AS client_name
        FROM systems
        INNER JOIN clients ON systems.uuid=clients.system_uuid
        WHERE system_uuid='{}';""".format(system_uuid)
    result_proxy = conn.execute(query)

    if len(result_proxy.fetchall()) >= 1:
        engine.dispose()
        flash("You are not permitted to delete a system which has client applications.", "danger")
        return redirect(url_for("system.show_system", system_uuid=system_uuid))

    # Now the system can be deleted
    selected_system = permitted_systems[0]  # This list has only one element

    # Delete new is_admin_of instance
    query = """DELETE FROM is_agent_of
        WHERE system_uuid='{}';""".format(system_uuid)
    conn.execute(query)

    # Delete system
    query = """DELETE FROM systems
        WHERE uuid='{}';""".format(system_uuid)
    conn.execute(query)

    engine.dispose()
    msg = "The system {}.{}.{}.{} was deleted.".format(selected_system["domain"], selected_system["enterprise"],
                                                       selected_system["workcenter"], selected_system["station"])
    app.logger.info(msg)
    flash(msg, "success")

    # Redirect to latest page, either /systems or /show_company/UID
    if session.get("last_url"):
        return redirect(session.get("last_url"))
    return redirect(url_for("system.show_all_systems"))


# Agent Management Form Class
class AgentForm(Form):
    email = StringField("Email", [validators.Email(message="The given email seems to be wrong.")])


@system.route("/add_agent_system/<string:system_uuid>", methods=["GET", "POST"])
@is_logged_in
def add_agent_system(system_uuid):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    form = AgentForm(request.form)

    # Check if you are agent of this system
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT company_uuid, system_uuid, domain, enterprise, workcenter, station
        FROM companies AS com
        INNER JOIN systems AS sys ON com.uuid=sys.company_uuid
        INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid
        WHERE agf.user_uuid='{}'
        AND agf.system_uuid='{}';""".format(user_uuid, system_uuid)
    result_proxy = conn.execute(query)
    permitted_systems = [dict(c.items()) for c in result_proxy.fetchall()]

    if permitted_systems == list():
        engine.dispose()
        flash("You are not permitted to add an agent for this system.", "danger")
        return redirect(url_for("show_system", system_uuid=system_uuid))

    payload = permitted_systems[0]

    if request.method == "POST" and form.validate():
        email = form.email.data

        # Check if the user is registered
        query = """SELECT * FROM users WHERE email='{}';""".format(email)
        result_proxy = conn.execute(query)
        found_users = [dict(c.items()) for c in result_proxy.fetchall()]

        if found_users == list():
            engine.dispose()
            flash("No user was found with this email address.", "danger")
            return render_template("/systems/add_agent_system.html", form=form, payload=payload)

        user = found_users[0]
        # Check if the user is already agent of this system
        query = """SELECT system_uuid, user_uuid FROM is_agent_of
        WHERE user_uuid='{}' AND system_uuid='{}';""".format(user["uuid"], system_uuid)
        result_proxy = conn.execute(query)
        if result_proxy.fetchall() != list():
            engine.dispose()
            flash("This user is already agent of this system.", "danger")
            return render_template("/systems/add_agent_system.html", form=form, payload=payload)

        # Create new is_agent_of instance
        query = db.insert(app.config["tables"]["is_agent_of"])
        values_list = [{"user_uuid": user["uuid"],
                        "system_uuid": payload["system_uuid"],
                        "creator_uuid": user_uuid,
                        "datetime": get_datetime()}]
        conn.execute(query, values_list)
        engine.dispose()

        flash("The user {} was added to {}.{}.{}.{} as an agent.".format(
            email, payload["domain"], payload["enterprise"], payload["workcenter"], payload["station"]), "success")
        return redirect(url_for("system.show_system", system_uuid=system_uuid))

    return render_template("/systems/add_agent_system.html", form=form, payload=payload)

# Delete agent for system
@system.route("/delete_agent_system/<string:system_uuid>/<string:agent_uuid>", methods=["GET"])
@is_logged_in
def delete_agent_system(system_uuid, agent_uuid):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Check if you are agent of this system
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT company_uuid, system_uuid, domain, enterprise, workcenter, station
            FROM companies AS com
            INNER JOIN systems AS sys ON com.uuid=sys.company_uuid
            INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid
            WHERE agf.user_uuid='{}'
            AND agf.system_uuid='{}';""".format(user_uuid, system_uuid)
    result_proxy = conn.execute(query)
    permitted_systems = [dict(c.items()) for c in result_proxy.fetchall()]

    if permitted_systems == list():
        engine.dispose()
        flash("You are not permitted to add an agent for this system.", "danger")
        return redirect(url_for("system.show_system", system_uuid=system_uuid))

    if user_uuid == agent_uuid:
        engine.dispose()
        flash("You can't remove yourself.", "danger")
        return redirect(url_for("system.show_system", system_uuid=system_uuid))

    # get info for the deleted agent
    query = """SELECT company_uuid, system_uuid, domain, enterprise, workcenter, station, agent.email AS email, 
    agent.uuid AS agent_uuid 
    FROM companies AS com
    INNER JOIN systems AS sys ON com.uuid=sys.company_uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}'
    AND agf.system_uuid='{}';""".format(agent_uuid, system_uuid)
    result_proxy = conn.execute(query)
    del_users = [dict(c.items()) for c in result_proxy.fetchall()]

    if del_users == list():
        engine.dispose()
        flash("nothing to delete.", "danger")
        return redirect(url_for("company.show_all_systems"))

    del_user = del_users[0]
    # Delete new is_agent_of instance
    query = """DELETE FROM is_agent_of
        WHERE user_uuid='{}'
        AND system_uuid='{}';""".format(agent_uuid, system_uuid)
    conn.execute(query)
    # print("DELETING: {}".format(query))

    engine.dispose()
    flash("User with email {} was removed as agent from system {}.{}.{}.{}.".format(
        del_user["email"], del_user["domain"], del_user["enterprise"], del_user["workcenter"], del_user["station"]),
        "success")
    return redirect(url_for("system.show_system", system_uuid=system_uuid))
