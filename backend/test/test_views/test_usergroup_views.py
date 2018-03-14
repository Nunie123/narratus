import json
from flask import Flask
from flask_testing import TestCase
from backend.app.models import Usergroup
from backend.test.test_utils import TestUtils, Config
from backend.app import db, app
from backend.app import helper_functions as helpers


class UserViewTest(TestCase, TestUtils):

    def create_app(self):
        app = Flask(__name__)
        app.config.from_object(Config())
        db.init_app(app)
        return app

    def setUp(self):
        self.client = app.test_client()
        db.create_all()

        # log in as writer
        login_response = self.create_user_and_login(username='writer', password='Secret123', role='writer')
        login_response_dict = json.loads(login_response.data)
        self.writer_token = login_response_dict['access_token']

        # log in as admin
        login_response = self.create_user_and_login(username='admin', password='Secret123', role='admin')
        login_response_dict = json.loads(login_response.data)
        self.admin_token = login_response_dict['access_token']

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def get_to_get_all_usergroups(self, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        response = self.client.get('/api/get_all_usergroups', content_type='application/json'
                                   , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_edit_usergroups(self, label='group42', token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        data = dict(label=label)
        response = self.client.post('/api/edit_usergroup', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def patch_to_edit_usergroups(self, usergroup_id, label='group42', member_ids: list = list()
                                 , connection_ids: list = list(), query_ids: list = list()
                                 , chart_ids: list = list(), report_ids: list = list()
                                 , token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        data = dict(label=label, usergroup_id=usergroup_id, member_ids=member_ids, connection_ids=connection_ids
                    , query_ids=query_ids, chart_ids=chart_ids, report_ids=report_ids)
        response = self.client.patch('/api/edit_usergroup', data=json.dumps(data), content_type='application/json'
                                     , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def test_get_all_usergroups_returns_all_usergroups(self):
        self.create_usergroup(label='ug101')
        self.create_usergroup(label='ug201')

        usergroup_count = len(Usergroup.query.all())

        response = self.get_to_get_all_usergroups()
        response_dict = json.loads(response.data)
        response_count = len(response_dict['usergroups'])

        assert response.status_code == 200
        assert usergroup_count == response_count

    def test_get_all_usergroups_requires_admin_privileges(self):
        response = self.get_to_get_all_usergroups(token_type='writer')

        assert response.status_code == 401

    def test_create_usergroup_with_valid_data(self):
        with db.session.no_autoflush:
            label = 'my usergroup'
            response = self.post_to_edit_usergroups(label=label)
            response_dict = json.loads(response.data)

            usergroup = Usergroup.query.filter(Usergroup.label == label).first()

        assert response.status_code == 200
        assert usergroup

    def test_create_usergroup_with_invalid_data(self):
        with db.session.no_autoflush:
            label = ''
            response = self.post_to_edit_usergroups(label=label)
            response_dict = json.loads(response.data)

            usergroup = Usergroup.query.filter(Usergroup.label == label).first()

        assert response.status_code == 400
        assert not usergroup

    def test_create_usergroup_requires_admin_privileges(self):
        with db.session.no_autoflush:
            label = 'my usergroup'
            response = self.post_to_edit_usergroups(label=label, token_type='writer')
            response_dict = json.loads(response.data)

            usergroup = Usergroup.query.filter(Usergroup.label == label).first()

        assert response.status_code == 401
        assert not usergroup

    def test_edit_label_with_valid_data(self):
        starting_label = 'my group'
        group_id = 42
        self.create_usergroup(label=starting_label, usergroup_id=group_id)

        new_label = 'my new group'
        response = self.patch_to_edit_usergroups(label=new_label, usergroup_id=group_id)
        usergroup = helpers.get_record_from_id(Usergroup, group_id)
        usergroup_label = usergroup.label

        assert response.status_code == 200
        assert usergroup_label == new_label

    def test_edit_label_with_bad_usergroup_id(self):
        group_id = 999999

        response = self.patch_to_edit_usergroups(usergroup_id=group_id)
        usergroup = helpers.get_record_from_id(Usergroup, group_id)

        assert response.status_code == 400
        assert not usergroup

    def test_edit_label_with_bad_label(self):
        starting_label = 'my group'
        group_id = 42
        self.create_usergroup(label=starting_label, usergroup_id=group_id)

        new_label = ''
        response = self.patch_to_edit_usergroups(label=new_label, usergroup_id=group_id)
        response_dict = json.loads(response.data)
        usergroup = helpers.get_record_from_id(Usergroup, group_id)
        usergroup_label = usergroup.label

        assert response.status_code == 400
        assert usergroup_label == starting_label

    def test_add_member_to_usergroup(self):
        user_id = 42
        user = self.create_user(user_id=user_id)

        usergroup_id = 1234
        self.create_usergroup(usergroup_id=usergroup_id)

        response = self.patch_to_edit_usergroups(usergroup_id=usergroup_id, member_ids=[user_id])

        usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)

        assert response.status_code == 200
        assert len(usergroup.members) == 1
        assert usergroup.members[0].id == user_id

    def test_add_member_to_usergroup_with_bad_user_id(self):
        usergroup_id = 1234
        self.create_usergroup(usergroup_id=usergroup_id)

        response = self.patch_to_edit_usergroups(usergroup_id=usergroup_id, member_ids=[99999])

        usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)

        assert response.status_code == 400
        assert not usergroup.members

    def test_add_connection_to_usergroup(self):
        usergroup_id = 1234
        self.create_usergroup(usergroup_id=usergroup_id)

        connection_id = 42
        self.create_connection(connection_id=connection_id)

        response = self.patch_to_edit_usergroups(usergroup_id=usergroup_id, connection_ids=[connection_id])

        usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)

        assert response.status_code == 200
        assert len(usergroup.connections) == 1

    def test_add_connection_to_usergroup_with_bad_connection_id(self):
        usergroup_id = 1234
        self.create_usergroup(usergroup_id=usergroup_id)

        connection_id = 9999999

        response = self.patch_to_edit_usergroups(usergroup_id=usergroup_id, connection_ids=[connection_id])

        usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)

        assert response.status_code == 400
        assert not usergroup.connections

    def test_add_query_to_usergroup(self):
        usergroup_id = 1234
        self.create_usergroup(usergroup_id=usergroup_id)

        query_id = 42
        self.create_query(query_id=query_id)

        response = self.patch_to_edit_usergroups(usergroup_id=usergroup_id, query_ids=[query_id])

        usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)

        assert response.status_code == 200
        assert len(usergroup.queries) == 1

    def test_add_query_to_usergroup_with_bad_query_id(self):
        usergroup_id = 1234
        self.create_usergroup(usergroup_id=usergroup_id)

        query_id = 9999999

        response = self.patch_to_edit_usergroups(usergroup_id=usergroup_id, query_ids=[query_id])

        usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)

        assert response.status_code == 400
        assert not usergroup.queries

    def test_add_chart_to_usergroup(self):
        usergroup_id = 1234
        self.create_usergroup(usergroup_id=usergroup_id)

        chart_id = 42
        self.create_chart(chart_id=chart_id)

        response = self.patch_to_edit_usergroups(usergroup_id=usergroup_id, chart_ids=[chart_id])

        usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)

        assert response.status_code == 200
        assert len(usergroup.charts) == 1

    def test_add_chart_to_usergroup_with_bad_chart_id(self):
        usergroup_id = 1234
        self.create_usergroup(usergroup_id=usergroup_id)

        chart_id = 9999999

        response = self.patch_to_edit_usergroups(usergroup_id=usergroup_id, chart_ids=[chart_id])

        usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)

        assert response.status_code == 400
        assert not usergroup.charts

    def test_add_report_to_usergroup(self):
        usergroup_id = 1234
        self.create_usergroup(usergroup_id=usergroup_id)

        report_id = 42
        self.create_report(report_id=report_id)

        response = self.patch_to_edit_usergroups(usergroup_id=usergroup_id, report_ids=[report_id])

        usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)

        assert response.status_code == 200
        assert len(usergroup.reports) == 1

    def test_add_report_to_usergroup_with_bad_report_id(self):
        usergroup_id = 1234
        self.create_usergroup(usergroup_id=usergroup_id)

        report_id = 9999999

        response = self.patch_to_edit_usergroups(usergroup_id=usergroup_id, report_ids=[report_id])

        usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)

        assert response.status_code == 400
        assert not usergroup.reports

    def test_cannot_create_personal_usergroups(self):
        label = 'personal_user42'
        response = self.post_to_edit_usergroups(label=label)

        assert response.status_code == 401

    def test_cannot_edit_personal_usergroups(self):
        starting_label = 'personal_user42'
        group_id = 42
        self.create_usergroup(label=starting_label, usergroup_id=group_id)

        new_label = 'my new group'
        response = self.patch_to_edit_usergroups(label=new_label, usergroup_id=group_id)
        usergroup = helpers.get_record_from_id(Usergroup, group_id)

        assert response.status_code == 401