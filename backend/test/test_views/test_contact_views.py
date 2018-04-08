import json
from flask import Flask
from flask_testing import TestCase
from backend.app.models import Contact
from backend.test import test_utils
from backend.app import db, app
from backend.app import helper_functions as helpers


class UserViewTest(TestCase):

    def create_app(self):
        app = Flask(__name__)
        app.config.from_object(test_utils.Config())
        db.init_app(app)
        return app

    def setUp(self):
        self.client = app.test_client()
        db.create_all()

        # log in as viewer
        login_response = test_utils.create_user_and_login(username='viewer', password='Secret123', role='viewer'
                                                          , client=self.client)
        login_response_dict = json.loads(login_response.data)
        self.viewer_token = login_response_dict['access_token']

        # log in as writer
        login_response = test_utils.create_user_and_login(username='writer', password='Secret123', role='writer'
                                                          , client=self.client)
        login_response_dict = json.loads(login_response.data)
        self.writer_token = login_response_dict['access_token']

        # log in as admin
        login_response = test_utils.create_user_and_login(username='admin', password='Secret123', role='admin'
                                                          , client=self.client)
        login_response_dict = json.loads(login_response.data)
        self.admin_token = login_response_dict['access_token']

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def get_to_get_all_contacts(self, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        elif token_type == 'viewer':
            token = self.viewer_token
        else:
            token = self.admin_token
        response = self.client.get('/api/get_all_contacts', content_type='application/json'
                                   , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_create_contacts(self, first_name='conn42', email='test@example.com'
                                , token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        elif token_type == 'viewer':
            token = self.viewer_token
        else:
            token = self.admin_token

        data = dict(first_name=first_name, email=email)
        response = self.client.post('/api/create_contact', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def patch_to_edit_contacts(self, contact_id, first_name='conn42', email='test@example.com'
                               , token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        data = dict(contact_id=contact_id, first_name=first_name, email=email)
        response = self.client.patch('/api/edit_contact', data=json.dumps(data), content_type='application/json'
                                     , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_delete_contacts(self, contact_id, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        elif token_type == 'viewer':
            token = self.viewer_token
        else:
            token = self.admin_token
        data = dict(contact_id=contact_id)
        response = self.client.post('/api/delete_contact', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def test_get_all_contacts_returns_all_contacts(self):
        test_utils.create_contact(email='ug101@example.com')

        contact_count = len(Contact.query.all())

        response = self.get_to_get_all_contacts()
        response_dict = json.loads(response.data)
        response_count = len(response_dict['contacts'])

        assert response.status_code == 200
        assert contact_count == response_count

    def test_get_all_contacts_requires_write_privileges(self):
        response = self.get_to_get_all_contacts(token_type='viewer')

        assert response.status_code == 401

    def test_create_contact_with_valid_data(self):
        with db.session.no_autoflush:
            first_name = 'Sam'
            response = self.post_to_create_contacts(first_name=first_name)
            response_dict = json.loads(response.data)

            contact = Contact.query.filter(Contact.first_name == first_name).first()

            assert response.status_code == 200
            assert contact

    def test_create_contact_with_invalid_data(self):
        email = ''
        response = self.post_to_create_contacts(email=email)
        response_dict = json.loads(response.data)

        assert response.status_code == 400

    def test_create_contact_requires_writer_privileges(self):
        first_name = 'my contact'
        response = self.post_to_create_contacts(first_name=first_name, token_type='viewer')
        response_dict = json.loads(response.data)

        contact = Contact.query.filter(Contact.first_name == first_name).first()

        assert response.status_code == 401
        assert not contact

    def test_edit_email_with_valid_data(self):
        starting_email = 'test@example.com'
        con_id = 42
        test_utils.create_contact(email=starting_email, contact_id=con_id)

        new_email = 'newTest@example2.com'
        response = self.patch_to_edit_contacts(email=new_email, contact_id=con_id)
        contact = helpers.get_record_from_id(Contact, con_id)

        assert response.status_code == 200
        assert contact.email.lower() == new_email.lower()

    def test_edit_contact_with_bad_contact_id(self):
        conn_id = 999999

        response = self.patch_to_edit_contacts(contact_id=conn_id)
        contact = helpers.get_record_from_id(Contact, conn_id)

        assert response.status_code == 400
        assert not contact

    def test_edit_email_with_bad_email(self):
        starting_email = 'test123@example.com'
        conn_id = 42
        test_utils.create_contact(email=starting_email, contact_id=conn_id)

        new_email = ''
        response = self.patch_to_edit_contacts(email=new_email, contact_id=conn_id)
        response_dict = json.loads(response.data)
        contact = helpers.get_record_from_id(Contact, conn_id)

        assert contact.email == starting_email

    def test_delete_contact_removes_contact(self):
        contact_id = 1234
        test_utils.create_contact(contact_id=contact_id)

        self.post_to_delete_contacts(contact_id=contact_id)

        contact = helpers.get_record_from_id(Contact, contact_id)

        assert not contact

    def test_delete_contact_requires_writer_privileges(self):
        contact_id = 1234
        test_utils.create_contact(contact_id=contact_id)

        self.post_to_delete_contacts(contact_id=contact_id, token_type='viewer')

        contact = helpers.get_record_from_id(Contact, contact_id)

        assert contact
