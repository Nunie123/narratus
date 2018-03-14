import json
from flask import Flask
from flask_testing import TestCase
from backend.app.models import (
    User, Usergroup
)
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

    def post_to_edit_user(self, username, password='Secret123', email='u@example.com', role='admin'
                          , usergroup_ids=list(), token_type='admin'):
        if token_type=='writer':
            token = self.writer_token
        else:
            token = self.admin_token
        data = dict(username=username, password=password, role=role, email=email
                    , usergroup_ids=usergroup_ids)
        response = self.client.post('/api/edit_user', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def patch_to_edit_user(self, user_id, username=None, password='Secret123', email='u@example.com', role='admin'
                           , usergroup_ids=list(), is_active=True, token_type='admin'):
        if token_type=='writer':
            token = self.writer_token
        else:
            token = self.admin_token
        data = dict(user_id=user_id, username=username, password=password, role=role, email=email
                    , usergroup_ids=usergroup_ids, is_active=is_active)
        response = self.client.patch('/api/edit_user', data=json.dumps(data), content_type='application/json'
                                     , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def post_to_delete_user(self, user_id, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        data = dict(user_id=user_id)
        response = self.client.post('/api/delete_user', data=json.dumps(data), content_type='application/json'
                                    , headers={'Authorization': 'Bearer {}'.format(token)})
        return response

    def get_to_get_all_users(self, token_type='admin'):
        if token_type == 'writer':
            token = self.writer_token
        else:
            token = self.admin_token
        response = self.client.get('/api/get_all_users', content_type='application/json'
                                   , headers={'Authorization': 'Bearer {}'.format(token)})
        return response


# field validation is tested in the test_validators.py file
    def test_create_new_user_with_valid_data(self):
        with db.session.no_autoflush:
            starting_user_count = len(User.query.all())

            username = 'test123'
            response = self.post_to_edit_user(username=username)
            response_dict = json.loads(response.data)
            users = User.query.all()

        assert response.status_code == 200  # user created
        assert response_dict['user']['username'] == username
        assert len(users) == starting_user_count + 1

    def test_create_new_user_with_blank_email(self):
        with db.session.no_autoflush:
            starting_user_count = len(User.query.all())
            response = self.post_to_edit_user(username='test1', email='')
            response_dict = json.loads(response.data)
            users = User.query.all()

        assert response.status_code == 400  # email required
        assert len(users) == starting_user_count

    def test_create_new_user_with_blank_username(self):
        with db.session.no_autoflush:
            starting_user_count = len(User.query.all())
            response = self.post_to_edit_user(username='')
            response_dict = json.loads(response.data)
            users = User.query.all()

        assert response.status_code == 400  # blank username rejected
        assert len(users) == starting_user_count

    def test_create_new_user_with_blank_password(self):
        with db.session.no_autoflush:
            starting_user_count = len(User.query.all())
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

    def test_create_new_user_with_valid_usergroups(self):
        with db.session.no_autoflush:
            starting_user_count = len(User.query.all())

            ug1 = Usergroup(label='ug101', id=101)
            ug2 = Usergroup(label='ug102', id=102)
            db.session.add(ug1)
            db.session.add(ug2)
            db.session.commit()

            username = 'test123'
            usergroup_ids = [101, 102]
            response = self.post_to_edit_user(username=username, usergroup_ids=usergroup_ids)
            response_dict = json.loads(response.data)
            users = User.query.all()

        assert response.status_code == 200
        assert response_dict['user']['username'] == username
        assert len(users) == starting_user_count + 1

    def test_create_new_user_with_invalid_usergroups(self):
        with db.session.no_autoflush:
            starting_user_count = len(User.query.all())

            username = 'test1'
            usergroup_ids = [99999, 888888]
            response = self.post_to_edit_user(username=username, usergroup_ids=usergroup_ids)
            response_dict = json.loads(response.data)
            users = User.query.all()

        assert response.status_code == 400
        assert len(users) == starting_user_count

    def test_edit_user_with_valid_data(self):
        starting_user_count = len(User.query.all())

        user_id = '42'
        self.create_user(username='edit1', email='edit1@example.com', role='viewer', user_id=user_id)

        response = self.patch_to_edit_user(username='edit2', email='edit2@gmail.com', role='writer', user_id=user_id)
        edited_user = User.query.filter(User.id == user_id).first()
        edited_user_dict = edited_user.get_dict()

        number_of_users = len(User.query.all())

        assert response.status_code == 200
        assert edited_user_dict['username'] == 'edit2'
        assert number_of_users == starting_user_count + 1

    def test_edit_user_with_invalid_id(self):
        starting_user_count = len(User.query.all())

        response = self.patch_to_edit_user(username='test1', user_id=9999999)
        response_dict = json.loads(response.data)
        number_of_users = len(User.query.all())

        assert response.status_code == 400
        assert response_dict['msg'] == 'Provided user_id not found.'
        assert number_of_users == starting_user_count

    def test_edit_user_with_valid_usergroups(self):
        starting_user_count = len(User.query.all())

        user_id = 42
        self.create_user(username='edit1', email='edit1@example.com', role='viewer', user_id=user_id)
        ug1 = self.create_usergroup(label='ug101', usergroup_id=101)
        ug2 = self.create_usergroup(label='ug102', usergroup_id=102)

        response = self.patch_to_edit_user(username='edit2', email='edit2@gmail.com', role='writer', user_id=user_id
                                           , usergroup_ids=[101, 102])
        edited_user = User.query.filter(User.id == user_id).first()
        edited_user_usergroup_ids = edited_user.get_usergroup_ids()

        number_of_users = len(User.query.all())

        assert response.status_code == 200
        assert 101 in edited_user_usergroup_ids
        assert number_of_users == starting_user_count + 1

    def test_edit_user_with_invalid_usergroups(self):
        user_id = 42
        self.create_user(username='edit1', email='edit1@example.com', role='viewer', user_id=user_id)

        usergroup_ids = [99999, 888888]
        response = self.patch_to_edit_user(user_id=user_id, usergroup_ids=usergroup_ids)
        response_dict = json.loads(response.data)
        edited_user = User.query.filter(User.id == user_id).first()
        edited_usergroup_ids = edited_user.get_usergroup_ids()

        assert response.status_code == 400
        assert usergroup_ids[0] not in edited_usergroup_ids

    def test_edit_user_cant_remove_personal_usergroup(self):
        user_id = 42
        username = 'edit_1'
        self.create_user(username=username, user_id=user_id)

        usergroup_ids = [99]

        self.create_usergroup(label='test_ug', usergroup_id=usergroup_ids[0])
        response = self.patch_to_edit_user(user_id=user_id, usergroup_ids=usergroup_ids)
        response_dict = json.loads(response.data)

        user = User.query.filter(User.id == user_id).first()
        usergroups = user.get_dicts_from_usergroups()
        personal_usergroup = \
            [usergroup for usergroup in usergroups if usergroup['label'] == 'personal_{}'.format(username)]

        assert personal_usergroup

    def test_non_admin_can_edit_self(self):
        username = 'writer'
        non_admin = User.query.filter(User.username == username).first()
        user_id = non_admin.id
        new_username = 'The Best Writer'

        response = self.patch_to_edit_user(user_id=user_id, username=new_username, token_type=username, role='')
        response_dict = json.loads(response.data)
        user = helpers.get_record_from_id(User, user_id)

        assert response.status_code == 200
        assert user.username == new_username.lower()

    def test_non_admin_cannot_change_own_role(self):
        username = 'writer'
        non_admin = User.query.filter(User.username == username).first()
        user_id = non_admin.id
        new_role = 'admin'

        response = self.patch_to_edit_user(user_id=user_id, role=new_role, token_type=username)
        response_dict = json.loads(response.data)

        assert response.status_code == 401

    def test_create_user_creates_personal_usergroup(self):
        with db.session.no_autoflush:
            username = 'new_user'
            response = self.post_to_edit_user(username=username)
            response_dict = json.loads(response.data)

            user = User.query.filter(User.username == username).first()
            usergroups = user.get_dicts_from_usergroups()
            usergroup_ids = user.get_usergroup_ids()
            personal_usergroup = [usergroup for usergroup in usergroups if
                                  usergroup['label'] == 'personal_{}'.format(username)]

        assert personal_usergroup

    def test_post_to_delete_user_with_valid_data(self):
        user_id = 42
        username = 'archibald'
        self.create_user(user_id=user_id, username=username)
        personal_usergroup = Usergroup.query.filter(Usergroup.label == 'personal_{}'.format(username)).first()
        usergroup_id = personal_usergroup.id

        response = self.post_to_delete_user(user_id=user_id)
        response_dict = json.loads(response.data)
        user = helpers.get_record_from_id(User, user_id)
        usergroup = helpers.get_record_from_id(Usergroup, usergroup_id)

        assert not user
        assert not usergroup


    def test_post_to_delete_user_with_bad_user_id(self):
        bad_user_id = 9999999

        response = self.post_to_delete_user(user_id=bad_user_id)
        response_dict = json.loads(response.data)

        assert response.status_code == 400

    def test_post_to_delete_user_without_admin_privileges(self):
        user_id = 42
        username = 'archibald'
        self.create_user(user_id=user_id, username=username)

        response = self.post_to_delete_user(user_id=user_id, token_type='writer')
        response_dict = json.loads(response.data)
        user = helpers.get_record_from_id(User, user_id)

        assert user
        assert response.status_code == 401

    def test_user_cannot_delete_self(self):
        admin_user = User.query.filter(User.username == 'admin').first()
        admin_user_id = admin_user.id

        response = self.post_to_delete_user(user_id=admin_user_id, token_type='admin')
        response_dict = json.loads(response.data)
        user = helpers.get_record_from_id(User, admin_user_id)

        assert user
        assert response.status_code == 401

    def test_admin_can_make_user_inactive(self):
        user_id = 42
        self.create_user(user_id=user_id)

        response = self.patch_to_edit_user(user_id=user_id, token_type='admin', is_active=False)
        user = helpers.get_record_from_id(User, user_id)

        assert response.status_code == 200
        assert user.is_active is False

    def test_only_admin_make_other_users_inactive(self):
        user_id = 42
        self.create_user(user_id=user_id)

        response = self.patch_to_edit_user(user_id=user_id, token_type='writer', is_active=False)
        user = helpers.get_record_from_id(User, user_id)

        assert response.status_code == 401
        assert user.is_active is True

    def test_only_admin_can_get_all_users(self):
        response = self.get_to_get_all_users(token_type='writer')

        assert response.status_code == 401

    def test_get_all_users_includes_all_users(self):
        all_users_count = len(User.query.all())

        response = self.get_to_get_all_users()
        response_dict = json.loads(response.data)

        response_count = len(response_dict['users'])

        assert all_users_count == response_count
