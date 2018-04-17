from flask import Flask
from flask_testing import TestCase
from sqlalchemy import exc
from backend.test import test_utils
from backend.app import db, app
from backend.app import connection_manager as cm


class ConnectionManagerTest(TestCase):

    def create_app(self):
        app = Flask(__name__)
        app.config.from_object(test_utils.Config())
        db.init_app(app)
        return app

    def setUp(self):
        self.client = app.test_client()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def create_db_with_test_data(self):
        conn = test_utils.create_connection(label='test_conn', db_type='sqlite', host='/tmp')
        connection = cm.create_connection(conn)
        connection.execute('DROP TABLE IF EXISTS "TABLE1"')
        connection.execute('CREATE TABLE "TABLE1" ('
                           'id INTEGER NOT NULL,'
                           'name VARCHAR, '
                           'PRIMARY KEY (id));')

        connection.execute('INSERT INTO "TABLE1" '
                           '(id, name) '
                           'VALUES (1,"raw1"), (2,"raw2"), (3,"raw3"), (4,"raw4")')
        return conn

    def test_create_engine_with_valid_input(self):
        conn = test_utils.create_connection(label='test_conn', db_type='sqlite', host='/tmp')
        engine = cm.create_engine(conn)

        assert engine

    def test_create_connection_with_valid_input(self):
        conn = test_utils.create_connection(label='test_conn', db_type='sqlite', host='/tmp')
        connection = cm.create_connection(conn)

        assert connection

    def test_create_connection_with_invalid_input(self):
        conn = test_utils.create_connection(label='test_conn', db_type='sqlite', host='bananas')

        try:
            connection = cm.create_connection(conn)
            assert not connection
        except exc.ArgumentError:
            pass
        except:
            assert False

    def test_get_db_metadata(self):
        conn = self.create_db_with_test_data()
        meta = cm.get_db_metadata(conn)
        assert isinstance(meta, list)

    def test_execute_select_statement_with_valid_input(self):
        conn = self.create_db_with_test_data()
        sql = 'select * from TABLE1'
        result = cm.execute_select_statement(conn=conn, raw_sql=sql)
        assert isinstance(result, list)

    def test_execute_select_statement_with_unknown_table(self):
        conn = self.create_db_with_test_data()
        sql = 'select * from TABLE12'
        try:
            result = cm.execute_select_statement(conn=conn, raw_sql=sql)
            assert not isinstance(result, list)
        except exc.OperationalError:
            pass
        except:
            assert False

    def test_execute_select_statement_with_invalid_input(self):
        conn = self.create_db_with_test_data()
        sql = 'delete all the tables'
        try:
            result = cm.execute_select_statement(conn=conn, raw_sql=sql)
            assert not result
        except AssertionError:
            pass
        except:
            assert False

    def test_execute_query_object_with_valid_input(self):
        conn = self.create_db_with_test_data()
        sql = 'select * from TABLE1'
        query = test_utils.create_query(label='testQ', raw_sql=sql)
        result = cm.execute_query_object(conn=conn, query=query)
        assert isinstance(result, list)

