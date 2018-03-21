import json
from flask import Flask
from flask_testing import TestCase
from backend.app.models import Connection
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

    def get_to_get_all_connections(self, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        response = self.client.get('/api/get_all_connections', content_type='application/json'
                                   , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_edit_connections(self, label='conn42', db_type='postgresql', host='www.example.com', port='1492'
                                 , username='conn_user1', password='secret', database_name='dev'
                                 , token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        elif token_type == 'viewer':
            token = self.viewer_token
        else:
            token = self.admin_token
        data = dict(label=label, db_type=db_type, host=host, port=port, username=username, password=password
                    , database_name=database_name)
        response = self.client.post('/api/edit_connection', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def patch_to_edit_connections(self, connection_id, label='conn42', db_type='postgresql', host='www.example.com'
                                  , port='1492', usergroup_ids=list()
                                  , username='conn_user1', password='secret', database_name='dev'
                                  , token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        data = dict(label=label, db_type=db_type, host=host, port=port, username=username, password=password
                    , database_name=database_name, connection_id=connection_id, usergroup_ids=usergroup_ids)
        response = self.client.patch('/api/edit_connection', data=json.dumps(data), content_type='application/json'
                                     , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_delete_connections(self, connection_id, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        elif token_type == 'viewer':
            token = self.viewer_token
        else:
            token = self.admin_token
        data = dict(connection_id=connection_id)
        response = self.client.post('/api/delete_connection', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def test_get_all_connections_returns_all_connections(self):
        test_utils.create_connection(label='ug101')
        test_utils.create_connection(label='ug201')

        connection_count = len(Connection.query.all())

        response = self.get_to_get_all_connections()
        response_dict = json.loads(response.data)
        response_count = len(response_dict['connections'])

        assert response.status_code == 200
        assert connection_count == response_count

    def test_get_all_connections_requires_admin_privileges(self):
        response = self.get_to_get_all_connections(token_type='writer')

        assert response.status_code == 401

    def test_create_connection_with_valid_data(self):
        with db.session.no_autoflush:
            label = 'my connection'
            response = self.post_to_edit_connections(label=label)
            response_dict = json.loads(response.data)

            connection = Connection.query.filter(Connection.label == label).first()

        assert response.status_code == 200
        assert connection

    def test_create_connection_with_invalid_data(self):
        with db.session.no_autoflush:
            label = ''
            response = self.post_to_edit_connections(label=label)
            response_dict = json.loads(response.data)

            connection = Connection.query.filter(Connection.label == label).first()

        assert response.status_code == 400
        assert not connection

    def test_create_connection_requires_writer_privileges(self):
        with db.session.no_autoflush:
            label = 'my_connection'
            response = self.post_to_edit_connections(label=label, token_type='viewer')
            response_dict = json.loads(response.data)

            connection = Connection.query.filter(Connection.label == label).first()

        assert response.status_code == 401
        assert not connection

    def test_edit_label_with_valid_data(self):
        starting_label = 'my_conn'
        conn_id = 42
        test_utils.create_connection(label=starting_label, connection_id=conn_id)

        new_label = 'my_new_conn'
        response = self.patch_to_edit_connections(label=new_label, connection_id=conn_id)
        connection = helpers.get_record_from_id(Connection, conn_id)
        connection_label = connection.label

        assert response.status_code == 200
        assert connection_label == new_label

    def test_edit_label_with_bad_connection_id(self):
        conn_id = 999999

        response = self.patch_to_edit_connections(connection_id=conn_id)
        connection = helpers.get_record_from_id(Connection, conn_id)

        assert response.status_code == 400
        assert not connection

    def test_edit_label_with_bad_label(self):
        starting_label = 'my_conn'
        conn_id = 42
        test_utils.create_connection(label=starting_label, connection_id=conn_id)

        new_label = ''
        response = self.patch_to_edit_connections(label=new_label, connection_id=conn_id)
        response_dict = json.loads(response.data)
        connection = helpers.get_record_from_id(Connection, conn_id)
        connection_label = connection.label

        assert connection_label == starting_label

    def test_add_usergroup_to_connection(self):
        usergroup_id = 42
        usergroup = test_utils.create_usergroup(usergroup_id=usergroup_id)

        connection_id = 1234
        test_utils.create_connection(connection_id=connection_id)

        response = self.patch_to_edit_connections(connection_id=connection_id, usergroup_ids=[usergroup_id])

        connection = helpers.get_record_from_id(Connection, connection_id)

        assert response.status_code == 200
        assert len(connection.usergroups) == 1
        assert connection.usergroups[0].id == usergroup_id

    def test_add_usergroup_to_connection_with_bad_user_id(self):
        connection_id = 1234
        test_utils.create_connection(connection_id=connection_id)

        response = self.patch_to_edit_connections(connection_id=connection_id, usergroup_ids=[99999])

        connection = helpers.get_record_from_id(Connection, connection_id)

        assert response.status_code == 400
        assert not connection.usergroups

    def test_delete_connection_removes_connection(self):
        connection_id = 1234
        test_utils.create_connection(connection_id=connection_id)

        self.post_to_delete_connections(connection_id=connection_id)

        connection = helpers.get_record_from_id(Connection, connection_id)

        assert not connection

    def test_delete_connection_requires_writer_privileges(self):
        connection_id = 1234
        test_utils.create_connection(connection_id=connection_id)

        self.post_to_delete_connections(connection_id=connection_id, token_type='viewer')

        connection = helpers.get_record_from_id(Connection, connection_id)

        assert connection
