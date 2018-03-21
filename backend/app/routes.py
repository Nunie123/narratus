import re
from flask import request, jsonify
from flask_jwt_extended import (
    jwt_required, create_access_token, get_raw_jwt
    , get_jwt_claims
)
from backend.app.models import (
    User, Usergroup, Connection, SqlQuery, Chart, Report, Publication,
    Contact, TokenBlacklist
)
from backend.app import app, jwt, db
from backend.app import helper_functions as helpers


@jwt.user_claims_loader
def add_claims_to_access_token(user):
    return {'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'is_active': user.is_active,
            'usergroups': user.get_dicts_from_usergroups(), }


@jwt.user_identity_loader
def user_identity_lookup(user):
    return user.username


@jwt.token_in_blacklist_loader
def check_if_token_in_blacklist(decrypted_token):
    jti = decrypted_token['jti']
    blacklist_objects = TokenBlacklist.query.all()
    blacklist = set(map(lambda obj: obj.jti, blacklist_objects))
    return jti in blacklist


@app.route('/', methods=['GET'])
def test():
    return jsonify(msg='this is working', success=1), 200


@app.route('/api/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    username = request.json.get('username', None)
    password = request.json.get('password', None)
    user = helpers.get_user_from_username(username)

    if user is None or not user.check_password(password):
        return jsonify(msg="Bad username or password", success=0), 401

    if user.is_active is False:
        return jsonify(msg="Your account is inactive.", success=0), 401

    access_token = create_access_token(identity=user)

    return jsonify(access_token=access_token, msg="Login complete.", success=1), 200


# Endpoint for revoking the current users access token
@app.route('/api/logout', methods=['POST'])
@jwt_required
def logout():
    jti = get_raw_jwt()['jti']
    blacklist_jti = TokenBlacklist(jti=jti)
    db.session.add(blacklist_jti)
    db.session.commit()
    return jsonify(msg="Logout successful.", success=1), 200


@app.route('/api/get_all_users', methods=['GET'])
@jwt_required
def get_all_users():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    # only admin and superusers can view all users
    claims = get_jwt_claims()
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg="User must have admin privileges to view other users", success=0), 401

    users_object_list = User.query.all()
    users_dict_list = list(map(lambda user: user.get_dict(), users_object_list))
    return jsonify(msg="All users provided", users=users_dict_list, success=1), 200


@app.route('/api/create_user', methods=['POST'])
@jwt_required
def create_user():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    # only admin and superusers can create new users
    if not helpers.requester_has_admin_privileges(requester):
        return jsonify(msg="User must have admin privileges to create new users.", success=0), 401

    try:
        user = helpers.create_user_from_dict(request_data)
        return jsonify(msg='User successfully created.', user=user.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. User not created'.format(exception_message), success=0), 400


@app.route('/api/edit_user', methods=['PATCH'])
@jwt_required
def edit_user():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_json = request.get_json()
    user_id = request_json.get('user_id', None)
    username = request_json.get('username', None)
    email = request_json.get('email', None)
    password = request_json.get('password', None)
    role = request_json.get('role', None)
    is_active = request_json.get('is_active', None)
    usergroup_ids = list(request_json.get('usergroup_ids', []))
    user = helpers.get_record_from_id(User, user_id)
    success_text = 'edited'
    usergroups = []
    for usergroup_id in usergroup_ids:
        record = helpers.get_record_from_id(Usergroup, usergroup_id)
        if record:
            usergroups.append(record)
        else:
            return jsonify(msg='Provided usergroup not found.', success=0), 400

    claims = get_jwt_claims()
    requester_is_editing_self = claims['user_id'] == user_id
    requester_is_admin = claims['role'] in ('admin', 'superuser')
    requester_is_active = claims['is_active']
    is_edit_user_request = user_id
    is_create_user_request = not user_id

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    # only admin and superusers can create new users
    if is_create_user_request and not requester_is_admin:
        return jsonify(msg="User must have admin privileges to create new users.", success=0), 401

    # non-admin can only edit themselves
    if is_edit_user_request and not requester_is_admin and not requester_is_editing_self:
        return jsonify(msg="User must have admin privileges to edit other users.", success=0), 401

    if is_edit_user_request and not requester_is_admin and role:
        return jsonify(msg="User must have admin privileges to edit a user's role.", success=0), 401

    # if user id is provided, check to make sure it exists in the db
    if is_edit_user_request and not user:
        msg = 'Provided user_id not found.'
        return jsonify(msg=msg, success=0), 400

    if is_edit_user_request \
            and not helpers.any_args_are_truthy(username, email, password, role, is_active, usergroup_ids):
        return jsonify(msg="No changes to user provided.", success=0), 400

    if is_create_user_request:
        user = User()
        success_text = 'added'
        db.session.add(user)

    try:
        if username or is_create_user_request:
            user.username = username.lower()

        if role:
            user.role = role

        if is_active or is_active is False:
            user.is_active = is_active

        if email or is_create_user_request:
            user.email = email.lower()

        personal_usergroup = Usergroup.query.filter(Usergroup.label == 'personal_{}'.format(user.username)).first()
        if not personal_usergroup:
            personal_usergroup = Usergroup(label='personal_{}'.format(user.username))

        if usergroups:
            user.usergroups = usergroups

        if personal_usergroup not in user.usergroups:
            db.session.add(personal_usergroup)
            user.usergroups.append(personal_usergroup)

        if password or is_create_user_request:
            user.set_password(password)

        db.session.commit()
        return jsonify(msg='User successfully {}.'.format(success_text), user=user.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. User not {}'.format(exception_message, success_text), success=0), 400


@app.route('/api/delete_user', methods=['POST'])
@jwt_required
def delete_user():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    user_id = request.json.get('user_id', None)
    user = helpers.get_record_from_id(User, user_id)
    claims = get_jwt_claims()

    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg="User must have admin privileges to delete a user.", success=0), 401

    if not user:
        return jsonify(msg='User not found', success=0), 400

    if user.role == 'superuser' and claims['role'] != 'superuser':
        return jsonify(msg="User must have superuser privileges to delete a superuser.", success=0), 401

    if claims['user_id'] == user_id:
        return jsonify(msg="User cannot delete self.", success=0), 401

    usergroup = helpers.get_personal_usergroup_from_user_object(user)
    db.session.delete(user)
    db.session.delete(usergroup)
    db.session.commit()
    return jsonify(msg='User deleted.', success=1), 200


@app.route('/api/get_all_usergroups', methods=['GET'])
@jwt_required
def get_all_usergroups():

    # only admin and superusers can view all usergroups
    claims = get_jwt_claims()
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg="User must have admin privileges to view all usergroups", success=0), 401

    try:
        usergroups_raw = Usergroup.query.all()
        usergroups = list(map(lambda usergroup: usergroup.get_dict(), usergroups_raw))
        return jsonify(msg="All usergroups provided", usergroups=usergroups, success=1), 200
    except:
        return jsonify(msg="Error occurred.", success=0), 400


# if no usergroup id is provided a new usergroup will be created
@app.route('/api/edit_usergroup', methods=['POST', 'PATCH'])
@jwt_required
def edit_usergroup():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_json = request.get_json()
    usergroup_id = request_json.get('usergroup_id', None)
    label = request_json.get('label', None)
    member_ids = list(request_json.get('member_ids', []))
    connection_ids = list(request_json.get('connection_ids', []))
    query_ids = list(request_json.get('query_ids', []))
    chart_ids = list(request_json.get('chart_ids', []))
    report_ids = list(request_json.get('report_ids', []))
    usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)
    success_text = 'edited'

    claims = get_jwt_claims()
    requester_is_admin = claims['role'] in ('admin', 'superuser')
    requester_is_active = claims['is_active']
    is_edit_usergroup_request = usergroup_id
    is_create_usergroup_request = not usergroup_id

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    # only admin and superusers can create or edit usergroups
    if not requester_is_admin:
        return jsonify(msg="User must have admin privileges to create and edit new usergroups.", success=0), 401

    # if provided usergroup_id is not valid
    if is_edit_usergroup_request and not helpers.get_record_from_id(Usergroup, usergroup_id):
        msg = 'Provided usergroup_id not found.'
        return jsonify(msg=msg, success=0), 400

    # if usergroup id is not provided create a new usergroup record
    if is_create_usergroup_request:
        usergroup = Usergroup()
        success_text = 'created'
        db.session.add(usergroup)

    if is_edit_usergroup_request \
            and not helpers.any_args_are_truthy(label, member_ids, connection_ids, query_ids, chart_ids, report_ids):
        return jsonify(msg="No changes to usergroup provided.", success=0), 400

    if re.match('personal_', label or 'x') or re.match('personal_', usergroup.label or 'x'):
        return jsonify(msg='Personal usergroups cannot be {}.'.format(success_text), success=0), 401

    try:
        for member_id in member_ids:
            user = helpers.get_record_from_id(User, member_id)
            usergroup.members.append(user)
        for connection_id in connection_ids:
            connection = helpers.get_record_from_id(Connection, connection_id)
            usergroup.connections.append(connection)
        for query_id in query_ids:
            query = helpers.get_record_from_id(SqlQuery, query_id)
            usergroup.queries.append(query)
        for chart_id in chart_ids:
            chart = helpers.get_record_from_id(Chart, chart_id)
            usergroup.charts.append(chart)
        for report_id in report_ids:
            report = helpers.get_record_from_id(Report, report_id)
            usergroup.reports.append(report)

        if label or is_create_usergroup_request:
            usergroup.label = label

        db.session.commit()
        return jsonify(msg='Usergroup successfully {}.'.format(success_text), success=1
                       , usergroup=usergroup.get_dict()), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}.'.format(exception_message), success=0), 400


@app.route('/api/delete_usergroup', methods=['POST'])
@jwt_required
def delete_usergroup():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    usergroup_id = request.json.get('usergroup_id', None)
    claims = get_jwt_claims()
    usergroup = Usergroup.query.filter(Usergroup.id == usergroup_id).first()

    # validate usergroup_id
    if not usergroup_id:
        return jsonify(msg='Usergroup_id not provided.', success=0), 400
    if not usergroup:
        return jsonify(msg='Usergroup not recoginized.', success=0), 400

    # Only admin can delete usergroups
    if claims['role'] not in ('admin', 'superuser'):
        msg = 'User not authorized to delete this usergroup.'
        return jsonify(msg=msg, success=0), 401

    # no user can delete their personal usergroup (only auto-deleted when user is deleted)
    if re.match('personal_', usergroup.label):
        return jsonify(msg='Personal usergroups cannot be deleted.', success=0), 401

    # delete usergroup
    db.session.delete(usergroup)
    db.session.commit()
    return jsonify(msg='Usergroup deleted.', success=1), 200


@app.route('/api/get_all_connections', methods=['GET'])
@jwt_required
def get_all_connections():
    claims = get_jwt_claims()

    # only admin may see all connections regardless of usergroups
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg='Must be admin to view all connections.', success=0), 401

    raw_connections = Connection.query.all()
    connections = list(map(lambda obj: obj.get_dict(), raw_connections))
    return jsonify(msg='Connections provided.', connections=connections, success=1), 200


# if no connection_id provided, create new connection
@app.route('/api/edit_connection', methods=['POST', 'PATCH'])
@jwt_required
def edit_connection():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    conn_data = request.get_json()

    connection_id = conn_data.get('connection_id')
    label = conn_data.get('label')
    db_type = conn_data.get('db_type')
    host = conn_data.get('host')
    port = conn_data.get('port')
    username = conn_data.get('username')
    password = conn_data.get('password')
    database_name = conn_data.get('database_name')
    usergroup_ids = list(conn_data.get('usergroup_ids', []))
    connection = helpers.get_record_from_id(Connection, connection_id)
    success_text = 'edited'

    claims = get_jwt_claims()
    requester_user_id = claims['user_id']
    is_edit_connection_request = connection_id
    is_create_connection_request = not is_edit_connection_request

    # viewer users cannot create new connections
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to edit or create connections.'
        return jsonify(msg=msg, success=0), 401

    if is_edit_connection_request and not connection:
        return jsonify(msg='Connection id not recognized', success=0), 400

    if is_edit_connection_request and not helpers.any_args_are_truthy(label, db_type, host, port, username, password
                                                                      , database_name, usergroup_ids):
        return jsonify(msg="No changes to connection provided.", success=0), 400

    if is_create_connection_request:
        connection = Connection()
        creator = helpers.get_record_from_id(User, requester_user_id)
        connection.creator = creator
        db.session.add(connection)
        success_text = 'added'

    try:
        if label or is_create_connection_request:
            connection.label = label

        if db_type or is_create_connection_request:
            connection.db_type = db_type

        if host or is_create_connection_request:
            connection.host = host

        if port or is_create_connection_request:
            connection.port = port

        if username or is_create_connection_request:
            connection.username = username

        if password or is_create_connection_request:
            connection.password = password

        if database_name or is_create_connection_request:
            connection.database_name = database_name

        for usergroup_id in usergroup_ids:
            usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)
            connection.usergroups.append(usergroup)

        db.session.commit()
        return jsonify(msg='Connection successfully {}.'.format(success_text), connection=connection.get_dict()
                       , success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}.'.format(exception_message), success=0), 400


@app.route('/api/delete_connection', methods=['POST'])
@jwt_required
def delete_connection():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    connection_id = request.json.get('connection_id', None)
    claims = get_jwt_claims()
    connection = helpers.get_record_from_id(Connection, connection_id)

    # validate connection_id
    if not connection_id:
        return jsonify(msg='Connection ID not provided.', success=0), 400
    if not connection:
        return jsonify(msg='Connection not recognized.', success=0), 400

    # viewer users cannot delete connections
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to delete connections.'
        return jsonify(msg=msg, success=0), 401

    db.session.delete(connection)
    db.session.commit()
    return jsonify(msg='Connection deleted.', success=1), 200


@app.route('/api/get_all_queries', methods=['GET'])
@jwt_required
def get_all_queries():
    claims = get_jwt_claims()

    # only admin may see all connections regardless of usergroups
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg='Must be admin to view all queries.', success=0), 401

    raw_queries = SqlQuery.query.all()
    queries = list(map(lambda obj: obj.get_dict(), raw_queries))
    return jsonify(msg='Queries provided.', queries=queries, success=1), 200


# if no query_id provided, create new query
@app.route('/api/edit_query', methods=['POST', 'PATCH'])
@jwt_required
def edit_query():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    data = request.get_json()

    query_id = data.get('query_id')
    label = data.get('label')
    raw_sql = data.get('raw_sql')
    usergroup_ids = list(data.get('usergroup_ids', []))
    query = helpers.get_record_from_id(SqlQuery, query_id)
    success_text = 'edited'

    claims = get_jwt_claims()
    requester_user_id = claims['user_id']
    is_edit_query_request = query_id
    is_create_query_request = not is_edit_query_request

    # viewer users cannot create new queries
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to edit or create queries.'
        return jsonify(msg=msg, success=0), 401

    if is_edit_query_request and not query:
        return jsonify(msg='SqlQuery id not recognized', success=0), 400

    if is_edit_query_request and not helpers.any_args_are_truthy(label, raw_sql, usergroup_ids):
        return jsonify(msg="No changes to query provided.", success=0), 400

    if is_create_query_request:
        query = SqlQuery()
        creator = helpers.get_record_from_id(User, requester_user_id)
        query.creator = creator
        db.session.add(query)
        success_text = 'added'

    try:
        if label or is_create_query_request:
            query.label = label

        if raw_sql or is_create_query_request:
            query.raw_sql = raw_sql

        for usergroup_id in usergroup_ids:
            usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)
            query.usergroups.append(usergroup)

        db.session.commit()
        return jsonify(msg='SqlQuery successfully {}.'.format(success_text), query=query.get_dict()
                       , success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}.'.format(exception_message), success=0), 400


@app.route('/api/delete_query', methods=['POST'])
@jwt_required
def delete_query():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    query_id = request.json.get('query_id', None)
    claims = get_jwt_claims()
    query = helpers.get_record_from_id(SqlQuery, query_id)

    # validate query_id
    if not query_id:
        return jsonify(msg='Query ID not provided.', success=0), 400
    if not query:
        return jsonify(msg='Query not recognized.', success=0), 400

    # viewer users cannot delete queries
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to delete queries.'
        return jsonify(msg=msg, success=0), 401

    db.session.delete(query)
    db.session.commit()
    return jsonify(msg='Query deleted.', success=1), 200


@app.route('/api/get_all_charts', methods=['GET'])
@jwt_required
def get_all_charts():
    claims = get_jwt_claims()

    # only admin may see all charts regardless of usergroups
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg='Must be admin to view all queries.', success=0), 401

    raw_charts = Chart.query.all()
    charts = list(map(lambda obj: obj.get_dict(), raw_charts))
    return jsonify(msg='Charts provided.', charts=charts, success=1), 200


# if no chat_id provided, create new chart
@app.route('/api/edit_chart', methods=['POST', 'PATCH'])
@jwt_required
def edit_chart():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    data = request.get_json()

    chart_id = data.get('chart_id')
    label = data.get('label')
    chart_type = data.get('chart_type')
    parameters = data.get('parameters')
    sql_query_id = data.get('sql_query_id')
    connection_id = data.get('connection_id')
    usergroup_ids = list(data.get('usergroup_ids', []))
    chart = helpers.get_record_from_id(Chart, chart_id)
    success_text = 'edited'

    claims = get_jwt_claims()
    requester_user_id = claims['user_id']
    is_edit_chart_request = chart_id
    is_create_chart_request = not is_edit_chart_request

    # viewer users cannot create new charts
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to edit or create charts.'
        return jsonify(msg=msg, success=0), 401

    if is_edit_chart_request and not chart:
        return jsonify(msg='Chart id not recognized', success=0), 400

    if is_edit_chart_request and not helpers.any_args_are_truthy(label, chart_type, parameters, sql_query_id
                                                                 , connection_id, usergroup_ids):
        return jsonify(msg="No changes to chart provided.", success=0), 400

    if is_create_chart_request:
        chart = Chart()
        creator = helpers.get_record_from_id(User, requester_user_id)
        chart.creator = creator
        db.session.add(chart)
        success_text = 'added'

    try:
        if label or is_create_chart_request:
            chart.label = label

        if chart_type or is_create_chart_request:
            chart.type = chart_type

        if parameters or is_create_chart_request:
            chart.parameters = parameters

        if sql_query_id or is_create_chart_request:
            chart.sql_query_id = sql_query_id

        if connection_id or is_create_chart_request:
            chart.connection_id = connection_id

        for usergroup_id in usergroup_ids:
            usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)
            chart.usergroups.append(usergroup)

        db.session.commit()
        return jsonify(msg='Chart successfully {}.'.format(success_text), chart=chart.get_dict()
                       , success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}.'.format(exception_message), success=0), 400


@app.route('/api/delete_chart', methods=['POST'])
@jwt_required
def delete_chart():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    chart_id = request.json.get('chart_id', None)
    claims = get_jwt_claims()
    chart = helpers.get_record_from_id(Chart, chart_id)

    # validate chart_id
    if not chart_id:
        return jsonify(msg='Chart ID not provided.', success=0), 400
    if not chart:
        return jsonify(msg='Chart not recognized.', success=0), 400

    # viewer users cannot delete chart
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to delete charts.'
        return jsonify(msg=msg, success=0), 401

    db.session.delete(chart)
    db.session.commit()
    return jsonify(msg='Chart deleted.', success=1), 200


@app.route('/api/get_all_reports', methods=['GET'])
@jwt_required
def get_all_reports():
    claims = get_jwt_claims()

    # only admin may see all reports regardless of usergroups
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg='Must be admin to view all reports.', success=0), 401

    raw_reports = Report.query.all()
    reports = list(map(lambda obj: obj.get_dict(), raw_reports))
    return jsonify(msg='Reports provided.', reports=reports, success=1), 200


# if no report_id provided, create new report
@app.route('/api/edit_report', methods=['POST', 'PATCH'])
@jwt_required
def edit_report():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    data = request.get_json()

    report_id = data.get('report_id')
    label = data.get('label')
    parameters = data.get('parameters')
    publication_ids = list(data.get('publication_ids', []))
    usergroup_ids = list(data.get('usergroup_ids', []))
    report = helpers.get_record_from_id(Report, report_id)
    success_text = 'edited'

    claims = get_jwt_claims()
    requester_user_id = claims['user_id']
    is_edit_report_request = report_id
    is_create_report_request = not is_edit_report_request

    # viewer users cannot create new reports
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to edit or create reports.'
        return jsonify(msg=msg, success=0), 401

    if is_edit_report_request and not report:
        return jsonify(msg='Report id not recognized', success=0), 400

    if is_edit_report_request and not helpers.any_args_are_truthy(label, parameters, publication_ids, usergroup_ids):
        return jsonify(msg="No changes to report provided.", success=0), 400

    if is_create_report_request:
        report = Report()
        creator = helpers.get_record_from_id(User, requester_user_id)
        report.creator = creator
        db.session.add(report)
        success_text = 'added'

    try:
        if label or is_create_report_request:
            report.label = label

        if parameters or is_create_report_request:
            report.parameters = parameters

        for publication_id in publication_ids:
            publication = helpers.get_record_from_id(Publication, publication_id)
            report.usergroups.append(publication)

        for usergroup_id in usergroup_ids:
            usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)
            report.usergroups.append(usergroup)

        db.session.commit()
        return jsonify(msg='Report successfully {}.'.format(success_text), report=report.get_dict()
                       , success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}.'.format(exception_message), success=0), 400


@app.route('/api/delete_report', methods=['POST'])
@jwt_required
def delete_report():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    report_id = request.json.get('report_id', None)
    claims = get_jwt_claims()
    report = Report.query.filter(Report.id == report_id).first()

    # validate report_id
    if not report_id:
        return jsonify(msg='Report ID not provided.', success=0), 400
    if not report:
        return jsonify(msg='Report not recognized.', success=0), 400

    # viewer users cannot delete connections
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to delete reports.'
        return jsonify(msg=msg, success=0), 401

    try:
        db.session.delete(report)
        db.session.commit()
        return jsonify(msg='Report deleted.', success=1), 200
    except:
        return jsonify(msg='Error: Report not deleted.', success=0), 400

@app.route('/api/edit_publication', methods=['PUT', 'POST'])
@jwt_required
def edit_publication():
    pass

@app.route('/api/delete_publication', methods=['POST'])
@jwt_required
def delete_publication():
    pass

@app.route('/api/get_all_contacts', methods=['GET'])
@jwt_required
def get_all_contacts():
    claims = get_jwt_claims()

    # only admin may see all connections regardless of usergroups
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg='Must be admin to view all contacts.', success=0), 401

    try:
        raw_contacts = Contact.query.all()
        contacts = list(map(lambda obj: obj.get_dict(), raw_contacts))
        return jsonify(msg='Contacts provided.', contacts=contacts, success=1), 200
    except:
        return jsonify(msg='Error: contacts not provided.', success=0), 400

@app.route('/api/get_user_contacts', methods=['GET'])
@jwt_required
def get_user_contacts():
    claims = get_jwt_claims()
    user = User.query.filter(User.id == claims['user_id']).first()

    try:
        charts = user.get_contacts()
        return jsonify(msg='Contacts provided.', contacts=contacts, success=1), 200
    except:
        return jsonify(msg='Error: contacts not provided.', success=0), 400

# if no contact_id provided, create new contact
@app.route('/api/edit_contact', methods=['POST', 'PATCH'])
@jwt_required
def edit_contact():
    pass

@app.route('/api/delete_contact', methods=['POST'])
@jwt_required
def delete_contact():
    pass
