import os
import uuid
import json
import logging
import psycopg2
import sqlalchemy as db
from sqlalchemy import exc as sqlalchemy_exc

from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask import Blueprint, Flask, render_template, flash , redirect, url_for, session, request

# from .data import Articles
from functools import wraps
from passlib.hash import sha256_crypt
import wtforms
from wtforms import Form, StringField, TextField, TextAreaField, PasswordField, validators
from flask import current_app as app

# print("current app: {}".format(app.config))
company = Blueprint('company', __name__) #, url_prefix='/comp')

def get_uid():
    return str(uuid.uuid4()).split("-")[-1]


def get_datetime():
    import pytz
    from dateutil import tz
    from datetime import datetime
    dt = datetime.utcnow().replace(microsecond=0).replace(tzinfo=pytz.UTC).astimezone(tz.gettz('Europe/Vienna'))
    return dt.isoformat()


# Check if user is logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash("Unauthorized. Please login", "danger")
            return redirect(url_for("login"))
    return wrap


# Article Form Class for the Company
class CompanyForm(Form):
    domain = StringField('Domain', [validators.Length(min=1, max=5)])
    enterprise = StringField('Enterprise', [validators.Length(min=4, max=15)])


@company.route('/companies')
@is_logged_in
def show_all_companies():
    # Get Form Fields
    user_uuid = session['user_uuid']
    # user_uuid = "b0b793502753"
    # print("Current user uuid: {}".format(user_uuid))
    # Create cursor
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    conn = engine.connect()

    query = """SELECT company_uuid, domain, enterprise, creator.email AS contact_mail
    FROM companies AS com 
    INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
    INNER JOIN users as admin ON admin.uuid=aof.user_uuid
    INNER JOIN users as creator ON creator.uuid=aof.creator_uuid
    WHERE admin.uuid='{}';""".format(user_uuid)
    ResultProxy = conn.execute(query)
    companies = [dict(c.items()) for c in ResultProxy.fetchall()]
    # print("Fetched companies: {}".format(companies))

    return render_template("/companies/companies.html", companies=companies)

# Add company
@company.route("/add_company", methods=["GET", "POST"])
@is_logged_in
def add_company():
    form = CompanyForm(request.form)
    form.enterprise.label = "Enterprise shortname"
    if request.method == 'POST' and form.validate():

        # Create cursor
        engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
        conn = engine.connect()

        # Create company
        company_uuid = get_uid()
        query = db.insert(app.config["tables"]["companies"])
        values_list = [{'uuid': company_uuid,
                        'domain': form.domain.data,
                        'enterprise': form.enterprise.data}]
        ResultProxy = conn.execute(query, values_list)

        # Create new is_admin_of instance
        query = db.insert(app.config["tables"]["is_admin_of"])
        values_list = [{'user_uuid': session['user_uuid'],
                        'company_uuid': company_uuid,
                        'creator_uuid': session['user_uuid'],
                        'datetime': get_datetime()}]
        try:
            ResultProxy = conn.execute(query, values_list)
            flash("The company {} was created.".format(form.enterprise.data), "success")
            return redirect(url_for('company.show_all_companies'))

        except sqlalchemy_exc.IntegrityError:
            flash("You are already registered with this email. Please log in", "danger")
            return render_template('login.html')

    return render_template('/companies/add_company.html', form=form)


# Delete company
@company.route("/delete_company/<string:uuid>", methods=["GET"])
@is_logged_in
def delete_company(uuid):
    user_uuid = session['user_uuid']

    # Create cursor
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    conn = engine.connect()

    # Check if you are admin of this company
    query = """SELECT company_uuid, domain, enterprise, creator.email AS contact_mail
        FROM companies AS com 
        INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
        INNER JOIN users as admin ON admin.uuid=aof.user_uuid
        INNER JOIN users as creator ON creator.uuid=aof.creator_uuid
        WHERE admin.uuid='{}';""".format(user_uuid)
    ResultProxy = conn.execute(query)
    company = [dict(c.items()) for c in ResultProxy.fetchall() if c["company_uuid"] == uuid][0]

    if uuid in company["company_uuid"]:
        # Delete new is_admin_of instance
        query = """DELETE FROM is_admin_of
            WHERE company_uuid='{}';""".format(uuid)
        ResultProxy = conn.execute(query)

        # Delete company
        query = """DELETE FROM companies
            WHERE uuid='{}';""".format(uuid)
        ResultProxy = conn.execute(query)

        flash("The company {} was deleted.".format(company["enterprise"]), "success")
        return redirect(url_for('company.show_all_companies'))

    else:
        flash("You are not permitted to delete this company", "danger")
        return redirect(url_for('company.show_all_companies'))
