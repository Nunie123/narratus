import sqlalchemy
from sqlalchemy import exc
from sqlalchemy.engine import reflection


def create_engine(conn):
    if conn.db_type.lower() == 'postgresql':
        db_type = 'postgresql'
    elif conn.db_type.lower() == 'mysql':
        db_type = 'mysql'
    elif conn.db_type.lower() == 'oracle':
        db_type = 'oracle'
    elif conn.db_type.lower() == 'sqlserver':
        db_type = 'mssql+pyodbc'
    elif conn.db_type.lower() == 'sqlite':
        db_type = 'sqlite'
    else:
        raise AssertionError('db_type not recognized')

    try:
        if db_type == 'sqlite':
            conn_string = f'sqlite://{conn.host}'
        else:
            conn_string = f'{db_type}://{conn.username}:{conn.password}@{conn.host}:{conn.port}/{conn.database_name}'
        engine = sqlalchemy.create_engine(conn_string)
        return engine
    except exc.ArgumentError as e:
        raise e


def create_connection(conn):
    engine = create_engine(conn)
    connection = engine.connect()
    return connection


def test_connection(conn):
    try:
        create_connection(conn)
        return True
    except:
        return False


def get_db_metadata(conn):
    engine = create_engine(conn)
    inspector = reflection.Inspector.from_engine(engine)
    schemas = inspector.get_schema_names()
    metadata = []
    for schema in schemas:
        table_names = inspector.get_table_names(schema=schema)

        tables = []
        for table_name in table_names:
            columns = inspector.get_columns(table_name=table_name)
            tables.append({table_name: columns})
        metadata.append({schema: tables})
    return metadata


def execute_select_statement(conn, raw_sql):
    if raw_sql.split()[0].lower() != 'select':
        raise AssertionError('SQL must begin with "select"')

    sql_text = sqlalchemy.sql.text(raw_sql)

    connection = create_connection(conn)
    trans = connection.begin()

    raw_result = connection.execute(sql_text)
    formatted_result = [dict(row) for row in raw_result]

    trans.rollback()
    connection.close()

    return formatted_result


def execute_query_object(conn, query):
    return execute_select_statement(conn=conn, raw_sql=query.raw_sql)
