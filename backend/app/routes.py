from flask import request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User, Connection
from app.forms import LoginForm, RegistrationForm
from app import app

@app.route('/')
def home():
    return 'root endpoint'


@app.route('/api/login', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return jsonify([{"status":"User already logged in.", "success":"0"}])
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            return jsonify([{"status":"Username or password invalid.", "success":"0"}])
        try:
            login_user(user, remember=form.remember_me.data)
            return jsonify([{"status":"Login successful.",
                        "username":user.username},
                        "success":"1"])
        except:
            return jsonify([{"status":"Login failed due to error", "success":"0"}])

@app.route('/api/logout')
def logout():
    try:
        logout_user()
        return jsonify([{"status":"Logout successful.", "success":"1"}])
    except:
        return jsonify([{"status":"Logout failed.", "success":"0"}])

@app.route('/register', methods=['POST'])
def register():
    if current_user.is_authenticated:
        return jsonify([{"status":"User already logged in.", "success":"0"}])
    form = RegistrationForm()
    if form.validate_on_submit():
        try:
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            return jsonify([{"status":"User registered.", "success":"1"}])
        except:
            return jsonify([{"status":"Error occured, user NOT registered.", "success":"0"}])
    return jsonify([{"status":"User not registered.", "success":"0"}])

@app.route('/api/users', methods=['GET'])
@login_required
def get_all_users():
    try:
        users_raw = User.query.filter_by(username=form.username.data).all()
        users = list(map(lambda user: {"username":user.username, "email":user.email}), users_raw)
        return jsonify(["users":users, "success":"1"])
    except:
        return jsonify([{"status":"Error occured.", "success":"0"}])

@app.route('/connections', methods=['GET', 'POST'])
@login_required
def connection():
    if request.method == 'GET':
        try:
            return jsonify(["connections":User.get_connections(), "success":"1"])
        except:
            return jsonify(["status":"Error occured.", "success":"0"])
    elif request.method == 'POST':
        try:
            data = request.get_json()[0]
            c = Connection(
                label = data['label'],
                db_type = data['db_type'],
                host = data['host'],
                port = data['port'],
                username = data['username'],
                password = data['password'],
                database_name = data['database_name']
            )
            db.session.add(c)
            db.session.commit()
            return jsonify([{"status":"Connection added."}])
        except:
            return jsonify([{"status":"Error Occured, Connection NOT added."}])
    return 'connections endpoint'
