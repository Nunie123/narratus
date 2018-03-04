from flask import Flask
from flask_testing import TestCase
from app.models import (
    User, Usergroup, Connection, SqlQuery, Chart, Report, Publication,
    Contact, TokenBlacklist, connection_perms
)
from app import db

class Config:
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class UserModelTest(TestCase):

    SQLALCHEMY_DATABASE_URI = "sqlite://"
    TESTING = True

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
        user = User(username="sam", email="sseaborn@whitehouse.gov", role="admin")
        db.session.add(user)
        db.session.commit()
        user_dict = user.get_dict()

        assert isinstance(user_dict, dict)
        assert user_dict['user_id']
        assert user_dict['username'] == "sam"
        assert user_dict['email'] == "sseaborn@whitehouse.gov"
        assert user_dict['role'] == "admin"

    def test_usernames_are_unique(self):
        user1 = User(username="sam")
        user2 = User(username="sam")
        db.session.add(user1, user2)
        db.session.commit()

        users = User.query.filter(User.username == "sam").all()

        assert len(users) == 1

    def test_password_is_hashed(self):
        user = User()
        password = 'not_hashed'
        user.set_password(password)

        assert user.password_hash != password

    def test_check_password(self):
        user = User()
        password = 'not_hashed'
        user.set_password(password)

        assert user.check_password(password)
        assert not user.check_password('not_password')

    def test_get_usergroup_ids(self):
        usergroup1 = Usergroup(label="group1")
        user = User(username="sam")
        user.usergroups.append(usergroup1)

        assert user.usergroups[0] == usergroup1

        usergroup2 = Usergroup(label="group2")
        user.usergroups.append(usergroup2)
        db.session.add(user)
        db.session.add(usergroup1, usergroup2)
        db.session.commit()

        assert len(user.usergroups) == 2

        usergroup_ids = user.get_usergroup_ids()

        assert len(usergroup_ids) == 2
        assert isinstance(usergroup_ids[0], int)

    def test_get_authorized_ids(self):
        connection = Connection(label='con1')
        usergroup1 = Usergroup(label='group1')
        usergroup2 = Usergroup(label='group2')
        usergroup3 = Usergroup(label='group3')
        user = User(username='sam')
        connection.usergroups.append(usergroup1)
        connection.usergroups.append(usergroup2)
        user.usergroups.append(usergroup2)
        user.usergroups.append(usergroup3)
        db.session.add(connection, usergroup1)
        db.session.add(usergroup2, usergroup3)
        db.session.add(user)
        db.session.commit()

        authorized_ids = user.get_authorized_ids(connection_perms) #connection_permsis joining table between Connection and Usergroup

        assert len(authorized_ids) == 1
        assert isinstance(authorized_ids[0], int)

    def test_get_dicts_from_usergroups(self):
        usergroup1 = Usergroup(label='group1')
        usergroup2 = Usergroup(label='group2')
        usergroup3 = Usergroup(label='group3')
        user = User(username='sam')
        user.usergroups.append(usergroup1)
        user.usergroups.append(usergroup2)
        db.session.add(user, usergroup1)
        db.session.add(usergroup2, usergroup3)
        db.session.commit()

        usergroups = user.get_dicts_from_usergroups()

        assert len(usergroups) == 2
        assert isinstance(usergroups[0], dict)
        assert usergroups[0]['label'] == 'group1'

    def test_get_connections(self):
        connection1 = Connection(label='con1')
        usergroup1 = Usergroup(label='group1')
        user = User(username='sam')
        connection1 = Connection(label='con1', creator=user)
        connection1.usergroups.append(usergroup1)
        user.usergroups.append(usergroup1)
        db.session.add(connection1)
        db.session.add(usergroup1)
        db.session.add(user)
        db.session.commit()

        connections = user.get_connections()

        assert len(connections) == 1
        assert connections[0]['label'] == 'con1'

    def test_get_queries(self):
        usergroup1 = Usergroup(label='group1')
        user = User(username='sam')
        query1 = SqlQuery(label='query1', creator=user)
        query1.usergroups.append(usergroup1)
        user.usergroups.append(usergroup1)
        db.session.add(query1)
        db.session.add(usergroup1)
        db.session.add(user)
        db.session.commit()

        queries = user.get_queries()

        assert len(queries) == 1
        assert queries[0]['label'] == 'query1'
        assert queries[0]['creator']['username'] == 'sam'

    def test_get_charts(self):
        usergroup1 = Usergroup(label='group1')
        user = User(username='sam')
        query = SqlQuery(label='q1', creator=user)
        connection = Connection(label='con1', creator=user)
        chart1 = Chart(label='chart1', creator=user, sql_query=query, chart_connection=connection)
        chart1.usergroups.append(usergroup1)
        user.usergroups.append(usergroup1)
        db.session.add(chart1)
        db.session.add(usergroup1)
        db.session.add(user)
        db.session.commit()

        charts = user.get_charts()

        assert len(charts) == 1
        assert charts[0]['label'] == 'chart1'
        assert charts[0]['creator']['username'] == 'sam'

    def test_get_reports(self):
        usergroup1 = Usergroup(label='group1')
        user = User(username='sam')
        report1 = Report(label='rep1', creator=user)
        report1.usergroups.append(usergroup1)
        user.usergroups.append(usergroup1)
        db.session.add(report1)
        db.session.add(usergroup1)
        db.session.add(user)
        db.session.commit()

        reports = user.get_reports()

        assert len(reports) == 1
        assert reports[0]['label'] == 'rep1'
        assert reports[0]['creator']['username'] == 'sam'

    def test_get_contacts(self):
        user1 = User(username='sam')
        user2 = User(username='josh')
        contact1 = Contact(first_name='bartlett', creator=user2, public=True)
        contact2 = Contact(first_name='toby', creator=user1, public=False)
        contact1 = Contact(first_name='leo', creator=user2, public=False)
        db.session.add(contact1, contact2)
        db.session.add(user1, user2)
        db.session.commit()

        contacts = user1.get_contacts()

        assert len(contacts) == 2
        assert contacts[0]['first_name'] == 'bartlett'
        assert contacts[0]['creator']['username'] == 'josh'


if __name__ == '__main__':
    unittest.main()
