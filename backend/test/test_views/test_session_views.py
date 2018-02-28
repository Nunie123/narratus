import unittest, json
from flask import Flask, jsonify
from flask_testing import TestCase
from app.models import (
    User, Usergroup, Connection, SqlQuery, Chart, Report, Publication,
    Contact, TokenBlacklist, connection_perms
)
from app import db, routes, app

class Config:
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class UserSessionTest(TestCase):

    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True

    def create_app(self):
        app = Flask(__name__)
        app.config.from_object(Config())
        db.init_app(app)
        return app

    def setUp(self):
        self.client = app.test_client()
        db.create_all()
        user = User(username='sam')
        user.set_password('westwing')
        db.session.add(user)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def login(self, username, password):
        data = dict(username=username, password=password)
        # print(json.load(data))
        return self.client.post('/api/login', data=json.dumps(data), content_type='application/json')

    def logout(self, token):
        return self.client.post('/api/logout', headers={'Authorization': 'Bearer {}'.format(token)})

    # def test_routes(self):
    #     rv = self.client.get('/')
    #     print(rv)
    #     assert False

    def test_login_logout(self):
        #response = json.load(self.login('sam', 'westwing'))
        response = self.login('sam', 'westwing')
        response_dict = json.loads(response.data)
        token = response_dict['access_token']

        assert response.status_code == 200

        response = self.logout(token)
        print(response)
        print(response.data)
        # response_dict = json.loads(response.data)
        assert response.status_code == 200
        #
        # response = self.login('adminx', 'default')
        # assert b'Invalid username' in response.data
        #
        # response = self.login('admin', 'defaultx')
        # assert b'Invalid password' in response.data
