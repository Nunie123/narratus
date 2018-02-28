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

    def test_get_dict_returns_dict(self):
        user = User(username='sam')
        connection = Connection(label='con1', creator=user)
        db.session.add(user)
        db.session.add(connection)
        db.session.commit()

        connection_dict = connection.get_dict()


        assert isinstance(connection_dict, dict)
        assert connection_dict['connection_id']
        assert connection_dict['label'] == "con1"
        assert connection_dict['creator']['username'] == 'sam'
