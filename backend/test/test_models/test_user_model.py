from flask import Flask
from flask_testing import TestCase
from sqlalchemy import exc
from backend.app.models import (
    User, Usergroup, Connection, SqlQuery, Chart, Report,
    Contact, connection_perms
)
from backend.app import db
from backend.test.test_utils import TestUtils, Config


class UserModelTest(TestCase, TestUtils):

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
        user = self.create_user(username='samson', email="sseaborn@whitehouse.gov", role="admin")
        user_dict = user.get_dict()

        assert isinstance(user_dict, dict)
        assert user_dict['user_id']
        assert user_dict['username'] == 'samson'
        assert user_dict['email'] == "sseaborn@whitehouse.gov"
        assert user_dict['role'] == "admin"

    def test_usernames_are_unique(self):
        self.create_user(username='samson')
        try:
            self.create_user(username='samson')
            raise Exception('username must be unique.')
        except (exc.IntegrityError, AssertionError):
            pass

    def test_password_is_hashed(self):
        user = User()
        password = 'Password123'
        user.set_password(password)

        assert user.password_hash != password

    def test_check_password(self):
        user = User()
        password = 'Password123'
        user.set_password(password)

        assert user.check_password(password)
        assert not user.check_password('not_password')

    def test_appending_to_usergroups(self):
        usergroup1 = Usergroup(label="group1")
        user = self.create_user(username='samson')
        usergroup_length_start = len(user.usergroups)
        user.usergroups.append(usergroup1)
        usergroup_length_end = len(user.usergroups)

        assert usergroup1 in user.usergroups
        assert usergroup_length_end == usergroup_length_start + 1

    def test_get_usergroup_ids(self):
        user = self.create_user()
        usergroup_ids = user.get_usergroup_ids()

        assert isinstance(usergroup_ids, list)
        assert isinstance(usergroup_ids[0], int)

    def test_get_authorized_ids(self):
        connection = Connection(label='con1')
        usergroup1 = Usergroup(label='group1')
        usergroup2 = Usergroup(label='group2')
        usergroup3 = Usergroup(label='group3')
        user = self.create_user(username='samson')
        connection.usergroups.append(usergroup1)
        connection.usergroups.append(usergroup2)
        user.usergroups.append(usergroup2)
        user.usergroups.append(usergroup3)
        db.session.add(connection)
        db.session.add(usergroup1)
        db.session.add(usergroup2)
        db.session.add(usergroup3)
        db.session.commit()

        # connection_perms is joining table between Connection and Usergroup
        authorized_ids = user.get_authorized_ids(connection_perms)

        assert len(authorized_ids) == 1
        assert isinstance(authorized_ids[0], int)

    def test_get_dicts_from_usergroups(self):
        user = self.create_user(username='samson')
        starting_usergroups_count = len(user.get_dicts_from_usergroups())

        usergroup2 = self.create_usergroup(label='group2')
        usergroup3 = self.create_usergroup(label='group3')
        user.usergroups.append(usergroup2)
        user.usergroups.append(usergroup3)
        db.session.commit()

        usergroups = user.get_dicts_from_usergroups()
        ending_usergroups_count = len(usergroups)

        assert ending_usergroups_count == starting_usergroups_count + 2
        assert isinstance(usergroups[0], dict)

    def test_get_connections(self):
        usergroup1 = self.create_usergroup(label='group1')
        user = self.create_user(username='samson')
        connection1 = Connection(label='con1', creator=user)
        connection1.usergroups.append(usergroup1)
        user.usergroups.append(usergroup1)
        db.session.add(connection1)
        db.session.add(usergroup1)
        db.session.commit()

        connections = user.get_connections()

        assert len(connections) == 1
        assert connections[0]['label'] == 'con1'

    def test_get_queries(self):
        usergroup1 = self.create_usergroup(label='group1')
        user = self.create_user(username='samson')
        query1 = SqlQuery(label='query1', creator=user)
        query1.usergroups.append(usergroup1)
        user.usergroups.append(usergroup1)
        db.session.add(query1)
        db.session.commit()

        queries = user.get_queries()

        assert len(queries) == 1
        assert queries[0]['label'] == 'query1'
        assert queries[0]['creator']['username'] == 'samson'

    def test_get_charts(self):
        usergroup1 = self.create_usergroup(label='group1')
        user = self.create_user(username='samson')
        query = SqlQuery(label='q1', creator=user)
        connection = Connection(label='con1', creator=user)
        chart1 = Chart(label='chart1', creator=user, sql_query=query, chart_connection=connection)
        chart1.usergroups.append(usergroup1)
        user.usergroups.append(usergroup1)
        db.session.add(chart1)
        db.session.commit()

        charts = user.get_charts()

        assert len(charts) == 1
        assert charts[0]['label'] == 'chart1'
        assert charts[0]['creator']['username'] == 'samson'

    def test_get_reports(self):
        usergroup1 = self.create_usergroup(label='group1')
        user = self.create_user(username='samson')
        report1 = Report(label='rep1', creator=user)
        report1.usergroups.append(usergroup1)
        user.usergroups.append(usergroup1)
        db.session.add(report1)
        db.session.commit()

        reports = user.get_reports()

        assert len(reports) == 1
        assert reports[0]['label'] == 'rep1'
        assert reports[0]['creator']['username'] == 'samson'

    def test_get_contacts(self):
        user1 = self.create_user(username='samson')
        user2 = self.create_user(username='joshua')
        contact1 = Contact(first_name='bartlett', creator=user2, public=True)
        contact2 = Contact(first_name='toby', creator=user1, public=False)
        db.session.add(contact1)
        db.session.add(contact2)
        db.session.add(user1)
        db.session.add(user2)
        db.session.commit()

        contacts = user1.get_contacts()

        assert len(contacts) == 2
        assert contacts[0]['first_name'] == 'bartlett'
        assert contacts[0]['creator']['username'] == 'joshua'


if __name__ == '__main__':
    unittest.main()
