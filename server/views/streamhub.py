from flask import Blueprint, render_template, flash, redirect, url_for, session, request

from .useful_functions import get_datetime, get_uid, is_logged_in

streamhub_bp = Blueprint("streamhub", __name__)  # url_prefix="/comp")


@streamhub_bp.route("/streamhub")
@is_logged_in
def show_all_streams():

    return render_template("/streamhub/streamhub.html")
