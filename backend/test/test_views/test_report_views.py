import json
from flask import Flask
from flask_testing import TestCase
from backend.app.models import Report
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

    def get_to_get_all_reports(self, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        response = self.client.get('/api/get_all_reports', content_type='application/json'
                                   , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_edit_reports(self, label='conn42', report_type='bar', parameters='test str', sql_query_id=None
                            , connection_id=None, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        elif token_type == 'viewer':
            token = self.viewer_token
        else:
            token = self.admin_token

        data = dict(label=label, report_type=report_type, parameters=parameters, sql_query_id=sql_query_id
                    , connection_id=connection_id)
        response = self.client.post('/api/edit_report', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def patch_to_edit_reports(self, report_id, label='conn42', report_type='bar', parameters='test str', sql_query_id=None
                             , connection_id=None, usergroup_ids=list(), token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        data = dict(label=label, report_type=report_type, parameters=parameters, sql_query_id=sql_query_id
                    , connection_id=connection_id, report_id=report_id, usergroup_ids=usergroup_ids)
        response = self.client.patch('/api/edit_report', data=json.dumps(data), content_type='application/json'
                                     , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_delete_reports(self, report_id, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        elif token_type == 'viewer':
            token = self.viewer_token
        else:
            token = self.admin_token
        data = dict(report_id=report_id)
        response = self.client.post('/api/delete_report', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def test_get_all_reports_returns_all_reports(self):
        test_utils.create_report(label='ug101')
        test_utils.create_report(label='ug202')

        report_count = len(Report.query.all())

        response = self.get_to_get_all_reports()
        response_dict = json.loads(response.data)
        response_count = len(response_dict['reports'])

        assert response.status_code == 200
        assert report_count == response_count

    def test_get_all_reports_requires_admin_privileges(self):
        response = self.get_to_get_all_reports(token_type='writer')

        assert response.status_code == 401

    def test_create_report_with_valid_data(self):
        with db.session.no_autoflush:
            sql_query_id = 111
            test_utils.create_query(query_id=sql_query_id)

            connection_id = 222
            test_utils.create_connection(connection_id=connection_id)

            label = 'my report'
            response = self.post_to_edit_reports(label=label, sql_query_id=sql_query_id, connection_id=connection_id)
            response_dict = json.loads(response.data)

            report = Report.query.filter(Report.label == label).first()

        assert response.status_code == 200
        assert report

    def test_create_report_with_invalid_data(self):
        with db.session.no_autoflush:
            sql_query_id = 111
            test_utils.create_query(query_id=sql_query_id)

            connection_id = 222
            test_utils.create_connection(connection_id=connection_id)

            label = ''
            response = self.post_to_edit_reports(label=label, sql_query_id=sql_query_id, connection_id=connection_id)
            response_dict = json.loads(response.data)

            report = Report.query.filter(Report.label == label).first()

        assert response.status_code == 400
        assert not report

    def test_create_report_requires_writer_privileges(self):
        with db.session.no_autoflush:
            sql_query_id = 111
            test_utils.create_query(query_id=sql_query_id)

            connection_id = 222
            test_utils.create_connection(connection_id=connection_id)

            label = 'my report'
            response = self.post_to_edit_reports(label=label, sql_query_id=sql_query_id, connection_id=connection_id
                                                , token_type='viewer')
            response_dict = json.loads(response.data)

            report = Report.query.filter(Report.label == label).first()

        assert response.status_code == 401
        assert not report

    def test_edit_label_with_valid_data(self):
        starting_label = 'my_conn'
        conn_id = 42
        test_utils.create_report(label=starting_label, report_id=conn_id)

        new_label = 'my_new_conn'
        response = self.patch_to_edit_reports(label=new_label, report_id=conn_id)
        report = helpers.get_record_from_id(Report, conn_id)
        report_label = report.label

        assert response.status_code == 200
        assert report_label == new_label

    def test_edit_label_with_bad_report_id(self):
        conn_id = 999999

        response = self.patch_to_edit_reports(report_id=conn_id)
        report = helpers.get_record_from_id(Report, conn_id)

        assert response.status_code == 400
        assert not report

    def test_edit_label_with_bad_label(self):
        starting_label = 'test123'
        conn_id = 42
        test_utils.create_report(label=starting_label, report_id=conn_id)

        new_label = ''
        response = self.patch_to_edit_reports(label=new_label, report_id=conn_id)
        response_dict = json.loads(response.data)
        report = helpers.get_record_from_id(Report, conn_id)
        report_label = report.label

        assert report_label == starting_label

    def test_add_usergroup_to_report(self):
        with db.session.no_autoflush:
            usergroup_id = 42
            usergroup = test_utils.create_usergroup(usergroup_id=usergroup_id)

            report_id = 1234
            test_utils.create_report(report_id=report_id)

            response = self.patch_to_edit_reports(report_id=report_id, usergroup_ids=[usergroup_id])

            report = helpers.get_record_from_id(Report, report_id)

            assert response.status_code == 200
            assert len(report.usergroups) == 1
            assert report.usergroups[0].id == usergroup_id

    def test_add_usergroup_to_report_with_bad_user_id(self):
        report_id = 1234
        test_utils.create_report(report_id=report_id)

        response = self.patch_to_edit_reports(report_id=report_id, usergroup_ids=[99999])

        report = helpers.get_record_from_id(Report, report_id)

        assert response.status_code == 400
        assert not report.usergroups

    def test_delete_report_removes_report(self):
        report_id = 1234
        test_utils.create_report(report_id=report_id)

        self.post_to_delete_reports(report_id=report_id)

        report = helpers.get_record_from_id(Report, report_id)

        assert not report

    def test_delete_report_requires_writer_privileges(self):
        report_id = 1234
        test_utils.create_report(report_id=report_id)

        self.post_to_delete_reports(report_id=report_id, token_type='viewer')

        report = helpers.get_record_from_id(Report, report_id)

        assert report
