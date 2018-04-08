import json
from flask import Flask
from flask_testing import TestCase
from backend.app.models import Publication
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

    def get_to_get_all_publications(self, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        response = self.client.get('/api/get_all_publications', content_type='application/json'
                                   , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_create_publication(self, report_id, type='dashboard', token_type='admin', contact_ids=None
                                   , frequency='daily'):
        if token_type == 'writer':
            token = self.writer_token
        elif token_type == 'viewer':
            token = self.viewer_token
        else:
            token = self.admin_token

        data = dict(report_id=report_id, type=type, contact_ids=contact_ids, frequency=frequency)
        response = self.client.post('/api/create_publication', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def patch_to_edit_publication(self, type=None, frequency=None
                                  , publication_id=None, token_type='admin', contact_ids=None):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        data = dict(type=type, frequency=frequency
                    , publication_id=publication_id, contact_ids=contact_ids)
        response = self.client.patch('/api/edit_publication', data=json.dumps(data), content_type='application/json'
                                     , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_delete_publications(self, publication_id, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        elif token_type == 'viewer':
            token = self.viewer_token
        else:
            token = self.admin_token
        data = dict(publication_id=publication_id)
        response = self.client.post('/api/delete_publication', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def test_get_all_publications_returns_all_publications(self):
        test_utils.create_publication()

        publication_count = len(Publication.query.all())

        response = self.get_to_get_all_publications()
        response_dict = json.loads(response.data)
        response_count = len(response_dict['publications'])

        assert response.status_code == 200
        assert publication_count == response_count

    def test_get_all_publications_requires_admin_privileges(self):
        response = self.get_to_get_all_publications(token_type='writer')

        assert response.status_code == 401

    def test_create_publication_with_valid_data(self):
        with db.session.no_autoflush:
            report_id = 111
            test_utils.create_report(report_id=report_id)

            response = self.post_to_create_publication(report_id=report_id)
            response_dict = json.loads(response.data)

            publication = Publication.query.filter(Publication.report_id == report_id).first()

        assert response.status_code == 200
        assert publication

    def test_create_publication_with_invalid_data(self):
        report_id = 111
        test_utils.create_report(report_id=report_id)

        frequency = ''
        response = self.post_to_create_publication(frequency=frequency, report_id=report_id)
        response_dict = json.loads(response.data)

        assert response.status_code == 400

    def test_create_publication_requires_writer_privileges(self):
        report_id = 111
        test_utils.create_report(report_id=report_id)

        response = self.post_to_create_publication(token_type='viewer', report_id=report_id)
        response_dict = json.loads(response.data)

        assert response.status_code == 401

    def test_edit_label_with_bad_publication_id(self):
        conn_id = 999999

        response = self.patch_to_edit_publication(publication_id=conn_id)
        publication = helpers.get_record_from_id(Publication, conn_id)

        assert response.status_code == 400
        assert not publication

    def test_add_contact_to_publication(self):
        contact_id = 42
        contact = test_utils.create_contact(contact_id=contact_id)

        report_id = 99
        test_utils.create_report(report_id=report_id)

        publication_id = 1234
        test_utils.create_publication(publication_id=publication_id, report_label='report1111')

        response = self.patch_to_edit_publication(publication_id=publication_id, contact_ids=[contact_id])

        publication = helpers.get_record_from_id(Publication, publication_id)

        assert response.status_code == 200
        assert len(publication.recipients) == 1
        assert publication.recipients[0].id == contact_id

    def test_add_recipient_to_publication_with_bad_contact_id(self):
        publication_id = 1234
        publication = test_utils.create_publication(publication_id=publication_id, report_label='report1111')

        response = self.patch_to_edit_publication(publication_id=publication_id, contact_ids=[9999])

        publication = helpers.get_record_from_id(Publication, publication_id)

        assert response.status_code == 400
        assert not publication.recipients

    def test_delete_publication_removes_publication(self):
        publication_id = 1234
        test_utils.create_publication(publication_id=publication_id)

        self.post_to_delete_publications(publication_id=publication_id)

        publication = helpers.get_record_from_id(Publication, publication_id)

        assert not publication

    def test_delete_publication_requires_writer_privileges(self):
        publication_id = 1234
        test_utils.create_publication(publication_id=publication_id)

        self.post_to_delete_publications(publication_id=publication_id, token_type='viewer')

        publication = helpers.get_record_from_id(Publication, publication_id)

        assert publication
