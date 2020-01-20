import json
import subprocess

import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request

from flask import current_app as app
from wtforms import Form, StringField, validators, TextAreaField

from .useful_functions import get_datetime, is_logged_in, valid_name, valid_system

streamhub_bp = Blueprint("streamhub", __name__)


@streamhub_bp.route("/streamhub")
@is_logged_in
def show_all_streams():
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Fetch streams, for which systems the current user is agent of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """
    SELECT sys.uuid AS system_uuid, streams.name, status, source_system, target_system, creator.email AS contact_mail
    FROM streams
    INNER JOIN users as creator ON creator.uuid=streams.creator_uuid
    INNER JOIN systems AS sys ON streams.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_admin_of_sys AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}'
    ORDER BY source_system, target_system, streams.name;""".format(user_uuid)
    result_proxy = conn.execute(query)
    engine.dispose()
    streams = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched streams: {}".format(streams))

    return render_template("/streamhub/streams.html", streams=streams)


@streamhub_bp.route("/show_stream/<string:system_uuid>/<string:stream_name>")
@is_logged_in
def show_stream(system_uuid, stream_name):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    payload = get_stream_payload(user_uuid, system_uuid, stream_name)
    if not isinstance(payload, dict):
        return payload

    # Check if the process is running
    if check_if_proc_runs(system_uuid, stream_name):
        payload["status"] = "running"
        set_status_to(system_uuid, stream_name, "running")

    # The stream doesn't run
    else:
        app.logger.debug("The stream '{}' doesn't run.".format(payload["name"]))
        # Get SOLL status
        engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
        conn = engine.connect()
        query = "SELECT status FROM streams WHERE system_uuid='{}' AND name='{}';".format(system_uuid, stream_name)
        result_proxy = conn.execute(query)
        engine.dispose()
        status = [dict(c.items()) for c in result_proxy.fetchall()][0]["status"]
        app.logger.debug("The stream '{}' has the SOLL status {}.".format(stream_name, status))

        if status == "running" or status == "starting":
            set_status_to(system_uuid, stream_name, "failing")
        # else:
        #     set_status_to(system_uuid, stream_name, "idle")

    # TODO update filter_logic
    # TODO show docker status of filter_logic
    # filter_logic = {"client_name": client_name,
    #           "system": "{}.{}.{}.{}".format(payload["domain"], payload["enterprise"],
    #                                          payload["workcenter"], payload["station"]),
    #           "gost_servers": "localhost:8084",
    #           "kafka_bootstrap_servers": app.config["KAFKA_BOOTSTRAP_SERVER"]}

    return render_template("/streamhub/show_stream.html", payload=payload)  # , filter_logic=filter_logic)


# Streamhub Form Class
class StreamhubForm(Form):
    name = StringField("Name", [validators.Length(min=2, max=20), valid_name])
    target_system = StringField("Target System", [validators.Length(max=72), valid_system])
    filter_logic = TextAreaField("Filter Logic", [validators.Length(max=4 * 1024)])
    description = TextAreaField("Description", [validators.Length(max=16 * 1024)])


# Add stream in all_streams view, redirect to systems
@streamhub_bp.route("/add_stream")
@is_logged_in
def add_stream():
    # redirect to systems
    flash("Specify the system to which a new stream should be added.", "info")
    return redirect(url_for("system.show_all_systems"))


# Add client in system view
@streamhub_bp.route("/add_stream/<string:system_uuid>", methods=["GET", "POST"])
@is_logged_in
def add_stream_for_system(system_uuid):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # The basic client form is used
    form = StreamhubForm(request.form)
    form_target_system = form.target_system.data.strip()
    form_name = form.name.data.strip()

    # Fetch all streams for the requested system and user agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """
    SELECT sys.uuid AS system_uuid, domain, enterprise, workcenter, station, agent.uuid AS agent_uuid
    FROM systems AS sys
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_admin_of_sys AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}' AND sys.uuid='{}';""".format(user_uuid, system_uuid)
    result_proxy = conn.execute(query)
    clients = [dict(c.items()) for c in result_proxy.fetchall()]
    print("Fetched streams: {}".format(clients))

    # Check if the system exists and has agents
    if len(clients) == 0:
        engine.dispose()
        flash("It seems that this stream doesn't exist or you are not permitted see details this stream.", "danger")
        return redirect(url_for("streamhub.show_all_streams"))

    # if not, streams has at least one item
    payload = clients[0]
    source_system = "{}.{}.{}.{}".format(payload["domain"], payload["enterprise"],
                                         payload["workcenter"], payload["station"])

    # Create a new stream using the form's input
    if request.method == "POST" and form.validate():
        # Check if source and target system are different
        if source_system == form_target_system:
            msg = "The source and target system can't be the equal."
            app.logger.info(msg)
            flash(msg, "danger")
            return redirect(url_for("streamhub.add_stream_for_system", system_uuid=system_uuid))

        # Create stream and check if the combination of the system_uuid and name exists
        query = """SELECT system_uuid, name
        FROM systems
        INNER JOIN streams ON streams.system_uuid=systems.uuid
        WHERE system_uuid='{}' AND name='{}';""".format(system_uuid, form_name)
        result_proxy = conn.execute(query)

        if len(result_proxy.fetchall()) == 0:
            query = db.insert(app.config["tables"]["streams"])
            values_list = [{'name': form_name,
                            'system_uuid': system_uuid,
                            'source_system': source_system,
                            'target_system': form_target_system,
                            'filter_logic': form.filter_logic.data,
                            'creator_uuid': user_uuid,
                            'datetime': get_datetime(),
                            'description': form.description.data}]
            conn.execute(query, values_list)
            engine.dispose()

            msg = "The stream '{}' was added to system '{}'.".format(form_name, source_system)
            app.logger.info(msg)
            flash(msg, "success")
            return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, stream_name=form_name))
        else:
            engine.dispose()
            msg = "The stream with name '{}' was already created for system '{}'.".format(form_name, source_system)
            app.logger.info(msg)
            flash(msg, "danger")
            return redirect(url_for("streamhub.add_stream_for_system", system_uuid=system_uuid))

    return render_template("/streamhub/add_stream.html", form=form, payload=payload)


# Delete stream
@streamhub_bp.route("/delete_stream/<string:system_uuid>/<string:stream_name>", methods=["GET"])
@is_logged_in
def delete_stream(system_uuid, stream_name):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Fetch streams of the system, for with the user is agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT sys.uuid AS system_uuid, streams.name AS name, source_system, target_system, 
    creator.email AS contact_mail, agent.uuid AS agent_uuid
    FROM streams
    INNER JOIN users as creator ON creator.uuid=streams.creator_uuid
    INNER JOIN systems AS sys ON streams.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_admin_of_sys AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}'
    AND sys.uuid='{}';""".format(user_uuid, system_uuid)
    result_proxy = conn.execute(query)
    streams = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched streams: {}".format(streams))

    # Check if the system exists and you are an agent
    if len(streams) == 0:
        engine.dispose()
        flash("It seems that this stream doesn't exist.", "danger")
        return redirect(url_for("streamhub.show_all_streams"))

    # Check if the current user is agent of the system
    if user_uuid not in [c["agent_uuid"] for c in streams]:
        engine.dispose()
        flash("You are not permitted to delete streams of this system.", "danger")
        return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, client_name=stream_name))

    # Delete the specified stream
    query = """DELETE FROM streams
        WHERE system_uuid='{}' AND name='{}';""".format(system_uuid, stream_name)
    conn.execute(query)
    engine.dispose()

    msg = "The stream '{}' of system '{}' was deleted.".format(stream_name, streams[0]["source_system"])
    app.logger.info(msg)
    flash(msg, "success")

    # Redirect to /show_system/system_uuid
    return redirect(url_for("system.show_system", system_uuid=system_uuid))


def get_stream_payload(user_uuid, system_uuid, stream_name):
    # Fetch all streams for the requested system and user agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """
    SELECT sys.uuid AS system_uuid, com.uuid AS company_uuid, streams.name, status, source_system, target_system, 
    creator.email AS contact_mail, streams.description, agent.uuid AS agent_uuid, streams.datetime AS datetime,
    filter_logic
    FROM streams
    INNER JOIN users as creator ON creator.uuid=streams.creator_uuid
    INNER JOIN systems AS sys ON streams.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_admin_of_sys AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE sys.uuid='{}' AND streams.name='{}';""".format(system_uuid, stream_name)
    result_proxy = conn.execute(query)
    engine.dispose()
    streams = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched streams: {}".format(streams))

    # Check if the system exists and has agents
    if len(streams) == 0:
        flash("It seems that this stream doesn't exist.", "danger")
        return redirect(url_for("streamhub.show_all_streams"))

    # Check if the current user is agent of the client's system
    if user_uuid not in [c["agent_uuid"] for c in streams]:
        flash("You are not permitted see details this stream.", "danger")
        return redirect(url_for("streamhub.show_all_streams"))

    # if not, agents has at least one item
    return streams[0]


# #################### Streams ####################

@streamhub_bp.route("/start_stream/<string:system_uuid>/<string:stream_name>", methods=["GET"])
@is_logged_in
def start_stream(system_uuid, stream_name):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    payload = get_stream_payload(user_uuid, system_uuid, stream_name)
    if len(payload["filter_logic"]) <= 1:  # TODO check if filter_logic is valid
        payload["filter_logic"] = "{}"

    if not isinstance(payload, dict):
        return payload

    # Check if the process is already running
    if check_if_proc_runs(system_uuid, stream_name):
        msg = "The stream '{}' already runs.".format(payload["name"])
        app.logger.debug(msg)
        flash(msg, "info")
        return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, stream_name=payload["name"]))

    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    transaction = conn.begin()
    # try:
    # Start the jar file
    cmd_list = ['java', '-jar', 'views/StreamEngine.jar']
    cmd_list += ['--stream-name', stream_name]
    cmd_list += ['--source-system', payload["source_system"]]
    cmd_list += ['--target-system', payload["target_system"]]
    cmd_list += ['--bootstrap-server', app.config["KAFKA_BOOTSTRAP_SERVER"]]
    cmd_list += ['--filter-logic', payload["filter_logic"]]
    cmd = " ".join(cmd_list)
    app.logger.debug("Try to deploy '{}'".format(cmd))

    proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    store_stream(system_uuid, stream_name, proc)

    app.logger.debug("Deployed stream {} with pid: {}".format(stream_name, proc.pid))

    # Set status in DB
    set_status_to(system_uuid, stream_name, "starting")

    transaction.commit()
    app.logger.debug("Stream with pid {} runs? {}".format(proc.pid, check_if_proc_runs(system_uuid, stream_name)))
    msg = "The stream '{}' is starting.".format(payload["name"])
    app.logger.info(msg)
    flash(msg, "success")

    return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, stream_name=payload["name"]))


@streamhub_bp.route("/stop_stream/<string:system_uuid>/<string:stream_name>", methods=["GET"])
@is_logged_in
def stop_stream(system_uuid, stream_name):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    payload = get_stream_payload(user_uuid, system_uuid, stream_name)
    if not isinstance(payload, dict):
        return payload

    # load configs of stream
    pid, cmd = load_stream(system_uuid, stream_name)
    #
    # if pid == 0 or not check_if_proc_runs(system_uuid, stream_name):
    #     set_status_to(system_uuid, stream_name, "idle")
    #     msg = "The stream '{}' doesn't run.".format(payload["name"])
    #     app.logger.info(msg)
    #     flash(msg, "info")
    #     return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, stream_name=payload["name"]))

    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    transaction = conn.begin()
    try:
        # Stop the stream
        procps = subprocess.Popen("ps -ef | grep '{}'".format(cmd), shell=True,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        res = procps.communicate()[0].decode()
        for proc_line in res.split("\n"):
            if proc_line == "":
                continue
            # app.logger.debug("proc_line: {}".format(proc_line))
            proc_pid = proc_line.split()[1]
            prockill_res = subprocess.Popen("kill -9 {}".format(proc_pid), shell=True,
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
            if not prockill_res[1]:
                app.logger.debug("Successfully killed process with pid {}".format(proc_pid))
            else:
                app.logger.debug("Can't remove process with pid {}: {}".format(proc_pid, prockill_res[1].decode()))

        # Set status
        set_status_to(system_uuid, stream_name, "idle")

        msg = "The stream '{}' is stopping.".format(payload["name"])
        app.logger.info(msg)
        flash(msg, "success")
    except Exception as e:
        transaction.rollback()
        app.logger.info("The stream '{}' couldn't be stopped, because {}".format(payload["name"], e))
        flash("The stream '{}' couldn't be stopped.".format(payload["name"]), "success")
    finally:
        return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, stream_name=payload["name"]))


def check_if_proc_runs(system_uuid, stream_name):
    app.logger.debug("check_if_proc_runs")
    # load config
    pid, cmd = load_stream(system_uuid, stream_name)
    if pid is None:
        app.logger.debug("Init status, no process.")
        return False

    pipe = subprocess.Popen("ps -ef | grep '{}'".format(cmd), shell=True, stdout=subprocess.PIPE)
    try:
        output = pipe.communicate()
        res = output[0].decode("utf-8")
        app.logger.debug(res)
        # if "StreamEngine.jar" not in res:
        for proc_line in res.split("\n"):
            if proc_line == "":
                continue
            if "grep" not in proc_line.replace(cmd, ""):
                app.logger.debug("The process is running.")
                return True
        app.logger.debug("The process is not running.")
        return False
    except ValueError:
        app.logger.debug("Process with pid {} doesn't exist.".format(pid))
        return False


def set_status_to(system_uuid, stream_name, status):
    # Set status
    app.logger.debug("Set status to {}".format(status))
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """UPDATE streams SET status='{status}' WHERE system_uuid='{system_uuid}' AND name='{stream_name}';""". \
        format(status=status, system_uuid=system_uuid, stream_name=stream_name)
    conn.execute(query)
    engine.dispose()


def load_stream(system_uuid, stream_name):
    try:
        with open("templates/streamhub/streamhub.json") as f:
            content = json.loads(f.read())
    except FileNotFoundError:
        with open("templates/streamhub/streamhub.json", "w") as f:
            f.write(json.dumps(dict(), indent=2))
        return None, None
    try:
        pid = content[system_uuid][stream_name]["pid"]
        cmd = content[system_uuid][stream_name]["cmd"]
        return pid, cmd
    except KeyError:
        return None, None


def store_stream(system_uuid, stream_name, proc):
    try:
        with open("templates/streamhub/streamhub.json") as f:
            content = json.loads(f.read())
    except FileNotFoundError:
        content = dict()

    if system_uuid not in content.keys():
        content[system_uuid] = dict()
    if stream_name not in content[system_uuid].keys():
        content[system_uuid][stream_name] = dict()
    content[system_uuid][stream_name]["pid"] = proc.pid
    content[system_uuid][stream_name]["cmd"] = proc.args

    with open("templates/streamhub/streamhub.json", "w") as f:
        f.write(json.dumps(content, indent=2))
