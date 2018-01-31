from flask import request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from app.models import User
from app.forms import LoginForm, RegistrationForm
from app import app

@app.route('/')
def home():
    return 'root endpoint'


@app.route('/api/login', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return jsonify([{"status":"User already logged in."}])
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            return jsonify([{"response":"Username or password invalid."}])
        login_user(user, remember=form.remember_me.data)
        return jsonify([{"status":"Login successful.",
                        "username":user.username}])

@app.route('/api/logout')
def logout():
    logout_user()
    return jsonify([{"status":"Logout successful."}])

@app.route('/register', methods=['POST'])
def register():
    if current_user.is_authenticated:
        return jsonify([{"status":"User already logged in."}])
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        return jsonify([{"status":"User registered."}])
    return jsonify([{"status":"User not registered."}])

@app.route('/api/users', methods=['GET'])
@login_required
def get_all_users():
    users_raw = User.query.filter_by(username=form.username.data).all()
    users = list(map(lambda user: {"username":user.username, "email":user.email}), users_raw)
    return jsonify(users)

@app.route('/connections', methods=['GET', 'POST'])
@login_required
def connection():
    if request.method == 'GET':
        pass
        #get connections that user has permission to view
    elif request.method == 'POST':
        pass
        #create new connection and permission to view
    return 'connections endpoint'
