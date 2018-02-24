from flask import request, jsonify
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token, get_jwt_identity
)
from app.models import (
    User, Usergroup, Connection, Query, Chart, Report, Publication,
    Contact, TokenBlacklist
)
from app import app, jwt, db
import app.validators as validators

@jwt.user_claims_loader
def add_claims_to_access_token(user):
    return {'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role}

@jwt.user_identity_loader
def user_identity_lookup(user):
    return user.username

@jwt.token_in_blacklist_loader
def check_if_token_in_blacklist(decrypted_token):
    jti = decrypted_token['jti']
    blacklist_objects = Report.query.filter(Report.id.in_(report_ids)).all()
    blacklist = set(map(lambda obj: obj.jti, blacklist_objects))
    return jti in blacklist

@app.route('/')
def home():
    return 'root endpoint'


@app.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    username = request.json.get('username', None)
    password = request.json.get('password', None)
    if not username:
        return jsonify(msg="Missing username parameter", success=0), 400
    if not password:
        return jsonify(msg="Missing password parameter", success=0), 400
    user = User.query.filter(User.username == username).first()

    if user is None or not user.check_password(password):
        return jsonify(msg="Bad username or password", success=0), 401

    # Identity can be any data that is json serializable
    access_token = create_access_token(identity=user)
    return jsonify(access_token=access_token
                    , msg="Login complete."
                    , success=1), 200

# Endpoint for revoking the current users access token
@app.route('/api/logout', methods=['DELETE'])
@jwt_required
def logout():
    try:
        jti = get_raw_jwt()['jti']
        blacklist_jti = TokenBlacklist(jti=jti)
        db.session.add(blacklist_jti)
        db.session.commit()
        return jsonify([{"msg":"Logout successful.", "success":"1"}]), 200
    except:
        return jsonify([{"msg":"Logout failed.", "success":"0"}]), 400

@app.route('/create_user', methods=['POST'])
@jwt_required
def create_user():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    #only admin and superusers can create new users
    claims = get_jwt_claims()
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg="User must have admin priviledges to create new users", success=0), 401

    username = request.json.get('username', None)
    email = request.json.get('email', None)
    password = request.json.get('password', None)
    role = request.json.get('role', None)

    # validating input
    username_check = validators.validate_username(username)
    if not username_check['validated']:
        return jsonify(msg=username_check['msg'], success=0), 400
    email_check = validators.validate_email(email)
    if not email_check['validated']:
        return jsonify(msg=email_check['msg'], success=0), 400
    password_check = validators.validate_password(password)
    if not password_check['validated']:
        return jsonify(msg=password_check['msg'], success=0), 400
    if not role_check['validated']:
        return jsonify(msg=role_check['msg'], success=0), 400

    # adding user to database and creating usergroup containing just that user.
    try:
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        ug = Usergroup(name='personal_{}'.format(username))
        db.session.add(ug)
        db.session.commit()
        user = User.query.filted(User.username == username).first()
        usergroup_id = Usergroup.query.filter(Usergroup.name == 'personal_{}'.format(username)).first().id
        user.usergroups.append(usergroup_id)
        return jsonify([{"msg":"User registered.", "success":"1"}]), 200
    except:
        return jsonify([{"msg":"Error occured, user NOT registered.", "success":"0"}]), 400


@app.route('/edit_user', methods=['PATCH'])
@jwt_required
def edit_user():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    old_username = request.json.get('old_username', None)
    new_username = request.json.get('new_username', None)
    email = request.json.get('email', None)
    old_password = request.json.get('old_password', None)
    new_password = request.json.get('new_password', None)
    role = request.json.get('role', None)
    user = User.query.filter(User.username == old_username).first()

    #only admin and superusers can create new users
    claims = get_jwt_claims()
    if claims['role'] not in ('admin', 'superuser') and claims['username']!=username:
        return jsonify(msg="User must have admin priviledges to edit other users", success=0), 401


    # validating input
    if not user:
        return jsonify(msg='User not found', success=0), 400
    if new_username:
        username_check = validators.validate_username(new_username)
        if not username_check['validated']:
            return jsonify(msg=username_check['msg'], success=0), 400
    if email:
        email_check = validators.validate_email(email)
        if not email_check['validated']:
            return jsonify(msg=email_check['msg'], success=0), 400
    #a user modifying their own password must provide existing password and new password.
    #an admin modifying someone else's password need not provide the existing password
    if new_password:
        if not user.check_password(old_password) and claims['username']==username:
            return jsonify(msg='Current password is incorrect.', success=0), 401
        password_check = validators.validate_password(new_password)
        if not password_check['validated']:
            return jsonify(msg=password_check['msg'], success=0), 400
    if role:
        if not role_check['validated']:
            return jsonify(msg=role_check['msg'], success=0), 400

    # adding user to database
    if not username and not email and not new_password and not role:
        return jsonify(msg='No user attributes provided.', success=0), 400

    try:
        if new_username:
            user.username = new_username
        if email:
            user.email = email
        if new_password:
            user.set_password(new_password)
        if role:
            user.role = role
        db.session.commit()
        return jsonify([{"msg":"User updated.", "success":"1"}]), 200
    except:
        return jsonify([{"msg":"Error occured, user NOT registered.", "success":"0"}]), 400

@app.route('/delete_user', methods=['DELETE'])
@jwt_required
def delete_user():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    user_id = request.json.get('user_id', None)
    user = User.query.filter(User.id == user_id).first()
    claims = get_jwt_claims()

    if not user:
        return jsonify(msg='User not found', success=0), 400

    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg="User must have admin priviledges to delete a user.", success=0), 401

    if user.role != 'superuser':
        return jsonify(msg="User must have superuser priviledges to delete a superuser.", success=0), 401

    usergroup = Usergroup.query.filter(Usergroup.name == 'personal_{}'.format(user.username))
    db.session.delete(user, usergroup)
    db.session.commit()
    return jsonify(msg='User deleted.', success=1), 200

@app.route('/api/get_all_users', methods=['GET'])
@jwt_required
def get_all_users():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    #only admin and superusers can view all users
    claims = get_jwt_claims()
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg="User must have admin priviledges to view other users", success=0), 401

    try:
        users_raw = User.query.all()
        users = list(map(lambda user: user.get_dict()), users_raw)
        return jsonify(msg="All users provided",users=users, success=1), 200
    except:
        return jsonify(msg="Error occured.", success=0), 400

@app.route('/api/get_all_usergroups', methods=['GET'])
@jwt_required
def get_all_usergroups():

    #only admin and superusers can view all usergroups
    claims = get_jwt_claims()
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg="User must have admin priviledges to view all usergroups", success=0), 401

    try:
        usergroups_raw = Usergroup.query.all()
        usergroups = list(map(lambda usergroup: usergroup.get_dict(), usergroups_raw))
        return jsonify(msg="All usergroups provided",users=users, success=1), 200
    except:
        return jsonify(msg="Error occured.", success=0), 400

@app.route('/api/get_usergroups_by_user', methods=['GET'])
@jwt_required
def get_usergroups_by_user():

    username = request.json.get('username', None)
    claims = get_jwt_claims()

    #endpoint will return current user's usergroups if no username is provided
    if not username:
        username = claims['username']

    user = User.query.filter(User.username == username).first()

    #only admin and superusers can cview another user's usergroups
    if claims['role'] not in ('admin', 'superuser') and claims['username']!=username:
        return jsonify(msg="User must have admin priviledges to view other users' usergroups", success=0), 401

    try:
        usergroups = user.get_usergroups()
        return jsonify(msg="All usergroups provided",usergroups=usergroups, success=1), 200
    except:
        return jsonify(msg="Error occured.", success=0), 400

# if no usergroup id is provided a new usergroup will be created
@app.route('/api/edit_usergroup', methods=['POST', 'PATCH'])
@jwt_required
def edit_usergroup():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    usergroup_id = request.json.get('usergroup_id', None)
    name = request.json.get('name', None)
    member_ids = list(request.json.get('members', []))
    connection_ids = list(request.json.get('connections', []))
    query_ids = list(request.json.get('queries', []))
    chart_ids = list(request.json.get('charts', []))
    report_ids = list(request.json.get('reports', []))
    claims = get_jwt_claims()
    success_text = 'edited'

    # Admin may add anyone to usergroup.  Standard user may only add themself.
    if claims['role'] not in ('admin', 'superuser'):
        if len(member_names)>1 or member_names[0]!=claims['username']:
            msg = 'Only admin may add other users to usergroup'
            return jsonify(msg=msg, success=0), 401

    # if usergroup id is not provided create a new usergroup record
    if not usergroup_id and request.method == 'POST':
        if not name:
            return jsonify(msg='Usergroup name must be provided.', success=0), 400
        if re.match('personal_', name):
            return jsonify(msg='Usergroup name cannot start with "personal".', success=0), 400
        ug = Usergroup(name=name)
        db.session.add(ug)
        db.session.commit()
        usergroup_id = Usergroup.query.filter(Usergroup.name == name).first().id
        success_text = 'created'
    # creating new usergroup shoudl be done with POST http method
    elif not usergroup_id and request.method != 'POST':
        msg = 'No usergroup_id provided.  To create new usergroup, use POST method.'
        return jsonify(msg=msg, success=0), 400
    # editing existing usergroup should be done through PATCH http method
    elif usergroup_id and request.method != 'PATCH':
        msg = 'Usergroup_id provided.  To edit existing usergroup, use PATCH method.'
        return jsonify(msg=msg, success=0), 400
    # if usergroup id is provided, check to make sure it exists in the db
    elif usergroup_id and not Usergroup.query.filter(Usergroup.id == usergroup_id):
        msg = 'Provided usergoup_id not found.'
        return jsonify(msg=msg, success=0), 400

    for member_id in member_ids:
        user = User.query.filted(User.id == member_id)
        user.usergroups.append(usergroup_id)
    for connection_id in connection_ids:
        connection = Connection.query.filted(Connection.id == connection_id)
        onnection.usergroups.append(usergroup_id)
    for query_id in query_ids:
        query = Query.query.filted(Query.id == query_id)
        query.usergroups.append(usergroup_id)
    for chart_id in chart_ids:
        chart = Chart.query.filted(Chart.id == chart_id)
        chart.usergroups.append(usergroup_id)
    for report_id in report_ids:
        report = Report.query.filted(Report.id == report_id)
        report.usergroups.append(usergroup_id)

    try:
        db.session.commit()
        return jsonify(msg='Usergroup successfully {}.'.format(success_text), success=1), 200
    except:
        return jsonify(msg='Error: usergroup not {}.'.format(success_text), success=0), 400

@app.route('/api/delete_usergroup', methods=['DELETE'])
@jwt_required
def delete_usergroup():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    usergroup_id = request.json.get('usergroup_id', None)
    claims = get_jwt_claims()
    usergroup = Usergroup.query.filter(Usergroup.id = usergroup_id)

    #validate usergroup_id
    if not usergroup_id:
        return jsonify(msg='Usergroup_id not provided.', success=0), 400
    if not usergroup:
        return jsonify(msg='Usergroup not recoginized.', success=0), 400

    # Admin may delete any usergroup.
    # Standard user may only delete usergroups when they are the only member.
    if claims['role'] not in ('admin', 'superuser'):
        members = usergroup.get_members()
        if len(members)>1 or members[0]['username']!=claims['username']:
            msg = 'User not authorized to delete this usergroup.'
            return jsonify(msg=msg, success=0), 401
    # no user can delete their personal usergroup (only auto-deleted when user is deleted)
    if re.match('personal_',usergroup.name):
        return jsonify(msg='Personal usergroups cannot be deleted.', success=0), 401

    #delete usergroup
    try:
        db.session.delete(usergroup)
        db.session.commit()
        return jsonify(msg='Usergroup deleted.', success=1), 200
    except:
        return jsonify(msg='Error: Usergroup not deleted.', success=0), 400

@app.route('/api/get_all_connections', methods=['GET'])
@jwt_required
def get_all_connections():
    claims = get_jwt_claims()

    # only admin may see all connections regardless of usergroups
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg='Must be admin to view all connections.', success=0), 401

    try:
        raw_connections = Connection.query.all()
        connections = list(map(lambda obj: obj.get_dict(), raw_connections))
        return jsonify(msg='Connections provided.', connections=connections, success=1), 200
    except:
        return jsonify(msg='Error: connections not provided.', success=0), 400


@app.route('/api/get_user_connections', methods=['GET'])
@jwt_required
def get_user_connections():
    claims = get_jwt_claims()
    user = User.query.filter(User.id == claims['user_id']).first()

    try:
        connections = user.get_connections()
        return jsonify(msg='Connections provided.', connections=connections, success=1), 200
    except:
        return jsonify(msg='Error: connections not provided.', success=0), 400

# if no connection_id provided, create new connection
@app.route('/api/edit_connection', methods=['POST', 'PATCH'])
@jwt_required
def edit_connection():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    usergroup_ids = list(request.json.get('usergroup_ids', []))
    connection_dict = request.get_json()[0]
    claims = get_jwt_claims()
    success_text = 'edited'
    connection = Connection.query.filter(Connection.id == connection_id).first()

    # viewer users cannot create new connections
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to edit or create connections.'
        return jsonify(msg=msg, success=0), 401

    #Verifying if user intended to edit or create new connection
    if connection_id and request.method == 'POST':
        msg='Connection Id provided with POST request.  PATCH should be used to edit existing connections.'
        return jsonify(msg=msg, success=0), 400
    if not connection_id and request.method == 'PATCH':
        msg='No Connection Id provided with PATCH request.  POST should be used to create new connection.'
        return jsonify(msg=msg, success=0), 400
    if connection_id and not connection:
        return jsonify(msg='Connection Id not recognized', success=0), 400

    # validate provided connection data for creating a new connection
    if not connection:
        required_fields = ['label', 'db_type', 'host', 'port', 'username', 'password', 'database_name', 'usergroup_ids']
        field_check = validators.validate_required_fields(required_fields, connection_dict)
        if not field_check['validated']:
            return jsonify(msg=field_check['msg'], success=0), 400
        usergroup_id_check = validators.validate_usergroup_ids(usergroup_ids)
        if not usergroup_id_check['validated']:
            return jsonify(msg=usergroup_id_check['msg'], success=0), 400
        success_text = 'added'
        connection = Connection()

    connection.label = connection_dict.get('label', connection.label)
    connection.db_type = connection_dict.get('db_type', connection.db_type)
    connection.host = connection_dict.get('host', connection.host)
    connection.port = connection_dict.get('port', connection.port)
    connection.username = connection_dict.get('username', connection.username)
    connection.password = connection_dict.get('password', connection.password)
    connection.database_name = connection_dict.get('database_name', connection.database_name)
    connection.usergroups.append(usergroup_ids)
    try:
        if success_text = 'added': db.session.add(connection)
        db.session.commit()
        return jsonify(msg='Connection successfully {}.'.format(success_text), success=1), 200
    except:
        return jsonify(msg='Error: Connection not {}'.format(success_text), success=0), 400


@app.route('/api/delete_connection', methods=['DELETE'])
@jwt_required
def delete_connection():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    connection_id = request.json.get('connection_id', None)
    claims = get_jwt_claims()
    connection = Connection.query.filter(Connection.id = connection_id)

    #validate connection_id
    if not connection_id:
        return jsonify(msg='Connection ID not provided.', success=0), 400
    if not connection:
        return jsonify(msg='Connection not recoginized.', success=0), 400

    # viewer users cannot delete connections
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to delete connections.'
        return jsonify(msg=msg, success=0), 401

    #delete usergroup
    try:
        db.session.delete(connection)
        db.session.commit()
        return jsonify(msg='Connection deleted.', success=1), 200
    except:
        return jsonify(msg='Error: Connection not deleted.', success=0), 400

@app.route('/api/get_all_queries', methods=['GET'])
@jwt_required
def get_all_queries():
    claims = get_jwt_claims()

    # only admin may see all connections regardless of usergroups
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg='Must be admin to view all queries.', success=0), 401

    try:
        raw_queries = Query.query.all()
        queries = list(map(lambda obj: obj.get_dict(), raw_queries))
        return jsonify(msg='Queries provided.', queries=queries, success=1), 200
    except:
        return jsonify(msg='Error: queries not provided.', success=0), 400

@app.route('/api/get_user_queries', methods=['GET'])
@jwt_required
def get_user_queries():
    claims = get_jwt_claims()
    user = User.query.filter(User.id == claims['user_id']).first()

    try:
        queries = user.get_queries()
        return jsonify(msg='Queries provided.', queries=queries, success=1), 200
    except:
        return jsonify(msg='Error: queries not provided.', success=0), 400

# if no query_id provided, create new query
@app.route('/api/edit_query', methods=['POST', 'PATCH'])
@jwt_required
def edit_query():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    usergroup_ids = list(request.json.get('usergroup_ids', []))
    query_dict = request.get_json()[0]
    claims = get_jwt_claims()
    success_text = 'edited'
    query = Query.query.filter(Query.id == query_id).first()

    # viewer users cannot create new queries
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to edit or create queries.'
        return jsonify(msg=msg, success=0), 401

    #Verifying if user intended to edit or create new query
    if query_id and request.method == 'POST':
        msg='Query Id provided with POST request.  PATCH should be used to edit existing query.'
        return jsonify(msg=msg, success=0), 400
    if not query_id and request.method == 'PATCH':
        msg='No Query Id provided with PATCH request.  POST should be used to create new query.'
        return jsonify(msg=msg, success=0), 400
    if query_id and not query:
        return jsonify(msg='Query Id not recognized', success=0), 400

    # validate provided query data for creating a new query
    if not query:
        required_fields = ['label', 'raw_sql', 'creator']
        field_check = validators.validate_required_fields(required_fields, query_dict)
        if not field_check['validated']:
            return jsonify(msg=field_check['msg'], success=0), 400
        user_check = validators.validate_user_exists(query_dict['creator'])
        if not user_check['validated']:
            return jsonify(msg=user_check['msg'], success=0), 400
        usergroup_id_check = validators.validate_usergroup_ids(usergroup_ids)
        if not usergroup_id_check['validated']:
            return jsonify(msg=usergroup_id_check['msg'], success=0), 400
        success_text = 'added'
        query = Query()

    query.label = query_dict.get('label', query.label)
    query.raw_sql = query_dict.get('raw_sql', query.raw_sql)
    query.user_id = query_dict.get('creator', query.user_id)
    query.usergroups.append(usergroup_ids)
    try:
        if success_text = 'added': db.session.add(query)
        db.session.commit()
        return jsonify(msg='Query successfully {}.'.format(success_text), success=1), 200
    except:
        return jsonify(msg='Error: Query not {}'.format(success_text), success=0), 400


@app.route('/api/delete_query', methods=['DELETE'])
@jwt_required
def delete_query():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    query_id = request.json.get('query_id', None)
    claims = get_jwt_claims()
    query = Query.query.filter(Query.id = query_id)

    #validate connection_id
    if not query_id:
        return jsonify(msg='Query ID not provided.', success=0), 400
    if not query:
        return jsonify(msg='Query not recoginized.', success=0), 400

    # viewer users cannot delete connections
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to delete queries.'
        return jsonify(msg=msg, success=0), 401

    #delete usergroup
    try:
        db.session.delete(query)
        db.session.commit()
        return jsonify(msg='Query deleted.', success=1), 200
    except:
        return jsonify(msg='Error: Query not deleted.', success=0), 400

@app.route('/api/get_all_charts', methods=['GET'])
@jwt_required
def get_all_charts():
    claims = get_jwt_claims()

    # only admin may see all charts regardless of usergroups
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg='Must be admin to view all queries.', success=0), 401

    try:
        raw_charts = Chart.query.all()
        charts = list(map(lambda obj: obj.get_dict(), raw_charts))
        return jsonify(msg='Charts provided.', charts=charts, success=1), 200
    except:
        return jsonify(msg='Error: charts not provided.', success=0), 400

@app.route('/api/get_user_charts', methods=['GET'])
@jwt_required
def get_user_charts():
    claims = get_jwt_claims()
    user = User.query.filter(User.id == claims['user_id']).first()

    try:
        charts = user.get_charts()
        return jsonify(msg='Charts provided.', charts=charts, success=1), 200
    except:
        return jsonify(msg='Error: charts not provided.', success=0), 400

# if no chat_id provided, create new chart
@app.route('/api/edit_chart', methods=['POST', 'PATCH'])
@jwt_required
def edit_chart():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    usergroup_ids = list(request.json.get('usergroup_ids', []))
    chart_dict = request.get_json()[0]
    claims = get_jwt_claims()
    success_text = 'edited'
    chart = Chart.query.filter(Chart.id == chart_id).first()

    # viewer users cannot create new charts
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to edit or create charts.'
        return jsonify(msg=msg, success=0), 401

    #Verifying if user intended to edit or create new chart
    if chart_id and request.method == 'POST':
        msg='Chart Id provided with POST request.  PATCH should be used to edit existing chart.'
        return jsonify(msg=msg, success=0), 400
    if not chart_id and request.method == 'PATCH':
        msg='No Chart Id provided with PATCH request.  POST should be used to create new chart.'
        return jsonify(msg=msg, success=0), 400
    if chart_id and not chart:
        return jsonify(msg='Chart Id not recognized', success=0), 400

    # validate provided chart data for creating a new chart
    if not chart:
        required_fields = ['label', 'creator', 'type', 'parameters', 'query_id', 'connection_id']
        field_check = validators.validate_required_fields(required_fields, chart_dict)
        if not field_check['validated']:
            return jsonify(msg=field_check['msg'], success=0), 400
        user_check = validators.validate_user_exists(chart_dict['creator'])
        if not user_check['validated']:
            return jsonify(msg=user_check['msg'], success=0), 400
        usergroup_id_check = validators.validate_usergroup_ids(usergroup_ids)
        if not usergroup_id_check['validated']:
            return jsonify(msg=usergroup_id_check['msg'], success=0), 400
        success_text = 'added'
        chart = Chart()

    chart.label = query_dict.get('label', chart.label)
    chart.user_id = query_dict.get('creator', chart.user_id)
    chart.type = query_dict.get('type', chart.type)
    chart.parameters = query_dict.get('parameters', chart.parameters)
    chart.query_id = query_dict.get('query_id', chart.query_id)
    chart.connection_id = query_dict.get('label', chart.connection_id)
    chart.usergroups.append(usergroup_ids)
    try:
        if success_text = 'added': db.session.add(chart)
        db.session.commit()
        return jsonify(msg='Chart successfully {}.'.format(success_text), success=1), 200
    except:
        return jsonify(msg='Error: Chart not {}'.format(success_text), success=0), 400

@app.route('/api/delete_chart', methods=['DELETE'])
@jwt_required
def delete_chart():

@app.route('/api/get_all_reports', methods=['GET'])
@jwt_required
def get_all_reports():
    claims = get_jwt_claims()

    # only admin may see all reports regardless of usergroups
    if claims['role'] not in ('admin', 'superuser'):
        return jsonify(msg='Must be admin to view all reports.', success=0), 401

    try:
        raw_reports = Report.query.all()
        reports = list(map(lambda obj: obj.get_dict(), raw_reports))
        return jsonify(msg='Reports provided.', reports=reports, success=1), 200
    except:
        return jsonify(msg='Error: reports not provided.', success=0), 400

@app.route('/api/get_user_reports', methods=['GET'])
@jwt_required
def get_user_reports():
    claims = get_jwt_claims()
    user = User.query.filter(User.id == claims['user_id']).first()

    try:
        reports = user.get_reports()
        return jsonify(msg='Reports provided.', reports=reports, success=1), 200
    except:
        return jsonify(msg='Error: reports not provided.', success=0), 400

# if no report_id provided, create new report
@app.route('/api/edit_report', methods=['POST', 'PATCH'])
@jwt_required
def edit_report():
    if not request.is_json:
        return jsonify(msg="Missing JSON in request", success=0), 400

    usergroup_ids = list(request.json.get('usergroup_ids', []))
    report_dict = request.get_json()[0]
    claims = get_jwt_claims()
    success_text = 'edited'
    report = Report.query.filter(report.id == report_id).first()
    # publication_dict = report_dict['publication']
    # recipients_id_list = list(puplication_dict['recipient_ids'])
    # publication = Publication.query.filter(report.id == report_id).first()
    # recipients = list(map(lambda user_id: User.query.filter(User.id == user_id).first(), recipients_id_list))

    # viewer users cannot create new reports
    if claims['role'] == 'viewer':
        msg = 'Current user does not have permission to edit or create reports.'
        return jsonify(msg=msg, success=0), 401

    #Verifying if user intended to edit or create new report
    if report_id and request.method == 'POST':
        msg='Report Id provided with POST request.  PATCH should be used to edit existing report.'
        return jsonify(msg=msg, success=0), 400
    if not report_id and request.method == 'PATCH':
        msg='No report id provided with PATCH request.  POST should be used to create new report.'
        return jsonify(msg=msg, success=0), 400
    if report_id and not report:
        return jsonify(msg='Report Id not recognized', success=0), 400

    # validate provided report data for creating a new report
    if not report:
        required_fields = ['label', 'creator', 'parameters', 'publication']
        field_check = validators.validate_required_fields(required_fields, report_dict)
        if not field_check['validated']:
            return jsonify(msg=field_check['msg'], success=0), 400
        user_check = validators.validate_user_exists(report_dict['creator'])
        if not user_check['validated']:
            return jsonify(msg=user_check['msg'], success=0), 400
        usergroup_id_check = validators.validate_usergroup_ids(usergroup_ids)
        if not usergroup_id_check['validated']:
            return jsonify(msg=usergroup_id_check['msg'], success=0), 400
        for recipient_id in recipients_id_list:
            recipients_check = validators.validate_contact_exists(recipient_id)
            if not recipients_check['validated']:
                return jsonify(msg=recipients_check['msg'], success=0), 400
        success_text = 'added'
        report = Report()



    report.label = query_dict.get('label', report.label)
    report.user_id = query_dict.get('creator', report.user_id)
    report.type = query_dict.get('type', report.type)
    report.parameters = query_dict.get('parameters', report.parameters)
    report.query_id = query_dict.get('query_id', report.query_id)
    report.connection_id = query_dict.get('label', report.connection_id)
    report.usergroups.append(usergroup_ids)
    try:
        if success_text = 'added': db.session.add(report)
        db.session.commit()
        return jsonify(msg='report successfully {}.'.format(success_text), success=1), 200
    except:
        return jsonify(msg='Error: report not {}'.format(success_text), success=0), 400


@app.route('/api/delete_report', methods=['DELETE'])
@jwt_required
def delete_report():

@app.route('/api/get_all_publications_for_report', methods=['DELETE'])
@jwt_required
def get_all_publications_for_report():

@app.route('/api/edit_publication', methods=['DELETE'])
@jwt_required
def edit_publication():

@app.route('/api/delete_publication', methods=['DELETE'])
@jwt_required
def delete_publication():

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

@app.route('/api/delete_contact', methods=['DELETE'])
@jwt_required
def delete_contact():
