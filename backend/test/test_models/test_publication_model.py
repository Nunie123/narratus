from flask import Flask
from flask_testing import TestCase
from app.models import (
    User, Report, Publication, Contact
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
        report = Report(label='r1', creator=user)
        publication = Publication(type='email', creator=user, publication_report=report)
        db.session.add(user)
        db.session.add(report)
        db.session.add(publication)
        db.session.commit()

        publication_dict = publication.get_dict()

        assert isinstance(publication_dict, dict)
        assert publication_dict['publication_id']
        assert publication_dict['type'] == "email"
        assert publication_dict['creator']['username'] == 'sam'
        assert publication_dict['report_id'] == 1

    def test_get_recipients(self):
        user = User(username='sam')
        report = Report(label='r1', creator=user)
        contact1 = Contact(first_name='Josiah', creator=user)
        contact2 = Contact(first_name='Toby', creator=user)
        publication = Publication(type='email', creator=user, publication_report=report)
        publication.recipients.append(contact1)
        publication.recipients.append(contact2)
        db.session.add(user)
        db.session.add(report)
        db.session.add(contact1, contact2)
        db.session.add(publication)
        db.session.commit()

        recipients_list = publication.get_recipients()

        assert isinstance(recipients_list, list)
        assert isinstance(recipients_list[0], dict)
        assert recipients_list[0]['first_name'] in ['Josiah', 'Toby']
