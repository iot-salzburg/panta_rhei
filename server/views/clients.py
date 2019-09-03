import os

import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request, send_file
# Must be imported to use the app config
from flask import current_app as app
from wtforms import Form, StringField, validators, TextAreaField

from .useful_functions import get_datetime, is_logged_in, valid_level_name

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
    engine.dispose()
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
    creator.email AS contact_mail, clients.description, keyfile_av, agent.uuid AS agent_uuid, clients.datetime AS datetime
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
        engine.dispose()
        flash("It seems that this client doesn't exist.", "danger")
        return redirect(url_for("client.show_all_clients"))

    # Check if the current user is agent of the client's system
    if user_uuid not in [c["agent_uuid"] for c in clients]:
        engine.dispose()
        flash("You are not permitted see details this client.", "danger")
        return redirect(url_for("client.show_all_clients"))

    if session["key_status"] == "download":
        session["key_status"] = "init"
        flash("The key was downloaded. Keep in mind that this key can't' be downloaded twice!", "success")

        # Delete the zip file for security reasons
        # make directory with unique name
        zipname = "ssl_{}_{}.zip".format(system_uuid, client_name)
        dir_path = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(dir_path, "keys", zipname)
        os.remove(path)
        app.logger.info("Removed key.")

    # if not, agents has at least one item
    payload = clients[0]
    return render_template("/clients/show_client.html", payload=payload)


# Client Form Class
class ClientForm(Form):
    name = StringField("Name", [validators.Length(min=2, max=20), valid_level_name])
    description = TextAreaField("Description", [validators.Length(max=16*1024)])


def create_keyfile(name="testclient", system_uuid="12345678"):
    import shutil
    # TODO create a real keyfile

    # make directory with unique name
    dirname = "ssl_{}_{}".format(system_uuid, name)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    path = os.path.join(dir_path, "keys", dirname)
    # print("Create dir with name: {}".format(path))
    os.mkdir(path)

    # Create keyfiles in the path
    os.mkfifo(os.path.join(path, "cert-signed"))
    os.mkfifo(os.path.join(path, "client-cert-signed"))

    # create zip archive and delete directory
    shutil.make_archive(path, "zip", path)
    app.logger.info("Create zip with name: {}".format(path))
    os.remove(os.path.join(path, "cert-signed"))
    os.remove(os.path.join(path, "client-cert-signed"))
    os.rmdir(path)


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
def add_client_for_system(system_uuid):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # The basic client form is used
    form = ClientForm(request.form)

    # Fetch clients of the system, for with the user is agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT sys.uuid AS system_uuid, domain, enterprise, workcenter, station, agent.uuid AS agent_uuid
    FROM systems AS sys
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}' AND sys.uuid='{}';""".format(user_uuid, system_uuid)
    result_proxy = conn.execute(query)
    clients = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched clients: {}".format(clients))

    # Check if the system exists and you are an admin
    if len(clients) == 0:
        engine.dispose()
        flash("It seems that this system doesn't exist.", "danger")
        return redirect(url_for("system.show_all_systems"))

    # Check if the current user is agent of the system
    if user_uuid not in [c["agent_uuid"] for c in clients]:
        engine.dispose()
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
                            "description": form.description.data,
                            'datetime': get_datetime(),
                            'keyfile_av': True}]
            conn.execute(query, values_list)
            engine.dispose()
            # Create keyfile based on the given information
            create_keyfile(name=form.name.data, system_uuid=system_uuid)
            flash("The client {} was created .".format(form.name.data), "success")
            return redirect(url_for("client.show_client", system_uuid=system_uuid, client_name=form.name.data))
        else:
            engine.dispose()
            flash("The client with name {} was already created for system {}.{}.{}.{}.".format(
                form.name.data, payload["domain"], payload["enterprise"], payload["workcenter"], payload["station"]),
                "danger")
            return redirect(url_for("client.add_client", system_uuid=system_uuid))

    return render_template("/clients/add_client.html", form=form, payload=payload)


# Delete client
@client.route("/delete_client/<string:system_uuid>/<string:client_name>", methods=["GET"])
@is_logged_in
def delete_client(system_uuid, client_name):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

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
        engine.dispose()
        flash("It seems that this system doesn't exist.", "danger")
        return redirect(url_for("client.show_all_clients"))

    # Check if the current user is agent of the system
    if user_uuid not in [c["agent_uuid"] for c in clients]:
        engine.dispose()
        flash("You are not permitted to delete clients of this system.", "danger")
        return redirect(url_for("client.show_client", system_uuid=system_uuid, client_name=client_name))

    # Delete the specified client
    query = """DELETE FROM clients
        WHERE system_uuid='{}' AND name='{}';""".format(system_uuid, client_name)
    conn.execute(query)
    engine.dispose()

    flash("The client with name {} was deleted.".format(client_name), "success")

    # Redirect to /show_system/system_uuid
    return redirect(url_for("system.show_system", system_uuid=system_uuid))


# download key as zip
@client.route("/download_key/<string:system_uuid>/<string:client_name>", methods=["GET"])
@is_logged_in
def download_key(system_uuid, client_name):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Only the creator of an client is allowed to download the key
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT system_uuid, name, creator.email AS contact_mail, creator_uuid
    FROM clients
    INNER JOIN users as creator ON creator.uuid=clients.creator_uuid
    WHERE creator_uuid='{}' AND system_uuid='{}';""".format(user_uuid, system_uuid)
    result_proxy = conn.execute(query)
    engine.dispose()
    clients = [dict(c.items()) for c in result_proxy.fetchall()]

    # Check if the system exists and you are an admin
    if len(clients) == 0:
        flash("It seems that this system doesn't exist.", "danger")
        return redirect(url_for("client.show_all_clients"))

    # Check if the current user is agent of the system
    if user_uuid != clients[0]["creator_uuid"]:
        flash("You are not permitted to delete clients of this system.", "danger")
        return redirect(url_for("client.show_client", system_uuid=system_uuid, client_name=client_name))

    zipname = "ssl_{}_{}.zip".format(system_uuid, client_name)
    dir_path = os.path.dirname(os.path.realpath(__file__))
    filepath = os.path.join(dir_path, "keys", zipname)

    if os.path.exists(filepath):
        engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
        conn = engine.connect()  # no transactions as they aren't threadsafe
        query = """UPDATE clients
        SET keyfile_av=False
        WHERE name='{}' AND system_uuid='{}';""".format(client_name, system_uuid)
        result_proxy = conn.execute(query)
        engine.dispose()

        # Set the status to download in order to flash a message in client.show_client
        # This Session value must be reset there!
        session["key_status"] = "download"
        return send_file(
                        filepath,
                        mimetype='application/zip',
                        as_attachment=True,
                        attachment_filename=zipname) and redirect(url_for("client.show_client", system_uuid=system_uuid, client_name=client_name))

    flash("The key file was not found.", "danger")
    return redirect(url_for("client.show_client", system_uuid=system_uuid, client_name=client_name))
