from flask import Flask
from flask_testing import TestCase
from backend.app.models import (
    User,
    Contact
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
        contact = Contact(first_name='josh', creator=user)
        db.session.add(user)
        db.session.add(contact)
        db.session.commit()

        contact_dict = contact.get_dict()

        assert isinstance(contact_dict, dict)
        assert contact_dict['contact_id']
        assert contact_dict['first_name'] == "josh"
        assert contact_dict['creator']['username'] == 'samson'
