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

from wtforms import Form, StringField, TextField, TextAreaField, PasswordField, validators
from flask import current_app as app

from .useful_functions import get_datetime, get_uid, is_logged_in

# print("current app: {}".format(app.config))
company = Blueprint('company', __name__)  # url_prefix='/comp')


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


@company.route('/show_company/<string:company_uuid>')
@is_logged_in
def show_company(company_uuid):
    # Get Form Fields
    user_uuid = session['user_uuid']

    # Create cursor
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    conn = engine.connect()

    query = """SELECT company_uuid, domain, enterprise, admin.uuid AS admin_uuid, admin.first_name, admin.sur_name, admin.email 
    FROM companies AS com 
    INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
    INNER JOIN users as admin ON admin.uuid=aof.user_uuid 
    INNER JOIN users as creator ON creator.uuid=aof.creator_uuid 
    WHERE company_uuid='{}';""".format(company_uuid)
    ResultProxy = conn.execute(query)
    admins = [dict(c.items()) for c in ResultProxy.fetchall()]
    print("Fetched admins: {}".format(admins))

    if user_uuid not in [c["admin_uuid"] for c in admins]:
        flash("You are not permitted to add an admin for this company", "danger")
        return redirect(url_for('company.show_all_companies'))

    # if not, admins has at least one item
    payload = admins[0]
    return render_template("/companies/show_company.html", admins=admins, payload=payload)


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
    permitted_companies = [dict(c.items()) for c in ResultProxy.fetchall() if c["company_uuid"] == uuid]

    if permitted_companies == list():
        flash("You are not permitted to delete this company", "danger")
        return redirect(url_for('company.show_all_companies'))
    else:
        selected_company = permitted_companies[0]
        # Delete new is_admin_of instance
        query = """DELETE FROM is_admin_of
            WHERE company_uuid='{}';""".format(uuid)
        ResultProxy = conn.execute(query)

        # Delete company
        query = """DELETE FROM companies
            WHERE uuid='{}';""".format(uuid)
        ResultProxy = conn.execute(query)

        flash("The company {} was deleted.".format(selected_company["enterprise"]), "success")
        return redirect(url_for('company.show_all_companies'))


# Add admin for company
class AdminForm(Form):
    email = StringField('Email', [validators.Email(message="The given email seems to be wrong")])


@company.route("/add_admin_company/<company_uuid>", methods=["GET", "POST"])
@is_logged_in
def add_admin_company(company_uuid):
    form = AdminForm(request.form)
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
            WHERE admin.uuid='{}' 
            AND com.uuid='{}';""".format(user_uuid, company_uuid)
    ResultProxy = conn.execute(query)
    permitted_companies = [dict(c.items()) for c in ResultProxy.fetchall() if c["company_uuid"] == company_uuid]

    if permitted_companies == list():
        flash("You are not permitted to add an admin for this company", "danger")
        return redirect(url_for('company.show_all_companies'))

    else:
        selected_company = permitted_companies[0]

        domain = selected_company["domain"]
        enterprise = selected_company["enterprise"]

        if request.method == 'POST' and form.validate():
            email = form.email.data

            # Create cursor
            engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
            conn = engine.connect()

            # Check if the user is registered
            query = """SELECT * FROM users WHERE email='{}';""".format(email)
            ResultProxy = conn.execute(query)
            found_users = [dict(c.items()) for c in ResultProxy.fetchall()]

            if found_users == list():
                flash("No user was found with this email address.", "danger")
                return render_template('/companies/add_admin_company.html', form=form, domain=domain,
                                       enterprise=enterprise)
            user = found_users[0]
            # Create new is_admin_of instance
            query = db.insert(app.config["tables"]["is_admin_of"])
            values_list = [{'user_uuid': user["uuid"],
                            'company_uuid': selected_company["company_uuid"],
                            'creator_uuid': user_uuid,
                            'datetime': get_datetime()}]

            ResultProxy = conn.execute(query, values_list)
            flash("The user {} was added to {}.{} as an admin.".format(form.email.data, domain, enterprise), "success")
            return redirect(url_for('company.show_company', company_uuid=selected_company["company_uuid"]))

        return render_template('/companies/add_admin_company.html', form=form, domain=domain, enterprise=enterprise)

# Delete admin for company
@company.route("/delete_admin_company/<string:company_uuid>/<string:admin_uuid>", methods=["GET"])
@is_logged_in
def delete_admin_company(company_uuid, admin_uuid):
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
        WHERE admin.uuid='{}'
        AND aof.company_uuid='{}';""".format(user_uuid, company_uuid)
    ResultProxy = conn.execute(query)
    permitted_companies = [dict(c.items()) for c in ResultProxy.fetchall()]

    if permitted_companies == list():
        flash("You are not permitted to delete this company", "danger")
        return redirect(url_for('company.show_all_companies'))

    elif user_uuid == admin_uuid and len(permitted_companies) == 1:
        flash("You are not permitted to remove yourself, if you are the last admin", "danger")
        return redirect(url_for('company.show_company', company_uuid=company_uuid))

    else:
        # get info for the deleted user
        query = """SELECT company_uuid, domain, enterprise, admin.email AS admin_email, admin.uuid AS admin_uuid
                FROM companies AS com 
                INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
                INNER JOIN users as admin ON admin.uuid=aof.user_uuid
                WHERE admin.uuid='{}'
                AND aof.company_uuid='{}';""".format(admin_uuid, company_uuid)
        ResultProxy = conn.execute(query)
        del_users = [dict(c.items()) for c in ResultProxy.fetchall()]
        if del_users == list():
            flash("nothing to delete.", "danger")
            return redirect(url_for('company.show_all_companies'))

        else:
            del_user = del_users[0]
            # Delete new is_admin_of instance
            query = """DELETE FROM is_admin_of
                WHERE user_uuid='{}'
                AND company_uuid='{}';""".format(admin_uuid, company_uuid)
            ResultProxy = conn.execute(query)
            # print("DELETING: {}".format(query))

            flash("User with email {} was removed as admin from company {}.{}.".format(
                del_user["admin_email"], del_user["domain"], del_user["enterprise"]), "success")
            return redirect(url_for('company.show_company', company_uuid=del_user["company_uuid"]))

