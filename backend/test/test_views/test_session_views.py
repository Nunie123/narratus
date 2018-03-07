import json
from flask import Flask
from flask_testing import TestCase
from backend.app.models import (
    User
)
from backend.test.test_utils import TestUtils, Config
from backend.app import db, app


class UserSessionTest(TestCase, TestUtils):

    def create_app(self):
        app = Flask(__name__)
        app.config.from_object(Config())
        db.init_app(app)
        return app

    def setUp(self):
        super().setUp()
        self.client = app.test_client()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_login_logout(self):
        username = 'samson'
        password = 'Secret123'
        self.create_user(username=username, password=password)
        response = self.login(username=username, password=password)
        response_dict = json.loads(response.data)
        token = response_dict['access_token']

        assert response.status_code == 200  # login successful

        response = self.logout(token)
        assert response.status_code == 200  # logout successful

        response = self.logout(token)
        assert response.status_code == 401  # token revoked

        response = self.login(username='unknown_sam', password='westwing')
        assert response.status_code == 401  # username rejected

        response = self.login(username='samson', password='incorrect')
        assert response.status_code == 401  # password rejected

        response = self.login(username='samson', password='')
        assert response.status_code == 401  # empty password rejected

        response = self.login(username='', password='westwing')
        assert response.status_code == 401  # empty username rejected
