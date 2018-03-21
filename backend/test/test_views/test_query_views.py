import json
from flask import Flask
from flask_testing import TestCase
from backend.app.models import SqlQuery
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

    def get_to_get_all_queries(self, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        response = self.client.get('/api/get_all_queries', content_type='application/json'
                                   , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_edit_queries(self, label='conn42', raw_sql='select * from table'
                                 , token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        elif token_type == 'viewer':
            token = self.viewer_token
        else:
            token = self.admin_token
        data = dict(label=label, raw_sql=raw_sql)
        response = self.client.post('/api/edit_query', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def patch_to_edit_queries(self, query_id, label='conn42', raw_sql='select * from table', usergroup_ids=list()
                                  , token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        data = dict(label=label, raw_sql=raw_sql, usergroup_ids=usergroup_ids, query_id=query_id)
        response = self.client.patch('/api/edit_query', data=json.dumps(data), content_type='application/json'
                                     , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_delete_queries(self, query_id, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        elif token_type == 'viewer':
            token = self.viewer_token
        else:
            token = self.admin_token
        data = dict(query_id=query_id)
        response = self.client.post('/api/delete_query', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def test_get_all_queries_returns_all_queries(self):
        test_utils.create_query(label='ug101')
        test_utils.create_query(label='ug202')

        query_count = len(SqlQuery.query.all())

        response = self.get_to_get_all_queries()
        response_dict = json.loads(response.data)
        response_count = len(response_dict['queries'])

        assert response.status_code == 200
        assert query_count == response_count

    def test_get_all_queries_requires_admin_privileges(self):
        response = self.get_to_get_all_queries(token_type='writer')

        assert response.status_code == 401

    def test_create_query_with_valid_data(self):
        with db.session.no_autoflush:
            label = 'my query'
            response = self.post_to_edit_queries(label=label)
            response_dict = json.loads(response.data)

            query = SqlQuery.query.filter(SqlQuery.label == label).first()

        assert response.status_code == 200
        assert query

    def test_create_query_with_invalid_data(self):
        with db.session.no_autoflush:
            label = ''
            response = self.post_to_edit_queries(label=label)
            response_dict = json.loads(response.data)

            query = SqlQuery.query.filter(SqlQuery.label == label).first()

        assert response.status_code == 400
        assert not query

    def test_create_query_requires_writer_privileges(self):
        with db.session.no_autoflush:
            label = 'my_query'
            response = self.post_to_edit_queries(label=label, token_type='viewer')
            response_dict = json.loads(response.data)

            query = SqlQuery.query.filter(SqlQuery.label == label).first()

        assert response.status_code == 401
        assert not query

    def test_edit_label_with_valid_data(self):
        starting_label = 'my_conn'
        conn_id = 42
        test_utils.create_query(label=starting_label, query_id=conn_id)

        new_label = 'my_new_conn'
        response = self.patch_to_edit_queries(label=new_label, query_id=conn_id)
        query = helpers.get_record_from_id(SqlQuery, conn_id)
        query_label = query.label

        assert response.status_code == 200
        assert query_label == new_label

    def test_edit_label_with_bad_query_id(self):
        conn_id = 999999

        response = self.patch_to_edit_queries(query_id=conn_id)
        query = helpers.get_record_from_id(SqlQuery, conn_id)

        assert response.status_code == 400
        assert not query

    def test_edit_label_with_bad_label(self):
        starting_label = 'test123'
        conn_id = 42
        test_utils.create_query(label=starting_label, query_id=conn_id)

        new_label = ''
        response = self.patch_to_edit_queries(label=new_label, query_id=conn_id)
        response_dict = json.loads(response.data)
        query = helpers.get_record_from_id(SqlQuery, conn_id)
        query_label = query.label

        assert query_label == starting_label

    def test_add_usergroup_to_query(self):
        usergroup_id = 42
        usergroup = test_utils.create_usergroup(usergroup_id=usergroup_id)

        query_id = 1234
        test_utils.create_query(query_id=query_id)

        response = self.patch_to_edit_queries(query_id=query_id, usergroup_ids=[usergroup_id])

        query = helpers.get_record_from_id(SqlQuery, query_id)

        assert response.status_code == 200
        assert len(query.usergroups) == 1
        assert query.usergroups[0].id == usergroup_id

    def test_add_usergroup_to_query_with_bad_user_id(self):
        query_id = 1234
        test_utils.create_query(query_id=query_id)

        response = self.patch_to_edit_queries(query_id=query_id, usergroup_ids=[99999])

        query = helpers.get_record_from_id(SqlQuery, query_id)

        assert response.status_code == 400
        assert not query.usergroups

    def test_delete_query_removes_query(self):
        query_id = 1234
        test_utils.create_query(query_id=query_id)

        self.post_to_delete_queries(query_id=query_id)

        query = helpers.get_record_from_id(SqlQuery, query_id)

        assert not query

    def test_delete_query_requires_writer_privileges(self):
        query_id = 1234
        test_utils.create_query(query_id=query_id)

        self.post_to_delete_queries(query_id=query_id, token_type='viewer')

        query = helpers.get_record_from_id(SqlQuery, query_id)

        assert query
