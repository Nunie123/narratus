import unittest, json
from flask import Flask
from flask_testing import TestCase
from app.models import (
    User, Usergroup
)
from test.test_utils import TestUtils, Config
from app import db, routes, app



class UserViewTest(TestCase, TestUtils):

    def create_app(self):
        app = Flask(__name__)
        app.config.from_object(Config())
        db.init_app(app)
        return app

    def setUp(self):
        self.client = app.test_client()
        db.create_all()

        login_response = self.create_user_and_login(username='writer', password='secret', role='writer')
        login_response_dict = json.loads(login_response.data)
        self.writer_token = login_response_dict['access_token']

        login_response = self.create_user_and_login(username='admin', password='secret', role='admin')
        login_response_dict = json.loads(login_response.data)
        self.admin_token = login_response_dict['access_token']

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def post_to_edit_user(self, username, password='Secret123', email='u@example.com', role='admin'
                        , usergroup_ids = [], token_type='admin'):
        if token_type=='writer':
            token = self.writer_token
        else: token = self.admin_token
        data = dict(username=username, password=password, role=role, email=email
                    , usergroup_ids=usergroup_ids)
        response = self.client.post('/api/edit_user', data=json.dumps(data), content_type='application/json', headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def patch_to_edit_user(self, user_id, username=None, password='Secret123', email='u@example.com', role='admin', token_type='admin'):
        if token_type=='writer':
            token = self.writer_token
        else: token = self.admin_token
        data = dict(user_id=user_id, username=username, password=password, role=role, email=email)
        response = self.client.patch('/api/edit_user', data=json.dumps(data), content_type='application/json', headers={'Authorization': 'Bearer {}'.format(token)})
        return response

# field validation is tested in the test_validators.py file
    def test_create_new_user_with_valid_data(self):
        starting_user_count = len(User.query.all())

        username = 'test1'
        response = self.post_to_edit_user(username=username)
        response_dict = json.loads(response.data)
        users = User.query.all()

        print(response_dict)
        assert response.status_code == 200  # user created
        assert response_dict['user']['username'] == username
        assert len(users) == starting_user_count + 1

    def test_create_new_user_with_invalid_data(self):
        starting_user_count = len(User.query.all())
        # submit without email
        response = self.post_to_edit_user(username='test1', email='')
        response_dict = json.loads(response.data)
        users = User.query.all()

        print(response_dict)
        assert response.status_code == 400  # email required
        assert len(users) == starting_user_count

        # submit with blank username
        response = self.post_to_edit_user(username='')
        response_dict = json.loads(response.data)
        users = User.query.all()

        assert response.status_code == 400  # blank username rejected
        assert len(users) == starting_user_count

        # submit with blank password
        response = self.post_to_edit_user(username='test1', password='')
        response_dict = json.loads(response.data)
        users = User.query.all()

        assert response.status_code == 400  # blank password rejected
        assert len(users) == starting_user_count

    def test_create_new_from_non_admin_account(self):
        starting_user_count = len(User.query.all())

        response = self.post_to_edit_user(username='test1', token_type='writer')
        response_dict = json.loads(response.data)
        users = User.query.all()

        assert response.status_code == 401  # only admin can create user
        assert len(users) == starting_user_count

    def test_create_new_user_with_usergroups(self):
        starting_user_count = len(User.query.all())

        ug1 = Usergroup(label='ug1', id=1)
        ug2 = Usergroup(label='ug2', id=2)
        db.session.add(ug1, ug2)
        db.session.commit()

        username = 'test1'
        usergroup_ids = [1,2]
        response = self.post_to_edit_user(username=username, usergroup_ids=usergroup_ids)
        response_dict = json.loads(response.data)
        users = User.query.all()

        print(response_dict)
        assert response.status_code == 200 
        assert response_dict['user']['username'] == username
        assert len(users) == starting_user_count + 1
        assert False

    def test_edit_user_with_valid_data(self):
        starting_user_count = len(User.query.all())

        user_id = '42'
        user = self.create_user(username='edit1', email='edit1@example.com', role='viewer', user_id=user_id)

        response = self.patch_to_edit_user(username='edit2', email='edit2@gmail.com', role='writer', user_id=user_id)
        response_dict = json.loads(response.data)
        edited_user = User.query.filter(User.id == user_id).first()
        edited_user_dict = edited_user.get_dict()

        users = User.query.all()

        print(response_dict)
        print(users)
        assert response.status_code == 200
        assert edited_user_dict['username'] == 'edit2'
        assert len(users) == starting_user_count + 1

    def test_edit_user_with_invalid_id(self):
        starting_user_count = len(User.query.all())

        response = self.patch_to_edit_user(username='test1', user_id=9999999)
        response_dict = json.loads(response.data)
        users = User.query.all()

        print(response_dict)
        assert response.status_code == 400  # need to use POST to create user
        assert len(users) == starting_user_count
