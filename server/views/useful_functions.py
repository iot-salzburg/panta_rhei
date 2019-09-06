# A collection of useful functions for this application


def get_uid():
    import uuid
    return str(uuid.uuid4()).split("-")[-1]


def get_datetime():
    import pytz
    from dateutil import tz
    from datetime import datetime
    dt = datetime.utcnow().replace(microsecond=0).replace(tzinfo=pytz.UTC).astimezone(tz.gettz('Europe/Vienna'))
    return dt.isoformat()


# Check if user is logged in
def is_logged_in(f):
    from flask import flash, redirect, url_for, session
    from functools import wraps
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("Please login.", "danger")
            return redirect(url_for("auth.login"))
    return wrap


# Validator for company, system and client names
# only 0-9, a-z, A-Z and "-" is allowed.
def valid_level_name(form, field):
    import re
    from wtforms import ValidationError
    if " " in field.data:
        raise ValidationError("Whitespaces are not allowed in the name.")
    if not re.match("^[a-zA-Z0-9-]*$", field.data):
        raise ValidationError("Only alphanumeric characters and '-' are allowed.")


# DO create is_admin and is_agent
