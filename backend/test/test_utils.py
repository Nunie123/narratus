import json
import datetime
from backend.app import db
from backend.app import helper_functions as helpers
from backend.app.models import User, Usergroup, Connection, SqlQuery, Chart, Report, Publication, Contact


class Config:
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    SQLALCHEMY_TRACK_MODIFICATIONS = False


def create_user_and_login(client, username='sam', password='Secret123', role='admin'):
    create_user(username=username, password=password, role=role)
    return login(username=username, password=password, role=role, client=client)


def login(client, username='sam', password='Secret123', role='admin'):
    data = dict(username=username, password=password, role=role)
    return client.post('/api/login', data=json.dumps(data), content_type='application/json')


def logout(token, client):
    return client.post('/api/logout', headers={'Authorization': 'Bearer {}'.format(token)})


def create_user(username: str = 'samson', password: str = 'Secret123', email: str = 'sseaborn@whitehouse.gov'
                , role: str = 'admin', user_id: int = None, usergroup_label: str = 'ug1'
                , is_active: bool = True) -> User:
    user = User(username=username, email=email, role=role, is_active=is_active)
    user.set_password(password)
    if user_id:
        user.id = user_id
    usergroup = Usergroup.query.filter(Usergroup.label == usergroup_label).first()
    if not usergroup:
        usergroup = create_usergroup(label=usergroup_label)
    personal_usergroup = Usergroup(label=username, personal_group=True)
    user.usergroups.append(usergroup)
    user.usergroups.append(personal_usergroup)
    db.session.add(usergroup)
    db.session.add(personal_usergroup)
    db.session.add(user)
    db.session.commit()
    return user


def create_usergroup(label: str = 'usergroup1', usergroup_id=None, personal_group: bool=False):
    usergroup = Usergroup(label=label, personal_group=personal_group)
    if usergroup_id:
        usergroup.id = usergroup_id
    db.session.add(usergroup)
    db.session.commit()
    return usergroup


def get_number_of_users():
    return len(User.query.all())


def create_connection(connection_id=None, label='con1', db_type='postgresql', host='www.example.com', port=3302
                      , username='user1', password='secret', database_name='test1', creator=None):

    connection = Connection(label=label, db_type=db_type, host=host, port=port, username=username
                            , password=password, database_name=database_name)
    if connection_id:
        connection.id = connection_id

    if creator:
        connection.creator = creator
    else:
        connection.creator = create_user(username='user_{}'.format(label))

    db.session.add(connection)
    db.session.commit()
    return connection


def create_query(query_id=None, label='test_query1', raw_sql: str='select * from flarp', creator=None):
    query = SqlQuery(label=label, raw_sql=raw_sql)

    if query_id:
        query.id = query_id

    if creator:
        query.creator = creator
    else:
        query.creator = create_user(username='user_{}'.format(label))

    db.session.add(query)
    db.session.commit()
    return query


def create_chart(creator=None, label='test_chart1', chart_id=None, type='bar', parameters='javascript stuff'
                 , sql_query: SqlQuery=None, chart_connection: Connection=None):
    chart = Chart(label=label, type=type, parameters=parameters)

    if chart_id:
        chart.id = chart_id

    if creator:
        chart.creator = creator
    else:
        chart.creator = create_user(username='user_{}'.format(label))

    if sql_query:
        chart.sql_query = sql_query
    else:
        chart.sql_query = create_query(label='query_{}'.format(label))

    if chart_connection:
        chart.chart_connection = chart_connection
    else:
        chart.chart_connection = create_connection(label='connection_{}'.format(label))

    db.session.add(chart)
    db.session.commit()
    return chart


def create_report(creator=None, label='test_report1', report_id=None, last_published=None
                  , parameters='JS stuff'):
    report = Report(label=label, parameters=parameters, last_published=last_published)

    if report_id:
        report.id = report_id

    if creator:
        report.creator = creator
    else:
        report.creator = create_user(username='user_{}'.format(label))

    db.session.add(report)
    db.session.commit()
    return report


def create_publication(type='dashboard'
                       , frequency='daily'
                       , monday=False
                       , tuesday=False
                       , wednesday=False
                       , thursday=False
                       , friday=False
                       , saturday=False
                       , sunday=False
                       , day_of_month=1
                       , pub_time=datetime.time()
                       , creator=None
                       , recipients=None
                       , publication_id=None
                       , report_label='TestReport1234'
                       ):

    publication = Publication(type=type, frequency=frequency, monday=monday, tuesday=tuesday, wednesday=wednesday
                              , thursday=thursday, friday=friday, saturday=saturday, sunday=sunday
                              , day_of_month=day_of_month, pub_time=pub_time)

    report = create_report(label=report_label)
    publication.publication_report = report

    if creator:
        publication.creator = creator
    else:
        publication.creator = report.creator

    if recipients:
        publication.recipients = recipients

    if publication_id:
        publication.id = publication_id

    db.session.add(publication)
    db.session.commit()
    return publication


def create_contact(contact_id=None, first_name='Bob', last_name='Dole'
                   , email='bdole@example.com', public=True, creator=None):
    contact = Contact(first_name=first_name, last_name=last_name, email=email, public=public)

    if contact_id:
        contact.id = contact_id

    if creator:
        contact.creator = creator
    else:
        contact.creator = create_user()

    db.session.add(contact)
    db.session.commit()
    return contact
