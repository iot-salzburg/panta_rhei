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


# Validator for company and system names
# only 0-9, a-z, A-Z and "-" are allowed.
def valid_level_name(form, field):
    import re
    from wtforms import ValidationError
    if " " in field.data:
        raise ValidationError("Whitespaces are not allowed in the name.")
    if not re.match("^[a-zA-Z0-9-]*$", field.data):
        raise ValidationError("Only alphanumeric characters and '-' are allowed.")


# Validator for client names
# only 0-9, a-z, A-Z, "-" and "_" are allowed.
def valid_name(form, field):
    import re
    from wtforms import ValidationError
    if " " in field.data:
        raise ValidationError("Whitespaces are not allowed in the name.")
    if not re.match("^[a-zA-Z0-9-_]*$", field.data):
        raise ValidationError("Only alphanumeric characters, '-' and '_' are allowed.")


# Validator for url
def valid_url(form, field):
    import re
    from wtforms import ValidationError
    regex = re.compile(
        r'^(?:http|ftp)s?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    if " " in field.data:
        raise ValidationError("Whitespaces are not allowed in the url.")
    if not re.match(regex, field.data):
        raise ValidationError("The URL seems to be malformed.")


# Validator for systems
def valid_system(form, field):
    import re
    from wtforms import ValidationError
    if " " in field.data:
        raise ValidationError("Whitespaces are not allowed in the url.")
    if not re.match("^[a-zA-Z0-9-.]*$", field.data):
        raise ValidationError("Only alphanumeric characters, '-' and '.' are allowed.")
    if field.data.count(".") != 3:
        raise ValidationError("The System doesn't match the pattern: [domain].[enterprice].[work-center].[station]")

# DO create is_admin and is_agent
