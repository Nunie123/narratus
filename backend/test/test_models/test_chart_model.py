from flask import Flask
from flask_testing import TestCase
from backend.app.models import Connection, SqlQuery, Chart
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
        user = self.create_user(username='samson')
        query = SqlQuery(label='q1', creator=user)
        connection = Connection(label='con1', creator=user)
        db.session.add(connection)
        chart = Chart(label='chart1', creator=user, sql_query=query, chart_connection=connection)
        db.session.add(query)
        db.session.add(chart)
        db.session.commit()

        chart_dict = chart.get_dict()

        assert isinstance(chart_dict, dict)
        assert chart_dict['chart_id']
        assert chart_dict['label'] == "chart1"
        assert chart_dict['creator']['username'] == 'samson'
        assert chart_dict['sql_query']['label'] == 'q1'
        assert chart_dict['connection']['label'] == 'con1'
