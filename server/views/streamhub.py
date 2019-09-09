import os
import json
import time

import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request, send_file
# Must be imported to use the app config
from flask import current_app as app, jsonify
from wtforms import Form, StringField, validators, TextAreaField

from .useful_functions import get_datetime, is_logged_in, valid_level_name, valid_name, valid_system

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
    SELECT sys.uuid AS system_uuid, streams.name AS name, input_system, output_system, creator.email AS contact_mail
    FROM streams
    INNER JOIN users as creator ON creator.uuid=streams.creator_uuid
    INNER JOIN systems AS sys ON streams.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    engine.dispose()
    streams = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched streams: {}".format(streams))

    return render_template("/streamhub/streams.html", streams=streams)
    # return "Not implemented yet.", 501


@streamhub_bp.route("/show_stream/<string:system_uuid>/<string:stream_name>")
@is_logged_in
def show_stream(system_uuid, stream_name):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Fetch all streams for the requested system and user agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """
    SELECT sys.uuid AS system_uuid, com.uuid AS company_uuid, streams.name AS name, input_system, output_system, 
    creator.email AS contact_mail, streams.description, agent.uuid AS agent_uuid, streams.datetime AS datetime
    FROM streams
    INNER JOIN users as creator ON creator.uuid=streams.creator_uuid
    INNER JOIN systems AS sys ON streams.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE sys.uuid='{}' AND streams.name='{}';""".format(system_uuid, stream_name)
    result_proxy = conn.execute(query)
    streams = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched streams: {}".format(streams))

    # Check if the system exists and has agents
    if len(streams) == 0:
        engine.dispose()
        flash("It seems that this stream doesn't exist.", "danger")
        return redirect(url_for("streamhub_bp.show_all_streams"))

    # Check if the current user is agent of the client's system
    if user_uuid not in [c["agent_uuid"] for c in streams]:
        engine.dispose()
        flash("You are not permitted see details this stream.", "danger")
        return redirect(url_for("streamhub_bp.show_all_streams"))

    # if not, agents has at least one item
    payload = streams[0]

    # TODO update filter
    # TODO show docker status of filter
    # filter = {"client_name": client_name,
    #           "system": "{}.{}.{}.{}".format(payload["domain"], payload["enterprise"],
    #                                          payload["workcenter"], payload["station"]),
    #           "gost_servers": "localhost:8084",
    #           "kafka_bootstrap_servers": app.config["KAFKA_BOOTSTRAP_SERVER"]}

    return render_template("/streamhub/show_stream.html", payload=payload)  # , filter=filter)


# Streamhub Form Class
class StreamhubForm(Form):
    name = StringField("Name", [validators.Length(min=2, max=20), valid_name])
    output_system = StringField("Target System", [validators.Length(max=72), valid_system])
    filter_logic = TextAreaField("Filter Logic", [validators.Length(max=4 * 1024)])
    description = TextAreaField("Description", [validators.Length(max=16 * 1024)])


# Add client in system view
@streamhub_bp.route("/add_stream/<string:system_uuid>", methods=["GET", "POST"])
@is_logged_in
def add_stream_for_system(system_uuid):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # The basic client form is used
    form = StreamhubForm(request.form)

    # Fetch all streams for the requested system and user agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """
    SELECT sys.uuid AS system_uuid, com.uuid AS company_uuid, streams.name AS name, input_system, output_system, 
    creator.email AS contact_mail, streams.description, agent.uuid AS agent_uuid, streams.datetime AS datetime
    FROM streams
    INNER JOIN users as creator ON creator.uuid=streams.creator_uuid
    INNER JOIN systems AS sys ON streams.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE sys.uuid='{}' AND agent.uuid='{}';""".format(system_uuid, user_uuid)
    result_proxy = conn.execute(query)
    streams = [dict(c.items()) for c in result_proxy.fetchall()]
    print("Fetched streams: {}".format(streams))

    # Check if the system exists and has agents
    if len(streams) == 0:
        engine.dispose()
        flash("It seems that this stream doesn't exist.", "danger")
        return redirect(url_for("streamhub.show_all_streams"))

    # Check if the current user is agent of the client's system
    if user_uuid not in [c["agent_uuid"] for c in streams]:
        engine.dispose()
        flash("You are not permitted see details this stream.", "danger")
        return redirect(url_for("streamhub.show_all_streams"))

    # if not, streams has at least one item
    payload = streams[0]

    # Create a new stream using the form's input
    if request.method == "POST" and form.validate():
        # Create stream and check if the combination of the system_uuid and name exists
        query = """SELECT system_uuid, name
        FROM systems
        INNER JOIN streams ON streams.system_uuid=systems.uuid
        WHERE system_uuid='{}' AND name='{}';""".format(system_uuid, form.name.data)
        result_proxy = conn.execute(query)

        system_name = payload["input_system"]

        if len(result_proxy.fetchall()) == 0:
            query = db.insert(app.config["tables"]["streams"])
            values_list = [{'name': form.name.data,
                            'system_uuid': system_uuid,
                            'input_system': system_name,
                            'output_system': form.output_system.data,
                            'filter': form.filter_logic.data,
                            'creator_uuid': user_uuid,
                            'datetime': get_datetime(),
                            'description': form.description.data}]
            conn.execute(query, values_list)
            engine.dispose()

            msg = "The stream '{}' was added to system '{}'.".format(form.name.data, system_name)
            app.logger.info(msg)
            flash(msg, "success")
            return redirect(url_for("streamhub.show_stream", system_uuid=system_uuid, stream_name=form.name.data))
        else:
            engine.dispose()
            msg = "The stream with name '{}' was already created for system '{}'.".format(form.name.data, system_name)
            app.logger.info(msg)
            flash(msg, "danger")
            return redirect(url_for("streamhub.add_stream_for_system", system_uuid=system_uuid))

    return render_template("/streamhub/add_stream.html", form=form, payload=payload)


# Delete stream
@streamhub_bp.route("/delete_stream/<string:system_uuid>/<stream_name>", methods=["GET"])
@is_logged_in
def delete_stream(system_uuid, stream_name):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Fetch streams of the system, for with the user is agent
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT sys.uuid AS system_uuid, streams.name AS name, input_system, output_system, 
    creator.email AS contact_mail, agent.uuid AS agent_uuid
    FROM streams
    INNER JOIN users as creator ON creator.uuid=streams.creator_uuid
    INNER JOIN systems AS sys ON streams.system_uuid=sys.uuid
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
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
        return redirect(url_for("streamhub_bp.show_all_streams"))

    # Check if the current user is agent of the system
    if user_uuid not in [c["agent_uuid"] for c in streams]:
        engine.dispose()
        flash("You are not permitted to delete streams of this system.", "danger")
        return redirect(url_for("streamhub_bp.show_stream", system_uuid=system_uuid, client_name=stream_name))

    # Delete the specified stream
    query = """DELETE FROM streams
        WHERE system_uuid='{}' AND name='{}';""".format(system_uuid, stream_name)
    conn.execute(query)
    engine.dispose()

    msg = "The stream '{}' of system '{}' was deleted.".format(stream_name, streams[0]["input_system"])
    app.logger.info(msg)
    flash(msg, "success")

    # Redirect to /show_system/system_uuid
    return redirect(url_for("system.show_system", system_uuid=system_uuid))
