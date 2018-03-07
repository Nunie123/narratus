from flask import Flask
from flask_testing import TestCase
from backend.app.models import (
    User, SqlQuery
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

    def test_get_dict_returns_dict(self):
        user = self.create_user(username='samson')
        query = SqlQuery(label='q1', creator=user)
        db.session.add(user)
        db.session.add(query)
        db.session.commit()

        query_dict = query.get_dict()

        assert isinstance(query_dict, dict)
        assert query_dict['query_id']
        assert query_dict['label'] == "q1"
        assert query_dict['creator']['username'] == 'samson'
