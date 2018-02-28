from flask import Flask
from flask_testing import TestCase
from app.models import (
    User, Usergroup, Connection, SqlQuery, Chart, Report, Publication,
    Contact, TokenBlacklist, connection_perms
)
from app import db

class Config:
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class UserModelTest(TestCase):

    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True

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
        user1 = User(username='sam')
        user2 = User(username='josh')
        usergroup = Usergroup(label='group1')
        usergroup.members.append(user1)
        usergroup.members.append(user2)

        members = usergroup.get_members()

        assert len(members) == 2
        assert isinstance(members[0], dict)
        assert members[0]['username'] == 'sam'

    def test_get_dict_returns_dict(self):
        user = User(username='sam')
        usergroup = Usergroup(label='group1')
        usergroup.members.append(user)
        db.session.add(usergroup, user)
        db.session.commit()
        usergroup_dict = usergroup.get_dict()

        assert isinstance(usergroup_dict, dict)
        assert usergroup_dict['usergroup_id']
        assert usergroup_dict['label'] == "group1"
        assert usergroup_dict['members'][0]['username'] == 'sam'

    def test_labels_are_unique(self):
        usergroup1 = Usergroup(label="sam")
        usergroup2 = Usergroup(label="sam")
        db.session.add(usergroup1, usergroup2)
        db.session.commit()

        usergroups = Usergroup.query.all()

        assert len(usergroups) == 1
