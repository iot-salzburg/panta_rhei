import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request
# Must be imported to use the app config
from flask import current_app as app
from sqlalchemy import exc as sqlalchemy_exc
from wtforms import Form, StringField, validators, TextField, TextAreaField

from .useful_functions import get_datetime, get_uid, is_logged_in

company = Blueprint("company", __name__)  # url_prefix="/comp")


@company.route("/companies")
@is_logged_in
def show_all_companies():
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Fetch companies, for which the current user is admin of
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """SELECT company_uuid, domain, enterprise, creator.email AS contact_mail
    FROM companies AS com 
    INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
    INNER JOIN users as admin ON admin.uuid=aof.user_uuid
    INNER JOIN users as creator ON creator.uuid=aof.creator_uuid
    WHERE admin.uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    engine.dispose()
    companies = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched companies: {}".format(companies))
    return render_template("/companies/companies.html", companies=companies)


@company.route("/show_company/<string:company_uuid>")
@is_logged_in
def show_company(company_uuid):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Set url (is used in system.delete_system)
    session["url"] = "/show_company/{}".format(company_uuid)

    # Fetch all admins for the requested company
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()
    query = """
    SELECT company_uuid, domain, enterprise, description, admin.uuid AS admin_uuid, admin.first_name, admin.sur_name, 
    admin.email, creator.email AS creator_mail, com.datetime AS com_datetime
    FROM companies AS com 
    INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
    INNER JOIN users as admin ON admin.uuid=aof.user_uuid 
    INNER JOIN users as creator ON creator.uuid=aof.creator_uuid 
    WHERE company_uuid='{}';""".format(company_uuid)
    result_proxy = conn.execute(query)
    admins = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched admins: {}".format(admins))

    # Check if the company exists and has admins
    if len(admins) == 0:
        engine.dispose()
        flash("It seems that this company doesn't exist.", "danger")
        return redirect(url_for("company.show_all_companies"))

    # Check if the current user is admin of the company
    if user_uuid not in [c["admin_uuid"] for c in admins]:
        engine.dispose()
        flash("You are not permitted to see details of this company.", "danger")
        return redirect(url_for("company.show_all_companies"))

    # if not, admins has at least one item
    payload = admins[0]

    # Fetch systems of this company
    query = """SELECT sys.uuid AS system_uuid, workcenter, station
    FROM systems AS sys WHERE sys.company_uuid='{}';""".format(company_uuid)
    result_proxy = conn.execute(query)
    engine.dispose()
    systems = [dict(c.items()) for c in result_proxy.fetchall()]

    return render_template("/companies/show_company.html", admins=admins, systems=systems, payload=payload)


# Company Form Class
class CompanyForm(Form):
    domain = StringField("Domain", [validators.Length(min=1, max=5)])
    enterprise = StringField("Enterprise", [validators.Length(min=4, max=15)])
    description = TextAreaField("Description", [validators.Length(max=16*1024)])

# Add company
@company.route("/add_company", methods=["GET", "POST"])
@is_logged_in
def add_company():
    # Get current user_uuid
    user_uuid = session["user_uuid"]
    # The basic company form is used
    form = CompanyForm(request.form)
    form.enterprise.label = "Enterprise short-name"

    if request.method == "POST" and form.validate():
        # Create a new company and admin-relation using the form"s input
        engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
        conn = engine.connect()

        # Create company and check if either the company_uuid or the company exists
        company_uuids = ["init"]
        company_uuid = get_uid()
        while company_uuids != list():
            company_uuid = get_uid()
            query = """SELECT uuid FROM companies WHERE uuid='{}';""".format(company_uuid)
            result_proxy = conn.execute(query)
            company_uuids = result_proxy.fetchall()

        query = """SELECT domain, enterprise FROM companies 
                    WHERE domain='{}' AND enterprise='{}';""".format(form.domain.data, form.enterprise.data)
        result_proxy = conn.execute(query)
        if len(result_proxy.fetchall()) == 0:
            query = db.insert(app.config["tables"]["companies"])
            values_list = [{"uuid": company_uuid,
                            "domain": form.domain.data,
                            "enterprise": form.enterprise.data,
                            "description": form.description.data}]
            conn.execute(query, values_list)
        else:
            engine.dispose()
            flash("The company {}.{} is already created.".format(form.domain.data, form.enterprise.data), "danger")
            return redirect(url_for("company.show_all_companies"))

        # Create new is_admin_of instance
        query = db.insert(app.config["tables"]["is_admin_of"])
        values_list = [{"user_uuid": user_uuid,
                        "company_uuid": company_uuid,
                        "creator_uuid": user_uuid,
                        "datetime": get_datetime()}]
        try:
            conn.execute(query, values_list)
            engine.dispose()
            flash("The company {} was created.".format(form.enterprise.data), "success")
            return redirect(url_for("company.show_all_companies"))

        except sqlalchemy_exc.IntegrityError as e:
            engine.dispose()
            print("An Integrity Error occured: {}".format(e))
            flash("An unexpected error occured.", "danger")
            return render_template(url_for("auth.login"))

    return render_template("/companies/add_company.html", form=form)


# Delete company
@company.route("/delete_company/<company_uuid>", methods=["GET"])
@is_logged_in
def delete_company(company_uuid):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Create cursor
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()

    # Check if you are admin of this company
    query = """SELECT company_uuid, domain, enterprise, user_uuid
        FROM companies AS com 
        INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
        WHERE aof.user_uuid='{}'
        AND aof.company_uuid='{}';""".format(user_uuid, company_uuid)
    result_proxy = conn.execute(query)
    permitted_companies = [dict(c.items()) for c in result_proxy.fetchall()]

    if permitted_companies == list():
        engine.dispose()
        flash("You are not permitted to delete this company.", "danger")
        return redirect(url_for("company.show_all_companies"))

    # Check if you are the last admin of the company
    query = """SELECT aof.company_uuid, domain, enterprise, user_uuid
        FROM companies AS com INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
        WHERE aof.company_uuid='{}';""".format(company_uuid)
    result_proxy_admin = conn.execute(query)

    # Check if there is no system left
    query = """SELECT sys.company_uuid
        FROM companies AS com 
        INNER JOIN systems AS sys ON com.uuid=sys.company_uuid 
        WHERE sys.company_uuid='{}';""".format(company_uuid)
    result_proxy_system = conn.execute(query)

    if len(result_proxy_system.fetchall()) >= 1:
        flash("You are not permitted to delete a company which has systems.", "danger")
        engine.dispose()
        return redirect(url_for("company.show_company", company_uuid=company_uuid))
    if len(result_proxy_admin.fetchall()) >= 2:
        flash("You are not permitted to delete a company which has other admins.", "danger")
        engine.dispose()
        return redirect(url_for("company.show_all_companies"))

    # Now the company can be deleted
    selected_company = permitted_companies[0]  # This list has only one element

    # Delete new is_admin_of instance
    query = """DELETE FROM is_admin_of
        WHERE company_uuid='{}';""".format(company_uuid)
    conn.execute(query)

    # Delete company
    query = """DELETE FROM companies
        WHERE uuid='{}';""".format(company_uuid)
    conn.execute(query)
    engine.dispose()

    flash("The company {} was deleted.".format(selected_company["enterprise"]), "success")
    return redirect(url_for("company.show_all_companies"))


# Admin Management Form Class
class AdminForm(Form):
    email = StringField("Email", [validators.Email(message="The given email seems to be wrong")])


@company.route("/add_admin_company/<string:company_uuid>", methods=["GET", "POST"])
@is_logged_in
def add_admin_company(company_uuid):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    form = AdminForm(request.form)

    # Create cursor
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()

    # Check if you are admin of this company
    query = """SELECT company_uuid, domain, enterprise, creator.email AS contact_mail
            FROM companies AS com 
            INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
            INNER JOIN users as admin ON admin.uuid=aof.user_uuid
            INNER JOIN users as creator ON creator.uuid=aof.creator_uuid
            WHERE admin.uuid='{}' 
            AND com.uuid='{}';""".format(user_uuid, company_uuid)
    result_proxy = conn.execute(query)
    engine.dispose()
    permitted_companies = [dict(c.items()) for c in result_proxy.fetchall() if c["company_uuid"] == company_uuid]

    if permitted_companies == list():
        flash("You are not permitted to add an admin for this company.", "danger")
        return redirect(url_for("company.show_all_companies"))

    selected_company = permitted_companies[0]

    domain = selected_company["domain"]
    enterprise = selected_company["enterprise"]

    if request.method == "POST" and form.validate():
        email = form.email.data

        # Create cursor
        engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
        conn = engine.connect()

        # Check if the user is registered
        query = """SELECT * FROM users WHERE email='{}';""".format(email)
        result_proxy = conn.execute(query)
        found_users = [dict(c.items()) for c in result_proxy.fetchall()]

        if found_users == list():
            flash("No user was found with this email address.", "danger")
            return render_template("/companies/add_admin_company.html", form=form, domain=domain,
                                   enterprise=enterprise)

        user = found_users[0]
        # Check if the user is already admin of this company
        query = """SELECT company_uuid, user_uuid
        FROM companies AS com 
        INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
        WHERE aof.user_uuid='{}' AND com.uuid='{}';""".format(user["uuid"], company_uuid)
        result_proxy = conn.execute(query)
        if result_proxy.fetchall() != list():
            engine.dispose()
            flash("This user is already admin of this company.", "danger")
            return render_template("/companies/add_admin_company.html", form=form, domain=domain,
                                   enterprise=enterprise)

        # Create new is_admin_of instance
        query = db.insert(app.config["tables"]["is_admin_of"])
        values_list = [{"user_uuid": user["uuid"],
                        "company_uuid": selected_company["company_uuid"],
                        "creator_uuid": user_uuid,
                        "datetime": get_datetime()}]

        conn.execute(query, values_list)
        engine.dispose()
        flash("The user {} was added to {}.{} as an admin.".format(form.email.data, domain, enterprise), "success")
        return redirect(url_for("company.show_company", company_uuid=selected_company["company_uuid"]))

    return render_template("/companies/add_admin_company.html", form=form, domain=domain, enterprise=enterprise)

# Delete admin for company
@company.route("/delete_admin_company/<string:company_uuid>/<string:admin_uuid>", methods=["GET"])
@is_logged_in
def delete_admin_company(company_uuid, admin_uuid):
    # Get current user_uuid
    user_uuid = session["user_uuid"]

    # Create cursor
    engine = db.create_engine(app.config["SQLALCHEMY_DATABASE_URI"])
    conn = engine.connect()

    # Check if you are admin of this company
    query = """SELECT company_uuid, domain, enterprise, creator.email AS contact_mail
        FROM companies AS com 
        INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
        INNER JOIN users as admin ON admin.uuid=aof.user_uuid
        INNER JOIN users as creator ON creator.uuid=aof.creator_uuid
        WHERE admin.uuid='{}'
        AND aof.company_uuid='{}';""".format(user_uuid, company_uuid)
    result_proxy = conn.execute(query)
    permitted_companies = [dict(c.items()) for c in result_proxy.fetchall()]

    if permitted_companies == list():
        engine.dispose()
        flash("You are not permitted to delete this company.", "danger")
        return redirect(url_for("company.show_all_companies"))

    elif user_uuid == admin_uuid:
        engine.dispose()
        flash("You are not permitted to remove yourself.", "danger")
        return redirect(url_for("company.show_company", company_uuid=company_uuid))

    else:
        # get info for the deleted user
        query = """SELECT company_uuid, domain, enterprise, admin.email AS admin_email, admin.uuid AS admin_uuid
                FROM companies AS com 
                INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid 
                INNER JOIN users as admin ON admin.uuid=aof.user_uuid
                WHERE admin.uuid='{}'
                AND aof.company_uuid='{}';""".format(admin_uuid, company_uuid)
        result_proxy = conn.execute(query)
        del_users = [dict(c.items()) for c in result_proxy.fetchall()]
        if del_users == list():
            engine.dispose()
            flash("nothing to delete.", "danger")
            return redirect(url_for("company.show_all_companies"))

        else:
            del_user = del_users[0]
            # Delete new is_admin_of instance
            query = """DELETE FROM is_admin_of
                WHERE user_uuid='{}'
                AND company_uuid='{}';""".format(admin_uuid, company_uuid)
            conn.execute(query)
            # print("DELETING: {}".format(query))

            engine.dispose()
            flash("User with email {} was removed as admin from company {}.{}.".format(
                del_user["admin_email"], del_user["domain"], del_user["enterprise"]), "success")
            return redirect(url_for("company.show_company", company_uuid=del_user["company_uuid"]))
