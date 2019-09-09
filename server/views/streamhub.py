import os
import json
import time

import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request, send_file
# Must be imported to use the app config
from flask import current_app as app, jsonify
from wtforms import Form, StringField, validators, TextAreaField

from .useful_functions import get_datetime, is_logged_in, valid_level_name, valid_name

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


@streamhub_bp.route("/show_stream/<string:system_uuid>/<string:client_name>")
@is_logged_in
def show_stream(system_uuid, client_name):
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
    WHERE sys.uuid='{}' AND streams.name='{}';""".format(system_uuid, client_name)
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

    return render_template("/streamhub/show_stream.html", payload=payload) #, filter=filter)
