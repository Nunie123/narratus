import json
from flask import Flask
from flask_testing import TestCase
from backend.app.models import Chart
from backend.test import test_utils
from backend.app import db, app
from backend.app import helper_functions as helpers


class ChartViewTest(TestCase):

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

    def get_to_get_all_charts(self, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        response = self.client.get('/api/get_all_charts', content_type='application/json'
                                   , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_create_charts(self, label='conn42', type='bar', parameters='test str', sql_query_id=None
                              , connection_id=None, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        elif token_type == 'viewer':
            token = self.viewer_token
        else:
            token = self.admin_token

        data = dict(label=label, type=type, parameters=parameters, sql_query_id=sql_query_id
                    , connection_id=connection_id)
        response = self.client.post('/api/create_chart', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def patch_to_edit_charts(self, chart_id, label='conn42', type='bar', parameters='test str', sql_query_id=None
                             , connection_id=None, usergroup_ids=list(), token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        data = dict(label=label, type=type, parameters=parameters, sql_query_id=sql_query_id
                    , connection_id=connection_id, chart_id=chart_id, usergroup_ids=usergroup_ids)
        response = self.client.patch('/api/edit_chart', data=json.dumps(data), content_type='application/json'
                                     , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_delete_charts(self, chart_id, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        elif token_type == 'viewer':
            token = self.viewer_token
        else:
            token = self.admin_token
        data = dict(chart_id=chart_id)
        response = self.client.post('/api/delete_chart', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def test_get_all_charts_returns_all_charts(self):
        test_utils.create_chart(label='ug101')
        test_utils.create_chart(label='ug202')

        chart_count = len(Chart.query.all())

        response = self.get_to_get_all_charts()
        response_dict = json.loads(response.data)
        response_count = len(response_dict['charts'])

        assert response.status_code == 200
        assert chart_count == response_count

    def test_get_all_charts_requires_admin_privileges(self):
        response = self.get_to_get_all_charts(token_type='writer')

        assert response.status_code == 401

    def test_create_chart_with_valid_data(self):
        with db.session.no_autoflush:
            sql_query_id = 111
            test_utils.create_query(query_id=sql_query_id)

            connection_id = 222
            test_utils.create_connection(connection_id=connection_id)

            label = 'my chart'
            response = self.post_to_create_charts(label=label, sql_query_id=sql_query_id, connection_id=connection_id)
            response_dict = json.loads(response.data)

            chart = Chart.query.filter(Chart.label == label).first()

        assert response.status_code == 200
        assert chart

    def test_create_chart_with_invalid_data(self):
        with db.session.no_autoflush:
            sql_query_id = 111
            test_utils.create_query(query_id=sql_query_id)

            connection_id = 222
            test_utils.create_connection(connection_id=connection_id)

            label = ''
            response = self.post_to_create_charts(label=label, sql_query_id=sql_query_id, connection_id=connection_id)
            response_dict = json.loads(response.data)

            chart = Chart.query.filter(Chart.label == label).first()

        assert response.status_code == 400
        assert not chart

    def test_create_chart_requires_writer_privileges(self):
        with db.session.no_autoflush:
            sql_query_id = 111
            test_utils.create_query(query_id=sql_query_id)

            connection_id = 222
            test_utils.create_connection(connection_id=connection_id)

            label = 'my chart'
            response = self.post_to_create_charts(label=label, sql_query_id=sql_query_id, connection_id=connection_id
                                                , token_type='viewer')
            response_dict = json.loads(response.data)

            chart = Chart.query.filter(Chart.label == label).first()

        assert response.status_code == 401
        assert not chart

    def test_edit_label_with_valid_data(self):
        starting_label = 'my_conn'
        conn_id = 42
        test_utils.create_chart(label=starting_label, chart_id=conn_id)

        new_label = 'my_new_conn'
        response = self.patch_to_edit_charts(label=new_label, chart_id=conn_id)
        chart = helpers.get_record_from_id(Chart, conn_id)
        chart_label = chart.label

        assert response.status_code == 200
        assert chart_label == new_label

    def test_edit_label_with_bad_chart_id(self):
        conn_id = 999999

        response = self.patch_to_edit_charts(chart_id=conn_id)
        chart = helpers.get_record_from_id(Chart, conn_id)

        assert response.status_code == 400
        assert not chart

    def test_edit_label_with_bad_label(self):
        starting_label = 'test123'
        conn_id = 42
        test_utils.create_chart(label=starting_label, chart_id=conn_id)

        new_label = ''
        response = self.patch_to_edit_charts(label=new_label, chart_id=conn_id)
        response_dict = json.loads(response.data)
        chart = helpers.get_record_from_id(Chart, conn_id)
        chart_label = chart.label

        assert chart_label == starting_label

    def test_add_usergroup_to_chart(self):
        with db.session.no_autoflush:
            usergroup_id = 42
            usergroup = test_utils.create_usergroup(usergroup_id=usergroup_id)

            chart_id = 1234
            test_utils.create_chart(chart_id=chart_id)

            response = self.patch_to_edit_charts(chart_id=chart_id, usergroup_ids=[usergroup_id])

            chart = helpers.get_record_from_id(Chart, chart_id)

            assert response.status_code == 200
            assert len(chart.usergroups) == 1
            assert chart.usergroups[0].id == usergroup_id

    def test_add_usergroup_to_chart_with_bad_user_id(self):
        chart_id = 1234
        test_utils.create_chart(chart_id=chart_id)

        response = self.patch_to_edit_charts(chart_id=chart_id, usergroup_ids=[99999])

        chart = helpers.get_record_from_id(Chart, chart_id)

        assert response.status_code == 400
        assert not chart.usergroups

    def test_delete_chart_removes_chart(self):
        chart_id = 1234
        test_utils.create_chart(chart_id=chart_id)

        self.post_to_delete_charts(chart_id=chart_id)

        chart = helpers.get_record_from_id(Chart, chart_id)

        assert not chart

    def test_delete_chart_requires_writer_privileges(self):
        chart_id = 1234
        test_utils.create_chart(chart_id=chart_id)

        self.post_to_delete_charts(chart_id=chart_id, token_type='viewer')

        chart = helpers.get_record_from_id(Chart, chart_id)

        assert chart
