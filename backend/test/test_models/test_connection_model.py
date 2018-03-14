from flask import Flask
from flask_testing import TestCase
from backend.app.models import Connection
from backend.app import db
from backend.test import test_utils


class UserModelTest(TestCase):

    def create_app(self):
        app = Flask(__name__)
        app.config.from_object(test_utils.Config())
        db.init_app(app)
        return app

    def setUp(self):
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_get_dict_returns_dict(self):
        user = test_utils.create_user(username='samson')
        connection = Connection(label='con1', creator=user)
        db.session.add(connection)
        db.session.commit()

        connection_dict = connection.get_dict()

        assert isinstance(connection_dict, dict)
        assert connection_dict['connection_id']
        assert connection_dict['label'] == "con1"
        assert connection_dict['creator']['username'] == 'samson'
