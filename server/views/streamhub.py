import json
import string
import subprocess
import time
from functools import wraps, update_wrapper

import pytz
from datetime import datetime

import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request, send_file, make_response

from flask import current_app as app, Response
from wtforms import Form, StringField, validators, TextAreaField

from .useful_functions import get_datetime, is_logged_in, valid_name, valid_system, nocache
from .StreamHandler import stream_checks, fab_streams


streamhub_bp = Blueprint("streamhub", __name__)

# PROCESS_FILE = "templates/streamhub/streamhub.json"
LOG_FILE = "templates/streamhub/template_stream.log"


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

    return render_template("streamhub/streams.html", streams=streams)


@streamhub_bp.route("/show_stream/<string:system_uuid>/<string:stream_name>")
@is_logged_in
def show_stream(system_uuid, stream_name):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    payload = get_stream_payload(user_uuid, system_uuid, stream_name)
    if not isinstance(payload, dict):
        return payload

    if not app.config["KAFKA_BOOTSTRAP_SERVER"]:
        app.logger.info("The connection to Kafka is disabled. Check the '.env' file!")
        flash("This platform runs in the 'platform-only' mode and doesn't provide the stream functionality.", "info")
        return render_template("/streamhub/show_stream.html", payload=payload)

    # Check if the stream app is running
    # status is one of ["idle", "starting", "running", "stopping", "idle"]
    # real_status is one of ["idle", "starting", "running", "failing", "crashed", "stopping", "idle"]
    status = payload["status"]
    app_stats = None
    app.logger.debug(f"SOLL status for stream app '{fab_streams.build_name(system_uuid, stream_name)}' is '{status}'")
    if status == "init":
        pass  # skip init step as there is nothing to do
    elif status in ["starting", "running"]:
        app_stats = fab_streams.local_stats(system_uuid=system_uuid, stream_name=stream_name)
        if app_stats.get("Running") != "true":  # The stream app has been crashed.
            status = "crashed"
        elif app_stats.get("Restarting") == "true":  # The stream app has been restarted caused by errors
            status = "failing"
        else:  # The stream app is running, because app_stats.get("Restarting") must be "false"
            status = "running"
            payload["status"] = "running"
            set_status_to(system_uuid, stream_name, "running")
    elif status in ["stopping", "idle"]:
        app_stats = fab_streams.local_stats(system_uuid=system_uuid, stream_name=stream_name)
        # if the stream doesn't run
        if app_stats is None or app_stats.get("Running") == "false":  # The stream app was stopped successfully
            status = "idle"
        else:
            status = "stopping"

    payload["status"] = status
    return render_template("/streamhub/show_stream.html", payload=payload, app_stats=app_stats)


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

    # Check if the system exists and has agents
    if len(clients) == 0:
        engine.dispose()
        flash("It seems that this system doesn't exist or you are not permitted see details this stream.", "danger")
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
    if not app.config["KAFKA_BOOTSTRAP_SERVER"]:
        # This platform runs in the 'platform-only' mode and doesn't provide the stream functionality
        flash("The platform runs in the 'platform-only' mode and doesn't provide the stream functionality.", "info")
        return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, stream_name=stream_name))

    # Get current user_uuid
    user_uuid = session["user_uuid"]

    payload = get_stream_payload(user_uuid, system_uuid, stream_name)
    if not isinstance(payload, dict):
        return payload

    if not stream_checks.is_valid(payload):
        flash("The stream is invalid.", "warning")
        return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, stream_name=stream_name))

    # Check if the stream app can be deployed
    if payload["status"] not in ["init", "idle"]:
        app.logger.debug(f"The stream can't be deployed in {payload['status']} mode.")

    # Check if the process is already running
    if fab_streams.local_is_deployed(system_uuid=system_uuid, stream_name=stream_name):
        app.logger.debug(f"The stream '{fab_streams.build_name(system_uuid, stream_name)}' is already deployed. "
                         f"This should not be possible!")

    # The stream can be started
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    transaction = conn.begin()

    # build the stream
    stream = dict()
    stream["SOURCE_SYSTEM"] = payload["source_system"]
    stream["TARGET_SYSTEM"] = payload["target_system"]
    stream["KAFKA_BOOTSTRAP_SERVERS"] = app.config["KAFKA_BOOTSTRAP_SERVER"]
    stream["GOST_SERVER"] = app.config["GOST_SERVER"]
    stream["FILTER_LOGIC"] = payload["filter_logic"]

    app.logger.debug(f"Try to deploy '{fab_streams.build_name(system_uuid, stream_name)}'")
    res = fab_streams.local_deploy(system_uuid=system_uuid, stream_name=stream_name, stream=stream)
    if len(res) != 64:  # res is the UUID of the container
        app.logger.warning(f"'{fab_streams.build_name(system_uuid, stream_name)}' was deployed with response {res}.")
    app.logger.debug(f"Deployed stream '{fab_streams.build_name(system_uuid, stream_name)}'.")

    # Set status in DB
    set_status_to(system_uuid, stream_name, "starting")
    transaction.commit()

    flash(f"{fab_streams.build_name(system_uuid, stream_name)} has been started.", "success")
    return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, stream_name=payload["name"]))


@streamhub_bp.route("/stop_stream/<string:system_uuid>/<string:stream_name>", methods=["GET"])
@is_logged_in
def stop_stream(system_uuid, stream_name):
    if not app.config["KAFKA_BOOTSTRAP_SERVER"]:
        # This platform runs in the 'platform-only' mode and doesn't provide the stream functionality
        flash("The platform runs in the 'platform-only' mode and doesn't provide the stream functionality.", "info")
        return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, stream_name=stream_name))

    # Get current user_uuid
    user_uuid = session["user_uuid"]

    payload = get_stream_payload(user_uuid, system_uuid, stream_name)
    if not isinstance(payload, dict):
        return payload

    # Check if the stream app can be stopped
    if payload["status"] not in ["starting", "running", "failing", "crashed"]:
        app.logger.debug(f"The stream can't be stopped in {payload['status']} mode. This should not happen.")

    # commit change in database
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    transaction = conn.begin()
    try:
        # Stop the stream
        res = fab_streams.local_down(system_uuid=system_uuid, stream_name=stream_name)
        time.sleep(0.1)
        if fab_streams.local_is_deployed(system_uuid=system_uuid, stream_name=stream_name):
            app.logger.debug("{fab_streams.build_name(system_uuid, stream_name)} couldn't be stopped.")

        # Set status
        set_status_to(system_uuid, stream_name, "idle")

        msg = f"{fab_streams.build_name(system_uuid, stream_name)} was stopped successfully."
        app.logger.info(msg)
        flash(msg, "success")
    except Exception as e:
        transaction.rollback()
        app.logger.info("The stream '{}' couldn't be stopped, because {}".format(payload["name"], e))
        flash(f"{fab_streams.build_name(system_uuid, stream_name)} couldn't be stopped.", "success")
    finally:
        return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, stream_name=stream_name))


@streamhub_bp.route("/download_log/<string:system_uuid>/<string:stream_name>")
@is_logged_in
# Don't use cache, as the log could be always the same
@nocache
def download_logs(system_uuid, stream_name):
    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
    container_name = fab_streams.build_name(system_uuid, stream_name)
    app.logger.debug(f"Downloading the log file for '{container_name}'.")

    if not app.config["KAFKA_BOOTSTRAP_SERVER"]:
        # This platform runs in the 'platform-only' mode and doesn't provide the stream functionality
        flash("The platform runs in the 'platform-only' mode and doesn't provide the stream functionality.", "info")
        return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, stream_name=stream_name))

    response = fab_streams.local_logs(system_uuid, stream_name)
    if response is None:
        flash(f"No logfile available for {fab_streams.build_name(system_uuid, stream_name)}.", "info")
        return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, stream_name=stream_name))\

    response = response.replace("\x00", "")
    # res = json.dumps(response.replace("\r\n", "\n").replace("\t", "  ").replace('\"', '"'),
    #                       ensure_ascii=False).encode("utf-8")  # Filter all non-ascii chars
    # printable = set(string.printable)
    # res = "".join(filter(lambda x: x in printable, response))
    # res = response.encode("utf-8", errors="ignore").decode()
    return Response(response, mimetype="test/plain",
                    headers={"Content-disposition": f"attachment; filename={container_name}_{get_datetime()}.log"})


def check_if_proc_runs(system_uuid, stream_name):
    """
    Checks whether the StreamApp runs or not
    :param system_uuid: UUID of the current system
    :param stream_name: name of the current stream
    :return: Boolean value, True if the process still runs.
    """
    app.logger.debug(f"Checks whether the '{fab_streams.build_name(system_uuid, stream_name)}' runs.")
    return fab_streams.local_is_deployed(system_uuid=system_uuid, stream_name=stream_name)


def set_status_to(system_uuid, stream_name, status):
    """
    Updates the SOLL-value of the stream app in the database
    :param system_uuid: UUID of the current system
    :param stream_name: name of the current stream
    :param status: boolean value representing the SOLL status
    :return:
    """
    app.logger.debug(f"Set status to '{status}' for '{fab_streams.build_name(system_uuid, stream_name)}'.")
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """UPDATE streams SET status='{status}' WHERE system_uuid='{system_uuid}' AND name='{stream_name}';""". \
        format(status=status, system_uuid=system_uuid, stream_name=stream_name)
    conn.execute(query)
    engine.dispose()


def get_streamapp_stats(system_uuid, stream_name):
    return fab_streams.local_stats(system_uuid=system_uuid, stream_name=stream_name)


# def load_stream(system_uuid, stream_name):
#     """
#     Loads some information of the stream-app process
#     :param system_uuid: UUID of the current system
#     :param stream_name: name of the current stream
#     :return: a dictionary consisting of pid, cmd line and stdout
#     """
#     try:
#         with open(PROCESS_FILE, "r") as f:
#             content = json.loads(f.read())
#     except FileNotFoundError:
#         with open(PROCESS_FILE, "w") as f:
#             f.write(json.dumps(dict(), indent=2))
#         return dict()
#     try:
#         # pid = content[system_uuid][stream_name]["pid"]
#         # cmd = content[system_uuid][stream_name]["cmd"]
#         # stdout = content[system_uuid][stream_name].get("stdout")
#         return content[system_uuid][stream_name]
#     except KeyError:
#         return dict()
#
#
# def store_stream(system_uuid, stream_name, proc, with_stdout=False):
#     """
#     Stores the current process in the status file and index by system uuid and stream_name
#     :param system_uuid: UUID of the current system
#     :param stream_name: name of the current stream
#     :param proc: process object, only attributes can be stored, not the whole object
#     :param with_stdout: store with stdout of process or not. Output of proc.communicate() can only called once.
#     :return:
#     """
#     try:
#         with open(PROCESS_FILE, "r") as f:
#             content = json.loads(f.read())
#     except FileNotFoundError:
#         content = dict()
#
#     if system_uuid not in content.keys():
#         content[system_uuid] = dict()
#     if stream_name not in content[system_uuid].keys():
#         content[system_uuid][stream_name] = dict()
#     content[system_uuid][stream_name]["pid"] = proc.pid
#     content[system_uuid][stream_name]["cmd"] = proc.args
#     content[system_uuid][stream_name]["datetime"] = \
#         datetime.utcnow().replace(tzinfo=pytz.UTC).replace(microsecond=0).isoformat()
#     if with_stdout:
#         content[system_uuid][stream_name]["stdout"] = proc.communicate(timeout=1)  # timeout returns during execution
#
#     with open(PROCESS_FILE, "w") as f:
#         f.write(json.dumps(content, indent=2))

