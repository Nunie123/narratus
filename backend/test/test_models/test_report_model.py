from flask import Flask
from flask_testing import TestCase
from backend.app.models import (
    User, Report, Publication
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
        report = Report(label='report1', creator=user)
        db.session.add(report)
        db.session.commit()

        report_dict = report.get_dict()

        assert isinstance(report_dict, dict)
        assert report_dict['report_id']
        assert report_dict['label'] == "report1"
        assert report_dict['creator']['username'] == 'samson'

    def test_get_publications(self):
        user = self.create_user(username='samson')
        report = Report(label='report1', creator=user)
        Publication(creator=user, type='email', publication_report=report)
        db.session.add(report)
        db.session.commit()

        pub_list = report.get_publications()

        assert isinstance(pub_list, list)
        assert isinstance(pub_list[0], dict)
        assert pub_list[0]['type'] == 'email'
        assert pub_list[0]['creator']['username'] == 'samson'
