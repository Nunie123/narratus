from flask import request, jsonify
from flask_jwt_extended import (
    jwt_required, create_access_token, get_raw_jwt, get_jwt_claims
)
from backend.app.models import (
    User, Usergroup, Connection, SqlQuery, Chart, Report, Publication, Contact, TokenBlacklist
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

    request_data = request.get_json()
    username = request_data.get('username', None)
    password = request_data.get('password', None)
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
    requester = get_jwt_claims()
    if not helpers.requester_has_admin_privileges(requester):
        return jsonify(msg="User must have admin privileges to view other users", success=0), 401

    users_object_list = User.query.all()
    users_dict_list = list(map(lambda user: user.get_dict(), users_object_list))
    return jsonify(msg="All users provided.", users=users_dict_list, success=1), 200


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

    request_data = request.get_json()
    user_id = request_data.get('user_id')

    requester = get_jwt_claims()
    requester_is_editing_self = requester['user_id'] == user_id
    requester_is_active = requester['is_active']

    user = helpers.get_record_from_id(User, user_id)
    if not user:
        return jsonify(msg='Provided user_id not found.', success=0), 400

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    # non-admin can only edit themselves
    if not helpers.requester_has_admin_privileges(requester) and not requester_is_editing_self:
        return jsonify(msg="User must have admin privileges to edit other users.", success=0), 401

    # only admin can edit user roles
    if not helpers.requester_has_admin_privileges(requester) and request_data.get('role') != user.role:
        return jsonify(msg="User must have admin privileges to edit a user's role.", success=0), 401

    try:
        user = helpers.edit_user_from_dict(request_data)
        return jsonify(msg='User successfully edited.', user=user.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. User not edited'.format(exception_message), success=0), 400


@app.route('/api/delete_user', methods=['POST'])
@jwt_required
def delete_user():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    user_id = request_data.get('user_id', None)
    user = helpers.get_record_from_id(User, user_id)
    requester = get_jwt_claims()

    if not helpers.requester_has_admin_privileges(requester):
        return jsonify(msg="User must have admin privileges to delete a user.", success=0), 401

    if not user:
        return jsonify(msg='User not found', success=0), 400

    if user.role == 'superuser' and requester['role'] != 'superuser':
        return jsonify(msg="User must have superuser privileges to delete a superuser.", success=0), 401

    if requester['user_id'] == user_id:
        return jsonify(msg="User cannot delete self.", success=0), 401

    usergroup = user.get_personal_usergroup()
    db.session.delete(user)
    db.session.delete(usergroup)
    db.session.commit()
    return jsonify(msg='User deleted.', success=1), 200


@app.route('/api/get_all_usergroups', methods=['GET'])
@jwt_required
def get_all_usergroups():

    # only admin and superusers can view all usergroups
    requester = get_jwt_claims()
    if not helpers.requester_has_admin_privileges(requester):
        return jsonify(msg="User must have admin privileges to view all usergroups.", success=0), 401

    usergroups_raw = Usergroup.query.all()
    usergroups = list(map(lambda usergroup: usergroup.get_dict(), usergroups_raw))
    return jsonify(msg="All usergroups provided", usergroups=usergroups, success=1), 200


@app.route('/api/create_usergroup', methods=['POST'])
@jwt_required
def create_usergroup():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    # read-only accounts can't create new usergroups
    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to create new usergroups.", success=0), 401

    try:
        usergroup = helpers.create_usergroup_from_dict(request_data)
        return jsonify(msg='Usergroup successfully created.', usergroup=usergroup.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. Usergroup not created'.format(exception_message), success=0), 400


@app.route('/api/edit_usergroup', methods=['PATCH'])
@jwt_required
def edit_usergroup():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    usergroup_id = request_data.get('usergroup_id')

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)

    if not usergroup:
        return jsonify(msg='Provided usergroup_id not found.', success=0), 400

    if usergroup.personal_group:
        return jsonify(msg='Personal usergroups cannot be edited', success=0), 401

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to edit other usergroups.", success=0), 401

    try:
        usergroup = helpers.edit_usergroup_from_dict(request_data)
        return jsonify(msg='Usergroup successfully edited.', usergroup=usergroup.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. Usergroup not edited'.format(exception_message), success=0), 400


@app.route('/api/delete_usergroup', methods=['POST'])
@jwt_required
def delete_usergroup():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    usergroup_id = request_data.get('usergroup_id', None)
    requester = get_jwt_claims()
    usergroup = Usergroup.query.filter(Usergroup.id == usergroup_id).first()

    # validate usergroup_id
    if not usergroup_id:
        return jsonify(msg='Usergroup_id not provided.', success=0), 400
    if not usergroup:
        return jsonify(msg='Usergroup not recginized.', success=0), 400

    # Only admin can delete usergroups
    if not helpers.requester_has_admin_privileges(requester):
        return jsonify(msg='User not authorized to delete this usergroup.', success=0), 401

    # no user can delete their personal usergroup (only auto-deleted when user is deleted)
    if usergroup.personal_group:
        return jsonify(msg='Personal usergroups cannot be deleted.', success=0), 401

    # delete usergroup
    db.session.delete(usergroup)
    db.session.commit()
    return jsonify(msg='Usergroup deleted.', success=1), 200


@app.route('/api/get_all_connections', methods=['GET'])
@jwt_required
def get_all_connections():
    requester = get_jwt_claims()

    if not helpers.requester_has_admin_privileges(requester):
        return jsonify(msg='Must be admin to view all connections.', success=0), 401

    raw_connections = Connection.query.all()
    connections = list(map(lambda obj: obj.get_dict(), raw_connections))
    return jsonify(msg='Connections provided.', connections=connections, success=1), 200


@app.route('/api/create_connection', methods=['POST'])
@jwt_required
def create_connection():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    # read-only accounts can't create new connections
    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to create new connections.", success=0), 401

    try:
        connection = helpers.create_connection_from_dict(request_data, requester['user_id'])
        return jsonify(msg='Connection successfully created.', connection=connection.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. Connection not created'.format(exception_message), success=0), 400


@app.route('/api/edit_connection', methods=['PATCH'])
@jwt_required
def edit_connection():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    connection_id = request_data.get('connection_id')

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    connection = helpers.get_record_from_id(Connection, connection_id)

    if not connection:
        return jsonify(msg='Provided connection_id not found.', success=0), 400

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to edit connections.", success=0), 401

    try:
        connection = helpers.edit_connection_from_dict(request_data)
        return jsonify(msg='Connection successfully edited.', connection=connection.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. Connection not edited'.format(exception_message), success=0), 400


@app.route('/api/delete_connection', methods=['POST'])
@jwt_required
def delete_connection():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    connection_id = request_data.get('connection_id', None)
    requester = get_jwt_claims()
    connection = helpers.get_record_from_id(Connection, connection_id)

    # validate connection_id
    if not connection_id:
        return jsonify(msg='Connection ID not provided.', success=0), 400
    if not connection:
        return jsonify(msg='Connection not recognized.', success=0), 400

    # viewer users cannot delete connections
    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg='Current user does not have permission to delete connections.', success=0), 401

    db.session.delete(connection)
    db.session.commit()
    return jsonify(msg='Connection deleted.', success=1), 200


@app.route('/api/get_all_queries', methods=['GET'])
@jwt_required
def get_all_queries():
    requester = get_jwt_claims()

    if not helpers.requester_has_admin_privileges(requester):
        return jsonify(msg='Must be admin to view all queries.', success=0), 401

    raw_queries = SqlQuery.query.all()
    queries = list(map(lambda obj: obj.get_dict(), raw_queries))
    return jsonify(msg='Queries provided.', queries=queries, success=1), 200


@app.route('/api/create_query', methods=['POST'])
@jwt_required
def create_query():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    # read-only accounts can't create new queries
    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to create new queries.", success=0), 401

    try:
        query = helpers.create_query_from_dict(request_data, requester['user_id'])
        return jsonify(msg='Query successfully created.', query=query.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. Query not created'.format(exception_message), success=0), 400


@app.route('/api/edit_query', methods=['PATCH'])
@jwt_required
def edit_query():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    query_id = request_data.get('query_id')

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    query = helpers.get_record_from_id(SqlQuery, query_id)

    if not query:
        return jsonify(msg='Provided query_id not found.', success=0), 400

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to edit querys.", success=0), 401

    try:
        query = helpers.edit_query_from_dict(request_data)
        return jsonify(msg='SqlQuery successfully edited.', query=query.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. SqlQuery not edited'.format(exception_message), success=0), 400


@app.route('/api/delete_query', methods=['POST'])
@jwt_required
def delete_query():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    query_id = request_data.get('query_id', None)
    requester = get_jwt_claims()
    query = helpers.get_record_from_id(SqlQuery, query_id)

    # validate query_id
    if not query_id:
        return jsonify(msg='Query ID not provided.', success=0), 400
    if not query:
        return jsonify(msg='Query not recognized.', success=0), 400

    # viewer users cannot delete queries
    if not helpers.requester_has_write_privileges(requester):
        msg = 'Current user does not have permission to delete queries.'
        return jsonify(msg=msg, success=0), 401

    db.session.delete(query)
    db.session.commit()
    return jsonify(msg='Query deleted.', success=1), 200


@app.route('/api/get_all_charts', methods=['GET'])
@jwt_required
def get_all_charts():
    requester = get_jwt_claims()

    # only admin may see all charts regardless of usergroups
    if not helpers.requester_has_admin_privileges(requester):
        return jsonify(msg='Must be admin to view all queries.', success=0), 401

    raw_charts = Chart.query.all()
    charts = list(map(lambda obj: obj.get_dict(), raw_charts))
    return jsonify(msg='Charts provided.', charts=charts, success=1), 200


@app.route('/api/create_chart', methods=['POST'])
@jwt_required
def create_chart():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    # read-only accounts can't create new charts
    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to create new charts.", success=0), 401

    try:
        chart = helpers.create_chart_from_dict(request_data, requester['user_id'])
        return jsonify(msg='Chart successfully created.', chart=chart.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. Chart not created'.format(exception_message), success=0), 400


@app.route('/api/edit_chart', methods=['PATCH'])
@jwt_required
def edit_chart():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    chart_id = request_data.get('chart_id')

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    chart = helpers.get_record_from_id(Chart, chart_id)

    if not chart:
        return jsonify(msg='Provided chart_id not found.', success=0), 400

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to edit charts.", success=0), 401

    try:
        chart = helpers.edit_chart_from_dict(request_data)
        return jsonify(msg='Chart successfully edited.', chart=chart.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. Chart not edited'.format(exception_message), success=0), 400


@app.route('/api/delete_chart', methods=['POST'])
@jwt_required
def delete_chart():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    chart_id = request_data.get('chart_id', None)
    requester = get_jwt_claims()
    chart = helpers.get_record_from_id(Chart, chart_id)

    # validate chart_id
    if not chart_id:
        return jsonify(msg='Chart ID not provided.', success=0), 400
    if not chart:
        return jsonify(msg='Chart not recognized.', success=0), 400

    # viewer users cannot delete chart
    if not helpers.requester_has_write_privileges(requester):
        msg = 'Current user does not have permission to delete charts.'
        return jsonify(msg=msg, success=0), 401

    db.session.delete(chart)
    db.session.commit()
    return jsonify(msg='Chart deleted.', success=1), 200


@app.route('/api/get_all_reports', methods=['GET'])
@jwt_required
def get_all_reports():
    requester = get_jwt_claims()

    # only admin may see all reports regardless of usergroups
    if not helpers.requester_has_admin_privileges(requester):
        return jsonify(msg='Must be admin to view all reports.', success=0), 401

    raw_reports = Report.query.all()
    reports = list(map(lambda obj: obj.get_dict(), raw_reports))
    return jsonify(msg='Reports provided.', reports=reports, success=1), 200


@app.route('/api/create_report', methods=['POST'])
@jwt_required
def create_report():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    # read-only accounts can't create new reports
    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to create new reports.", success=0), 401

    try:
        report = helpers.create_report_from_dict(request_data, requester['user_id'])
        return jsonify(msg='Report successfully created.', report=report.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. Report not created'.format(exception_message), success=0), 400


@app.route('/api/edit_report', methods=['PATCH'])
@jwt_required
def edit_report():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    report_id = request_data.get('report_id')

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    report = helpers.get_record_from_id(Report, report_id)

    if not report:
        return jsonify(msg='Provided report_id not found.', success=0), 400

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to edit reports.", success=0), 401

    try:
        report = helpers.edit_report_from_dict(request_data)
        return jsonify(msg='Report successfully edited.', report=report.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. Report not edited'.format(exception_message), success=0), 400


@app.route('/api/delete_report', methods=['POST'])
@jwt_required
def delete_report():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    report_id = request_data.get('report_id', None)
    requester = get_jwt_claims()
    report = Report.query.filter(Report.id == report_id).first()

    if not report_id:
        return jsonify(msg='Report ID not provided.', success=0), 400
    if not report:
        return jsonify(msg='Report not recognized.', success=0), 400

    # viewer users cannot delete reports
    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg='Current user does not have permission to delete reports.', success=0), 401

    db.session.delete(report)
    db.session.commit()
    return jsonify(msg='Report deleted.', success=1), 200


@app.route('/api/get_all_publications', methods=['GET'])
@jwt_required
def get_all_publications():
    requester = get_jwt_claims()

    # only admin may see all publications regardless of usergroups
    if not helpers.requester_has_admin_privileges(requester):
        return jsonify(msg='Must be admin to view all publications.', success=0), 401

    raw_publications = Publication.query.all()
    publications = list(map(lambda obj: obj.get_dict(), raw_publications))
    return jsonify(msg='Publications provided.', publications=publications, success=1), 200


@app.route('/api/create_publication', methods=['POST'])
@jwt_required
def create_publication():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    # read-only accounts can't create new publications
    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to create new publications.", success=0), 401

    try:
        publication = helpers.create_publication_from_dict(request_data, requester['user_id'])
        return jsonify(msg='Publication successfully created.', publication=publication.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. Publication not created'.format(exception_message), success=0), 400


@app.route('/api/edit_publication', methods=['PATCH'])
@jwt_required
def edit_publication():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    publication_id = request_data.get('publication_id')

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    publication = helpers.get_record_from_id(Publication, publication_id)

    if not publication:
        return jsonify(msg='Provided publication_id not found.', success=0), 400

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to edit publications.", success=0), 401

    try:
        publication = helpers.edit_publication_from_dict(request_data)
        return jsonify(msg='Publication successfully edited.', publication=publication.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. Publication not edited'.format(exception_message), success=0), 400


@app.route('/api/delete_publication', methods=['POST'])
@jwt_required
def delete_publication():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    publication_id = request_data.get('publication_id', None)
    requester = get_jwt_claims()
    publication = helpers.get_record_from_id(Publication, publication_id)

    if not publication_id:
        return jsonify(msg='Publication ID not provided.', success=0), 400
    if not publication:
        return jsonify(msg='Publication not recognized.', success=0), 400

    # viewer users cannot delete publications
    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg='Current user does not have permission to delete publications.', success=0), 401

    db.session.delete(publication)
    db.session.commit()
    return jsonify(msg='Publication deleted.', success=1), 200


@app.route('/api/get_all_contacts', methods=['GET'])
@jwt_required
def get_all_contacts():
    requester = get_jwt_claims()

    # must have write privileges see all contacts
    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg='Must have write privileges to view all contacts.', success=0), 401

    raw_contacts = Contact.query.all()
    contacts = list(map(lambda obj: obj.get_dict(), raw_contacts))
    return jsonify(msg='Contacts provided.', contacts=contacts, success=1), 200


@app.route('/api/create_contact', methods=['POST'])
@jwt_required
def create_contact():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    # read-only accounts can't create new contacts
    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to create new contacts.", success=0), 401

    try:
        contact = helpers.create_contact_from_dict(request_data, requester['user_id'])
        return jsonify(msg='Contact successfully created.', contact=contact.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. Contact not created'.format(exception_message), success=0), 400


@app.route('/api/edit_contact', methods=['PATCH'])
@jwt_required
def edit_contact():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    contact_id = request_data.get('contact_id')

    requester = get_jwt_claims()
    requester_is_active = requester['is_active']

    contact = helpers.get_record_from_id(Contact, contact_id)

    if not contact:
        return jsonify(msg='Provided contact_id not found.', success=0), 400

    if not requester_is_active:
        return jsonify(msg="Your account is no longer active.", success=0), 401

    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg="User must have write privileges to edit contacts.", success=0), 401

    try:
        contact = helpers.edit_contact_from_dict(request_data)
        return jsonify(msg='Contact successfully edited.', contact=contact.get_dict(), success=1), 200
    except AssertionError as exception_message:
        return jsonify(msg='Error: {}. Contact not edited'.format(exception_message), success=0), 400


@app.route('/api/delete_contact', methods=['POST'])
@jwt_required
def delete_contact():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    request_data = request.get_json()
    contact_id = request_data.get('contact_id', None)
    requester = get_jwt_claims()
    contact = helpers.get_record_from_id(Contact, contact_id)

    if not contact_id:
        return jsonify(msg='Contact ID not provided.', success=0), 400
    if not contact:
        return jsonify(msg='Contact not recognized.', success=0), 400

    # viewer users cannot delete contacts
    if not helpers.requester_has_write_privileges(requester):
        return jsonify(msg='Current user does not have permission to delete contacts.', success=0), 401

    db.session.delete(contact)
    db.session.commit()
    return jsonify(msg='Contact deleted.', success=1), 200
