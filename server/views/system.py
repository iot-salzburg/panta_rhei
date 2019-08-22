import sqlalchemy as db
from flask import Blueprint, render_template, flash, redirect, url_for, session, request
# Must be imported to use the app config
from flask import current_app as app
from sqlalchemy import exc as sqlalchemy_exc
from wtforms import Form, StringField, validators

from .useful_functions import get_datetime, get_uid, is_logged_in

system = Blueprint('system', __name__)  # url_prefix='/comp')


@system.route('/systems')
@is_logged_in
def show_all_systems():
    # Get current user_uuid
    user_uuid = session['user_uuid']

    # Fetch systems, for which the current user is agent of
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    conn = engine.connect()
    query = """SELECT sys.uuid AS system_uuid, domain, enterprise, workcenter, station, agent.email AS contact_mail
    FROM systems AS sys
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    WHERE agent.uuid='{}';""".format(user_uuid)
    result_proxy = conn.execute(query)
    systems = [dict(c.items()) for c in result_proxy.fetchall()]
    # print("Fetched companies: {}".format(companies))

    return render_template("/systems/systems.html", systems=systems)


@system.route('/show_system/<string:system_uuid>')
@is_logged_in
def show_system(system_uuid):
    # Get current user_uuid
    user_uuid = session['user_uuid']

    # Fetch all agents for the requested system
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    conn = engine.connect()
    query = """
    SELECT sys.uuid AS system_uuid, domain, enterprise, workcenter, station, 
    agent.uuid AS agent_uuid, agent.first_name, agent.sur_name, agent.email
    FROM systems AS sys
    INNER JOIN companies AS com ON sys.company_uuid=com.uuid
    INNER JOIN is_agent_of AS agf ON sys.uuid=agf.system_uuid 
    INNER JOIN users as agent ON agent.uuid=agf.user_uuid
    INNER JOIN users as creator ON creator.uuid=agf.creator_uuid 
    WHERE sys.uuid='{}';""".format(system_uuid)
    result_proxy = conn.execute(query)
    agents = [dict(c.items()) for c in result_proxy.fetchall()]
    print("Fetched agents: {}".format(agents))

    # Check if the system exists and has agents
    if len(agents) == 0:
        flash("It seems that this system doesn't exist.", "danger")
        return redirect(url_for('system.show_all_systems'))

    # Check if the current user is admin of the system
    if user_uuid not in [c["agent_uuid"] for c in agents]:
        flash("You are not permitted see details this system.", "danger")
        return redirect(url_for('system.show_all_systems'))

    # if not, agents has at least one item
    payload = agents[0]
    return render_template("/systems/show_system.html", agents=agents, payload=payload)


# System Form Class
class SystemForm(Form):
    workcenter = StringField('Workcenter', [validators.Length(min=4, max=30)])
    station = StringField('Station', [validators.Length(min=4, max=20)])

# Add system in system view, redirect to companies
@system.route("/add_system")
@is_logged_in
def add_system():
    # redirect to companies
    flash("Specify the company to which a system should be added.", "info")
    return redirect(url_for('company.show_all_companies'))

# Add system in company view
@system.route("/add_system/<string:company_uuid>", methods=["GET", "POST"])
@is_logged_in
def add_system_for_company():
    # Get current user_uuid
    user_uuid = session['user_uuid']
    # The basic company form is used
    form = CompanyForm(request.form)
    form.enterprise.label = "Enterprise short-name"

    if request.method == 'POST' and form.validate():
        # Create a new company and admin-relation using the form's input
        engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
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
            values_list = [{'uuid': company_uuid,
                            'domain': form.domain.data,
                            'enterprise': form.enterprise.data}]
            conn.execute(query, values_list)
        else:
            flash("The company {}.{} is already created.".format(form.domain.data, form.enterprise.data), "danger")
            return redirect(url_for('company.show_all_companies'))

        # Create new is_admin_of instance
        query = db.insert(app.config["tables"]["is_admin_of"])
        values_list = [{'user_uuid': user_uuid,
                        'company_uuid': company_uuid,
                        'creator_uuid': user_uuid,
                        'datetime': get_datetime()}]
        try:
            conn.execute(query, values_list)
            flash("The company {} was created.".format(form.enterprise.data), "success")
            return redirect(url_for('company.show_all_companies'))

        except sqlalchemy_exc.IntegrityError as e:
            print("An Integrity Error occured: {}".format(e))
            flash("An unexpected error occured.", "danger")
            return render_template('login.html')

    return render_template('/companies/add_company.html', form=form)


# Delete company
@system.route("/delete_company/<string:uuid>", methods=["GET"])
@is_logged_in
def delete_company(uuid):
    # Get current user_uuid
    user_uuid = session['user_uuid']

    # Create cursor
    engine = db.create_engine(app.config['SQLALCHEMY_DATABASE_URI'])
    conn = engine.connect()

    # Check if you are admin of this company
    query = """SELECT company_uuid, domain, enterprise, user_uuid
        FROM companies AS com
        INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid
        WHERE aof.user_uuid='{}'
        AND aof.company_uuid='{}';""".format(user_uuid, uuid)
    result_proxy = conn.execute(query)
    permitted_companies = [dict(c.items()) for c in result_proxy.fetchall()]

    if permitted_companies == list():
        flash("You are not permitted to delete this company.", "danger")
        return redirect(url_for('company.show_all_companies'))

    # Check if you are the last admin of the company
    query = """SELECT company_uuid, domain, enterprise, user_uuid
        FROM companies AS com
        INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid
        AND aof.company_uuid='{}';""".format(uuid)
    result_proxy = conn.execute(query)
    # admins_of_company = [dict(c.items()) for c in result_proxy.fetchall()]

    if len(result_proxy.fetchall()) >= 2:
        flash("You are not permitted to delete a company which has multiple admins.", "danger")
        return redirect(url_for('company.show_all_companies'))

    # Now the company can be deleted
    selected_company = permitted_companies[0]  # This list has only one element

    # Delete new is_admin_of instance
    query = """DELETE FROM is_admin_of
        WHERE company_uuid='{}';""".format(uuid)
    conn.execute(query)

    # Delete company
    query = """DELETE FROM companies
        WHERE uuid='{}';""".format(uuid)
    conn.execute(query)

    flash("The company {} was deleted.".format(selected_company["enterprise"]), "success")
    return redirect(url_for('company.show_all_companies'))


# Agent Management Form Class
class AgentForm(Form):
    email = StringField('Email', [validators.Email(message="The given email seems to be wrong")])


@system.route("/add_admin_company/<company_uuid>", methods=["GET", "POST"])
@is_logged_in
def add_admin_company(company_uuid):
    # Get current user_uuid
    user_uuid = session['user_uuid']

    form = AdminForm(request.form)

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
    result_proxy = conn.execute(query)
    permitted_companies = [dict(c.items()) for c in result_proxy.fetchall() if c["company_uuid"] == company_uuid]

    if permitted_companies == list():
        flash("You are not permitted to add an admin for this company.", "danger")
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
            result_proxy = conn.execute(query)
            found_users = [dict(c.items()) for c in result_proxy.fetchall()]

            if found_users == list():
                flash("No user was found with this email address.", "danger")
                return render_template('/companies/add_admin_company.html', form=form, domain=domain,
                                       enterprise=enterprise)

            user = found_users[0]
            # Check if the user is already admin of this company
            query = """SELECT company_uuid, user_uuid
            FROM companies AS com
            INNER JOIN is_admin_of AS aof ON com.uuid=aof.company_uuid
            WHERE aof.user_uuid='{}' AND com.uuid='{}';""".format(user["uuid"], company_uuid)
            result_proxy = conn.execute(query)
            if result_proxy.fetchall() != list():
                flash("This user is already admin of this company.", "danger")
                return render_template('/companies/add_admin_company.html', form=form, domain=domain,
                                       enterprise=enterprise)

            # Create new is_admin_of instance
            query = db.insert(app.config["tables"]["is_admin_of"])
            values_list = [{'user_uuid': user["uuid"],
                            'company_uuid': selected_company["company_uuid"],
                            'creator_uuid': user_uuid,
                            'datetime': get_datetime()}]

            conn.execute(query, values_list)
            flash("The user {} was added to {}.{} as an admin.".format(form.email.data, domain, enterprise), "success")
            return redirect(url_for('company.show_company', company_uuid=selected_company["company_uuid"]))

        return render_template('/companies/add_admin_company.html', form=form, domain=domain, enterprise=enterprise)

# Delete admin for company
@system.route("/delete_admin_company/<string:company_uuid>/<string:admin_uuid>", methods=["GET"])
@is_logged_in
def delete_admin_company(company_uuid, admin_uuid):
    # Get current user_uuid
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
    result_proxy = conn.execute(query)
    permitted_companies = [dict(c.items()) for c in result_proxy.fetchall()]

    if permitted_companies == list():
        flash("You are not permitted to delete this company.", "danger")
        return redirect(url_for('company.show_all_companies'))

    elif user_uuid == admin_uuid:
        flash("You are not permitted to remove yourself.", "danger")
        return redirect(url_for('company.show_company', company_uuid=company_uuid))

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
            flash("nothing to delete.", "danger")
            return redirect(url_for('company.show_all_companies'))

        else:
            del_user = del_users[0]
            # Delete new is_admin_of instance
            query = """DELETE FROM is_admin_of
                WHERE user_uuid='{}'
                AND company_uuid='{}';""".format(admin_uuid, company_uuid)
            conn.execute(query)
            # print("DELETING: {}".format(query))

            flash("User with email {} was removed as admin from company {}.{}.".format(
                del_user["admin_email"], del_user["domain"], del_user["enterprise"]), "success")
            return redirect(url_for('company.show_company', company_uuid=del_user["company_uuid"]))
