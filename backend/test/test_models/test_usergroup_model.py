from flask import Flask
from flask_testing import TestCase
from sqlalchemy import exc
from backend.app.models import (
    Usergroup
)
from backend.app import db
from backend.test.test_utils import TestUtils, Config


class UserModelTest(TestCase, TestUtils):

    def create_app(self):
        app = Flask(__name__)
        app.config.from_object(Config())
        db.init_app(app)
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_get_members(self):
        user1 = self.create_user(username='samson')
        user2 = self.create_user(username='joshua')
        usergroup = Usergroup(label='group1')
        usergroup.members.append(user1)
        usergroup.members.append(user2)

        members = usergroup.get_members()

        assert len(members) == 2
        assert isinstance(members[0], dict)
        assert members[0]['username'] == 'samson'

    def test_get_dict_returns_dict(self):
        user = self.create_user(username='samson')
        usergroup = self.create_usergroup(label='group1')
        usergroup.members.append(user)
        db.session.commit()
        usergroup_dict = usergroup.get_dict()

        assert isinstance(usergroup_dict, dict)
        assert usergroup_dict['usergroup_id']
        assert usergroup_dict['label'] == "group1"
        assert usergroup_dict['members'][0]['username'] == 'samson'

    def test_labels_are_unique(self):
        self.create_user(username='samson')
        try:
            self.create_user(username='samson')
            raise Exception('username must be unique.')
        except (exc.IntegrityError, AssertionError):
            pass
