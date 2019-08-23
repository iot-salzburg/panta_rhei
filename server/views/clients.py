import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request
# Must be imported to use the app config
from flask import current_app as app
from sqlalchemy import exc as sqlalchemy_exc
from wtforms import Form, StringField, validators

from .useful_functions import get_datetime, get_uid, is_logged_in

client = Blueprint("client", __name__)  # url_prefix="/comp")


@client.route("/clients")
@is_logged_in
def show_all_clients():
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Fetch clients, for which systems the current user is agent of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
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

    return render_template("/clients/clients.html", clients=clients)


@client.route("/show_client/<string:system_uuid>/<string:client_name>")
@is_logged_in
def show_client(system_uuid, client_name):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Fetch all clients for the requested system and user agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT sys.uuid AS system_uuid, com.uuid AS company_uuid, name, domain, enterprise, workcenter, station, 
    creator.email AS contact_mail, keyfile, agent.uuid AS agent_uuid
    FROM clients
    INNER JOIN users as creator ON creator.uuid=clients.creator_uuid
    INNER JOIN systems AS sys ON clients.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE sys.uuid='{}' AND clients.name='{}';""".format(system_uuid, client_name)
    result_proxy = conn.execute(query)
    clients = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched agents: {}".format(agents))

    # Check if the system exists and has agents
    if len(clients) == 0:
        flash("It seems that this client doesn't exist.", "danger")
        return redirect(url_for("client.show_all_clients"))

    # Check if the current user is agent of the client's system
    if user_uuid not in [c["agent_uuid"] for c in clients]:
        flash("You are not permitted see details this client.", "danger")
        return redirect(url_for("client.show_all_clients"))

    # if not, agents has at least one item
    payload = clients[0]
    return render_template("/clients/show_client.html", payload=payload)


# Client Form Class
class ClientForm(Form):
    name = StringField("Name", [validators.Length(min=2, max=20)])


def create_keyfile():
    # TODO create keyfile
    return "This will be made later"


# Add client in clients view, redirect to systems
@client.route("/add_client")
@is_logged_in
def add_client():
    # redirect to systems
    flash("Specify the system to which a client should be added.", "info")
    return redirect(url_for("system.show_all_systems"))


# Add client in system view
@client.route("/add_client/<string:system_uuid>", methods=["GET", "POST"])
@is_logged_in
def add_client_for_company(system_uuid):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # The basic client form is used
    form = ClientForm(request.form)

    # Fetch clients of the system, for with the user is agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT sys.uuid AS system_uuid, name, domain, enterprise, workcenter, station, 
    creator.email AS contact_mail, agent.uuid AS agent_uuid
    FROM clients
    INNER JOIN users as creator ON creator.uuid=clients.creator_uuid
    INNER JOIN systems AS sys ON clients.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}'
    AND sys.uuid='{}';""".format(user_uuid, system_uuid)
    result_proxy = conn.execute(query)
    clients = [dict(c.items()) for c in result_proxy.fetchall()]

    # Check if the system exists and you are an admin
    if len(clients) == 0:
        flash("It seems that this system doesn't exist.", "danger")
        return redirect(url_for("system.show_all_systems"))

    # Check if the current user is agent of the system
    if user_uuid not in [c["agent_uuid"] for c in clients]:
        flash("You are not permitted to add clients for this system.", "danger")
        return redirect(url_for("system.show_all_systems"))

    # if not, clients has at least one item
    payload = clients[0]

    # Create a new client using the form"s input
    if request.method == "POST" and form.validate():
        # Create client and check if the combination of the system_uuid and name exists
        query = """SELECT system_uuid, name 
        FROM systems
        INNER JOIN clients ON clients.system_uuid=systems.uuid
        WHERE system_uuid='{}' AND name='{}';""".format(system_uuid, form.name.data)
        result_proxy = conn.execute(query)
        if len(result_proxy.fetchall()) == 0:
            query = db.insert(app.config["tables"]["clients"])
            values_list = [{'name': form.name.data,
                            'system_uuid': system_uuid,
                            'creator_uuid': user_uuid,
                            'datetime': get_datetime(),
                            'keyfile': create_keyfile()}]
            conn.execute(query, values_list)
            flash("The client {} was created for the  system {}.{}.{}.{}.".format(form.name.data,
                payload["domain"], payload["enterprise"], payload["workcenter"], payload["station"]), "success")
            return redirect(url_for("client.show_client", system_uuid=system_uuid, client_name=form.name.data))
        else:
            flash("The client with name {} was already created for system {}.{}.{}.{}.".format(form.name.data,
                payload["domain"], payload["enterprise"], payload["workcenter"], payload["station"]), "danger")
            return redirect(url_for("client.add_client", system_uuid=system_uuid))

    return render_template("/clients/add_client.html", form=form, payload=payload)


# # Delete system
# # TODO restrict deleting if clients exist
# @system.route("/delete_system/<string:system_uuid>", methods=["GET"])
# @is_logged_in
# def delete_system(system_uuid):
#     # Get current user_uuid
#     user_uuid = session["user_uuid"]
#
#     # Check if you are agent of this system
#     engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
#     conn = engine.connect()
#     query = """SELECT company_uuid, domain, enterprise, workcenter, station
#         FROM companies AS com
#         INNER JOIN systems AS sys ON com.uuid=sys.company_uuid
#         INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid
#         WHERE agf.user_uuid='{}'
#         AND agf.system_uuid='{}';""".format(user_uuid, system_uuid)
#     result_proxy = conn.execute(query)
#     permitted_systems = [dict(c.items()) for c in result_proxy.fetchall()]
#
#     if permitted_systems == list():
#         flash("You are not permitted to delete this system.", "danger")
#         return redirect(url_for("system.show_all_systems"))
#
#     # Check if you are the last agent of the system
#     query = """SELECT company_uuid, domain, enterprise, workcenter, station
#         FROM companies AS com
#         INNER JOIN systems AS sys ON com.uuid=sys.company_uuid
#         INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid
#         AND agf.system_uuid='{}';""".format(system_uuid)
#     result_proxy = conn.execute(query)
#
#     if len(result_proxy.fetchall()) >= 2:
#         flash("You are not permitted to delete a system which has multiple agents.", "danger")
#         return redirect(url_for("system.show_all_systems"))
#
#     # Now the system can be deleted
#     selected_system = permitted_systems[0]  # This list has only one element
#
#     # Delete new is_admin_of instance
#     query = """DELETE FROM is_agent_of
#         WHERE system_uuid='{}';""".format(system_uuid)
#     conn.execute(query)
#
#     # Delete system
#     query = """DELETE FROM systems
#         WHERE uuid='{}';""".format(system_uuid)
#     conn.execute(query)
#
#     flash("The system {}.{}.{}.{} was deleted.".format(selected_system["domain"], selected_system["enterprise"],
#                                                        selected_system["workcenter"], selected_system["station"]),
#           "success")
#
#     # Redirect to latest page, either /systems or /show_company/UID
#     if session.get("url"):
#         return redirect(session.get("url"))
#     return redirect(url_for("system.show_all_systems"))
#
#
# # Agent Management Form Class
# class AgentForm(Form):
#     email = StringField("Email", [validators.Email(message="The given email seems to be wrong")])
#
#
# @system.route("/add_agent_system/<string:system_uuid>", methods=["GET", "POST"])
# @is_logged_in
# def add_agent_system(system_uuid):
#     # Get current user_uuid
#     user_uuid = session["user_uuid"]
#
#     form = AgentForm(request.form)
#
#     # Check if you are agent of this system
#     engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
#     conn = engine.connect()
#     query = """SELECT company_uuid, system_uuid, domain, enterprise, workcenter, station
#         FROM companies AS com
#         INNER JOIN systems AS sys ON com.uuid=sys.company_uuid
#         INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid
#         WHERE agf.user_uuid='{}'
#         AND agf.system_uuid='{}';""".format(user_uuid, system_uuid)
#     result_proxy = conn.execute(query)
#     permitted_systems = [dict(c.items()) for c in result_proxy.fetchall()]
#
#     if permitted_systems == list():
#         flash("You are not permitted to add an agent for this system.", "danger")
#         return redirect(url_for("show_system", system_uuid=system_uuid))
#
#     payload = permitted_systems[0]
#
#     if request.method == "POST" and form.validate():
#         email = form.email.data
#
#         # Check if the user is registered
#         query = """SELECT * FROM users WHERE email='{}';""".format(email)
#         result_proxy = conn.execute(query)
#         found_users = [dict(c.items()) for c in result_proxy.fetchall()]
#
#         if found_users == list():
#             flash("No user was found with this email address.", "danger")
#             return render_template("/systems/add_agent_system.html", form=form, payload=payload)
#
#         user = found_users[0]
#         # Check if the user is already agent of this system
#         query = """SELECT system_uuid, user_uuid FROM is_agent_of
#         WHERE user_uuid='{}' AND system_uuid='{}';""".format(user["uuid"], system_uuid)
#         result_proxy = conn.execute(query)
#         if result_proxy.fetchall() != list():
#             flash("This user is already agent of this system.", "danger")
#             return render_template("/systems/add_agent_system.html", form=form, payload=payload)
#
#         # Create new is_agent_of instance
#         query = db.insert(app.config["tables"]["is_agent_of"])
#         values_list = [{"user_uuid": user["uuid"],
#                         "system_uuid": payload["system_uuid"],
#                         "creator_uuid": user_uuid,
#                         "datetime": get_datetime()}]
#         conn.execute(query, values_list)
#         flash("The user {} was added to {}.{}.{}.{} as an agent.".format(
#             email, payload["domain"], payload["enterprise"], payload["workcenter"], payload["station"]), "success")
#         return redirect(url_for("system.show_system", system_uuid=system_uuid))
#
#     return render_template("/systems/add_agent_system.html", form=form, payload=payload)
#
# # Delete agent for system
# @system.route("/delete_agent_system/<string:system_uuid>/<string:agent_uuid>", methods=["GET"])
# @is_logged_in
# def delete_agent_system(system_uuid, agent_uuid):
#     # Get current user_uuid
#     user_uuid = session["user_uuid"]
#
#     # Check if you are agent of this system
#     engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
#     conn = engine.connect()
#     query = """SELECT company_uuid, system_uuid, domain, enterprise, workcenter, station
#             FROM companies AS com
#             INNER JOIN systems AS sys ON com.uuid=sys.company_uuid
#             INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid
#             WHERE agf.user_uuid='{}'
#             AND agf.system_uuid='{}';""".format(user_uuid, system_uuid)
#     result_proxy = conn.execute(query)
#     permitted_systems = [dict(c.items()) for c in result_proxy.fetchall()]
#
#     if permitted_systems == list():
#         flash("You are not permitted to add an agent for this system.", "danger")
#         return redirect(url_for("system.show_system", system_uuid=system_uuid))
#
#     if user_uuid == agent_uuid:
#         flash("You are not permitted to remove yourself.", "danger")
#         return redirect(url_for("system.show_system", system_uuid=system_uuid))
#
#     # get info for the deleted agent
#     query = """SELECT company_uuid, system_uuid, domain, enterprise, workcenter, station, agent.email AS email,
#     agent.uuid AS agent_uuid
#     FROM companies AS com
#     INNER JOIN systems AS sys ON com.uuid=sys.company_uuid
#     INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid
#     INNER JOIN users as agent ON agent.uuid=agf.user_uuid
#     WHERE agent.uuid='{}'
#     AND agf.system_uuid='{}';""".format(agent_uuid, system_uuid)
#     result_proxy = conn.execute(query)
#     del_users = [dict(c.items()) for c in result_proxy.fetchall()]
#
#     if del_users == list():
#         flash("nothing to delete.", "danger")
#         return redirect(url_for("company.show_all_systems"))
#
#     del_user = del_users[0]
#     # Delete new is_agent_of instance
#     query = """DELETE FROM is_agent_of
#         WHERE user_uuid='{}'
#         AND system_uuid='{}';""".format(agent_uuid, system_uuid)
#     conn.execute(query)
#     # print("DELETING: {}".format(query))
#
#     flash("User with email {} was removed as agent from system {}.{}.{}.{}.".format(
#         del_user["email"], del_user["domain"], del_user["enterprise"], del_user["workcenter"], del_user["station"]),
#         "success")
#     return redirect(url_for("system.show_system", system_uuid=system_uuid))
