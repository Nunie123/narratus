from datetime import datetime
import re
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import validates
from sqlalchemy import func
from backend.app import helper_functions as helpers
from backend.app import db

user_perms = db.Table('user_perms',
                      db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
                      db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True),
                      db.UniqueConstraint('user_id', 'usergroup_id', name='UC_user_id_usergroup_id'),
                      )


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.Enum('viewer', 'writer', 'admin', 'superuser', name='user_roles'), default='viewer')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    connections = db.relationship('Connection', backref='creator', lazy='dynamic')
    queries = db.relationship('SqlQuery', backref='creator', lazy='dynamic')
    charts = db.relationship('Chart', backref='creator', lazy='dynamic')
    reports = db.relationship('Report', backref='creator', lazy='dynamic')
    publications = db.relationship('Publication', backref='creator', lazy='dynamic')
    contacts = db.relationship('Contact', backref='creator', lazy='dynamic')
    usergroups = db.relationship("Usergroup", secondary=user_perms, backref="members", cascade="save-update, merge")

    @validates('username')
    def validate_username(self, key, username):
        if not username:
            raise AssertionError('No username provided')

        is_string = isinstance(username, str)
        is_unique = not User.query.filter(User.username == username).first()
        is_only_numbers_and_letters = re.match("^[a-zA-Z0-9_]+$", username)
        is_more_than_5_characters = len(username) >= 5
        is_less_than_40_characters = len(username) <= 40

        if not is_string:
            raise AssertionError('Provided username is invalid')

        if not is_unique:
            raise AssertionError('Provided username is already in use')

        if not is_only_numbers_and_letters:
            raise AssertionError('Usernames may only contain letters, numbers, and underscores')

        if not is_more_than_5_characters:
            raise AssertionError('Username must be 5 or more characters')

        if not is_less_than_40_characters:
            raise AssertionError('Usernames may only be 40 characters or less')

        return username

    @validates('email')
    def validate_email(self, key, email):
        if not email:
            raise AssertionError('No email provided')
        if not re.match("[^@]+@[^@]+\.[^@]+", email):
            raise AssertionError('Provided email is not an email address')

        return email

    @validates('role')
    def validate_role(self, key, role):
        if role not in ('viewer', 'writer', 'admin'):
            AssertionError('Provided role is not recognized')

        return role

    @validates('usergroups')
    def validate_usergroups(self, key, usergroups):
        if not isinstance(usergroups, Usergroup):
            raise AssertionError('Provided usergroup is not recognized')

        return usergroups

    def get_dict(self):
        dict_format = {
            "user_id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role,
            "usergroups": self.get_dicts_from_usergroups()

            }
        return dict_format

    def set_password(self, password):
        if not password:
            raise AssertionError('Password not provided')

        if not re.match('\d.*[A-Z]|[A-Z].*\d', password):
            raise AssertionError('Password must contain 1 capital letter and 1 number')

        if len(password) < 8 or len(password) > 50:
            raise AssertionError('Password must be between 8 and 50 characters')

        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# returns list of usergroup ids
    def get_usergroup_ids(self):
        ug_tuple_list = db.session.query(user_perms).filter(user_perms.c.user_id == self.id).all()
        return list(map(lambda tup: tup[1], ug_tuple_list))

# takes table, returns list of ids
    def get_authorized_ids(self, table):
        usergroup_ids = self.get_usergroup_ids()
        conn_tuple_list = db.session.query(table).filter(table.c.usergroup_id.in_(usergroup_ids)).all()
        return list(set(map(lambda tup: tup[1], conn_tuple_list)))

# returns list of usergroup dictionaries
    def get_dicts_from_usergroups(self):
        usergroup_ids = self.get_usergroup_ids()
        usergroup_objects_list = Usergroup.query.filter(Usergroup.id.in_(usergroup_ids)).all()
        return list(map(lambda obj: {'id': obj.id, 'label': obj.label, }, usergroup_objects_list))

# returns list of connection dictionaries
    def get_connections(self):
        connection_ids = self.get_authorized_ids(connection_perms)
        connection_objects_list = Connection.query.filter(Connection.id.in_(connection_ids)).all()
        return list(map(lambda obj: obj.get_dict(), connection_objects_list))

# returns list of query dictionaries
    def get_queries(self):
        query_ids = self.get_authorized_ids(query_perms)
        query_objects_list = SqlQuery.query.filter(SqlQuery.id.in_(query_ids)).all()
        return list(map(lambda obj: obj.get_dict(), query_objects_list))

# returns list of chart dictionaries
    def get_charts(self):
        chart_ids = self.get_authorized_ids(chart_perms)
        chart_objects_list = db.session.query(Chart).filter(Chart.id.in_(chart_ids)).all()
        return list(map(lambda obj: obj.get_dict(), chart_objects_list))

# returns list of report dictionaries
    def get_reports(self):
        report_ids = self.get_authorized_ids(report_perms)
        report_objects_list = Report.query.filter(Report.id.in_(report_ids)).all()
        return list(map(lambda obj: obj.get_dict(), report_objects_list))

# returns list of contact dictionaries
    def get_contacts(self):
        public_contacts = Contact.query.filter(Contact.public).all()
        created_contacts = Contact.query.filter(Contact.creator_user_id == self.id).all()
        return list(map(lambda obj: obj.get_dict(), public_contacts + created_contacts))

    def __repr__(self):
        return '<User {}>'.format(self.username)


class Usergroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    personal_group = db.Column(db.Boolean, default=False)

    @validates('label')
    def validate_label(self, key, label):
        if not label:
            raise AssertionError('No label provided')
        if Usergroup.query.filter(func.lower(Usergroup.label) == func.lower(label)).first():
            raise AssertionError('Provided label is already in use')

        return label

    @validates('members')
    def validate_members(self, key, members):
        if not isinstance(members, User):
            raise AssertionError('Provided member is not recognized')

        return members

    @validates('connections')
    def validate_connections(self, key, connections):
        if not isinstance(connections, Connection):
            raise AssertionError('Provided connection is not recognized')

        return connections

    @validates('queries')
    def validate_queries(self, key, queries):
        if not isinstance(queries, SqlQuery):
            raise AssertionError('Provided SQL query is not recognized')

        return queries

    @validates('charts')
    def validate_charts(self, key, charts):
        if not isinstance(charts, Chart):
            raise AssertionError('Provided chart is not recognized')

        return charts

    @validates('reports')
    def validate_reports(self, key, reports):
        if not isinstance(reports, Report):
            raise AssertionError('Provided chart is not recognized')

        return reports

    def get_members(self):
        return list(map(lambda obj: obj.get_dict(), self.members))

    def get_connections(self):
        return list(map(lambda obj: obj.get_dict(), self.connections))

    def get_queries(self):
        return list(map(lambda obj: obj.get_dict(), self.queries))

    def get_charts(self):
        return list(map(lambda obj: obj.get_dict(), self.charts))

    def get_reports(self):
        return list(map(lambda obj: obj.get_dict(), self.reports))

    def get_dict(self):
        dict_format = {
            'usergroup_id': self.id,
            'label': self.label,
            'members': self.get_members(),
            'connections': self.get_connections(),
            'queries': self.get_queries(),
            'charts': self.get_charts(),
            'reports': self.get_reports(),
            }
        return dict_format

    def __repr__(self):
        return '<Usergroup id:{} label:{}>'.format(self.id, self.label)


connection_perms = \
    db.Table('connection_perms',
             db.Column('connection_id', db.Integer, db.ForeignKey('connection.id'), primary_key=True),
             db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
             )


class Connection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True, nullable=False)
    db_type = db.Column(db.String(64))
    host = db.Column(db.String(256))
    port = db.Column(db.Integer)
    username = db.Column(db.String(128))
    password = db.Column(db.String(128))
    database_name = db.Column(db.String(256))
    charts = db.relationship('Chart', backref='chart_connection', lazy='dynamic')
    creator_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True, nullable=False)
    usergroups = db.relationship("Usergroup", secondary=connection_perms, backref="connections")

    @validates('label')
    def validate_label(self, key, label):
        if not label:
            raise AssertionError('No label provided')
        if Usergroup.query.filter(func.lower(Usergroup.label) == func.lower(label)).first():
            raise AssertionError('Provided label is already in use')

        return label

    @validates('db_type')
    def validate_db_type(self, key, db_type):
        if not db_type:
            raise AssertionError('No db_type provided')
        if not isinstance(db_type, str):
            raise AssertionError('Provided db_type not valid')

        return db_type

    @validates('host')
    def validate_host(self, key, host):
        if not host:
            raise AssertionError('No host provided')
        if not isinstance(host, str):
            raise AssertionError('Provided host not valid')

        return host

    @validates('port')
    def validate_host(self, key, port):
        if not port:
            raise AssertionError('No port provided')
        if not isinstance(port, (str, int)):
            raise AssertionError('Provided port not valid')

        return port

    @validates('username')
    def validate_username(self, key, username):
        if not username:
            raise AssertionError('No username provided')
        if not isinstance(username, str):
            raise AssertionError('Provided username not valid')

        return username

    @validates('password')
    def validate_password(self, key, password):
        if not password:
            raise AssertionError('No password provided')
        if not isinstance(password, str):
            raise AssertionError('Provided password not valid')

        return password

    @validates('database_name')
    def validate_database_name(self, key, database_name):
        if not database_name:
            raise AssertionError('No database_name provided')
        if not isinstance(database_name, str):
            raise AssertionError('Provided database name not valid')

        return database_name

    @validates('creator')
    def validate_creator(self, key, creator):
        if not isinstance(creator, User):
            raise AssertionError('Provided creator is not recognized')

        return creator

    @validates('usergroups')
    def validate_usergroups(self, key, usergroups):
        if not isinstance(usergroups, Usergroup):
            raise AssertionError('Provided usergroup is not recognized')

        return usergroups

    def get_dict(self):
        dict_format = {
            'connection_id': self.id,
            'label': self.label,
            'db_type': self.db_type,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'password': self.password,
            'db_name': self.database_name,
            'creator': self.creator.get_dict(),
            }
        return dict_format

    def get_usergroups(self):
        usergroups = helpers.get_dicts_from_usergroups(self.usergroups)
        return usergroups

    def get_authorized_users(self):
        users = helpers.get_users_from_usergroups(self.usergroups)
        return users

    def __repr__(self):
        return '<Connection label: {}>'.format(self.label)


query_perms = \
    db.Table('query_perms',
             db.Column('query_id', db.Integer, db.ForeignKey('sql_query.id'), primary_key=True),
             db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
             )


class SqlQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    raw_sql = db.Column(db.Text)
    creator_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True, nullable=False)
    charts = db.relationship('Chart', backref='sql_query', lazy='dynamic')
    usergroups = db.relationship("Usergroup", secondary=query_perms, backref="queries")

    @validates('label')
    def validate_label(self, key, label):
        if not label:
            raise AssertionError('No label provided')
        if Usergroup.query.filter(func.lower(Usergroup.label) == func.lower(label)).first():
            raise AssertionError('Provided label is already in use')

        return label

    @validates('raw_sql')
    def validate_raw_sql(self, key, raw_sql):
        if not raw_sql:
            raise AssertionError('No raw_sql provided')
        if not isinstance(raw_sql, str):
            raise AssertionError('raw_sql must be a string')

        return raw_sql

    @validates('usergroups')
    def validate_usergroups(self, key, usergroups):
        if not isinstance(usergroups, Usergroup):
            raise AssertionError('Provided usergroup is not recognized')

        return usergroups

    def get_dict(self):
        dict_format = {
            'query_id': self.id,
            'label': self.label,
            'raw_sql': self.raw_sql,
            'creator': self.creator.get_dict(),
        }
        return dict_format

    def get_usergroups(self):
        usergroups = helpers.get_dicts_from_usergroups(self.usergroups)
        return usergroups

    def get_authorized_users(self):
        users = dict(users=helpers.get_users_from_usergroups(self.usergroups))
        return users

    def __repr__(self):
        return '<SqlQuery {}:{}'.format(self.id, self.label)


chart_perms = db.Table('chart_perms',
                       db.Column('chart_id', db.Integer, db.ForeignKey('chart.id'), primary_key=True),
                       db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
                       )


class Chart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    type = db.Column(db.String(128))
    parameters = db.Column(db.Text)
    creator_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    sql_query_id = db.Column(db.Integer, db.ForeignKey('sql_query.id'))
    connection_id = db.Column(db.Integer, db.ForeignKey('connection.id'))
    usergroups = db.relationship("Usergroup", secondary=chart_perms, backref="charts")

    @validates('label')
    def validate_label(self, key, label):
        if not label:
            raise AssertionError('No label provided')
        if Usergroup.query.filter(func.lower(Usergroup.label) == func.lower(label)).first():
            raise AssertionError('Provided label is already in use')

        return label

    @validates('type')
    def validate_raw_sql(self, key, type):
        if not type:
            raise AssertionError('No chart_type provided')
        if not isinstance(type, str):
            raise AssertionError('chart_type must be a string')

        return type

    @validates('parameters')
    def validate_parameters(self, key, parameters):
        if not parameters:
            raise AssertionError('No parameters provided')
        if not isinstance(parameters, str):
            raise AssertionError('Provided parameters is wrong data type')

        return parameters

    @validates('sql_query_id')
    def validate_sql_query_id(self, key, sql_query_id):
        if not sql_query_id:
            raise AssertionError('sql_query_id not provided')
        if not helpers.get_record_from_id(SqlQuery, sql_query_id):
            raise AssertionError('sql_query_id not recognized')

        return sql_query_id

    @validates('connection_id')
    def validate_connection_id(self, key, connection_id):
        if not connection_id:
            raise AssertionError('connection_id not provided')
        if not helpers.get_record_from_id(Connection, connection_id):
            raise AssertionError('connection_id not recognized')

        return connection_id

    @validates('usergroups')
    def validate_usergroups(self, key, usergroups):
        if not isinstance(usergroups, Usergroup):
            raise AssertionError('Provided usergroup is not recognized')

        return usergroups

    def get_dict(self):
        dict_format = {
            'chart_id': self.id,
            'label': self.label,
            'creator': self.creator.get_dict(),
            'type': self.type,
            'parameters': self.parameters,
            'sql_query': self.sql_query.get_dict(),
            'connection': self.chart_connection.get_dict(),
            }
        return dict_format

    def get_usergroups(self):
        usergroups = helpers.get_dicts_from_usergroups(self.usergroups)
        return usergroups

    def get_authorized_users(self):
        users = dict(users=helpers.get_users_from_usergroups(self.usergroups))
        return users

    def __repr__(self):
        return '<Chart label: {}>'.format(self.label)


report_perms = db.Table('report_perms',
                        db.Column('report_id', db.Integer, db.ForeignKey('report.id'), primary_key=True),
                        db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
                        )


class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    creator_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    last_published = db.Column(db.DateTime)
    parameters = db.Column(db.Text)
    publications = db.relationship('Publication', backref='publication_report', lazy='dynamic')
    usergroups = db.relationship("Usergroup", secondary=report_perms, backref="reports")

    @validates('label')
    def validate_label(self, key, label):
        if not label:
            raise AssertionError('No label provided')
        if Usergroup.query.filter(func.lower(Usergroup.label) == func.lower(label)).first():
            raise AssertionError('Provided label is already in use')

        return label

    @validates('parameters')
    def validate_parameters(self, key, parameters):
        if not parameters:
            raise AssertionError('No parameters provided')
        if not isinstance(parameters, str):
            raise AssertionError('Provided parameters is wrong data type')

        return parameters

    @validates('usergroups')
    def validate_usergroups(self, key, usergroups):
        if not isinstance(usergroups, Usergroup):
            raise AssertionError('Provided usergroup is not recognized')

        return usergroups

    def get_dict(self):
        dict_format = {
            'report_id': self.id,
            'label': self.label,
            'creator': self.creator.get_dict(),
            'created_on': self.created_on,
            'last_published': self.last_published,
            'parameters': self.parameters,
            'publications': self.get_publications(),
            }
        return dict_format

    def get_usergroups(self):
        usergroups = helpers.get_dicts_from_usergroups(self.usergroups)
        return usergroups

    def get_authorized_users(self):
        users = dict(users=helpers.get_users_from_usergroups(self.usergroups))
        return users

    def get_publications(self):
        return list(map(lambda obj: obj.get_dict(), self.publications))

    def __repr__(self):
        return '<Report {}>'.format(self.label)


publication_recipients = \
    db.Table('publication_recipients',
             db.Column('contact_id', db.Integer, db.ForeignKey('contact.id'), primary_key=True),
             db.Column('publication_id', db.Integer, db.ForeignKey('publication.id'), primary_key=True)
             )


class Publication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(128))
    creator_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    frequency = db.Column(db.Enum('manual', 'days_of_week', 'day_of_month', 'daily', 'hourly', 'every_ten_min',
                                  name='pub_frequency'), default='manual')
    monday = db.Column(db.String(15))
    tuesday = db.Column(db.String(15))
    wednesday = db.Column(db.String(15))
    thursday = db.Column(db.String(15))
    friday = db.Column(db.String(15))
    saturday = db.Column(db.String(15))
    sunday = db.Column(db.String(15))
    day_of_month = db.Column(db.Integer)
    pub_time = db.Column(db.Time)
    report_id = db.Column(db.Integer, db.ForeignKey('report.id'), index=True)
    notification_or_attachment = db.Column(db.String(32))
    contact_ids = db.relationship("Contact", secondary=publication_recipients, backref="publications")

    def get_dict(self):
        dict_format = {
            'publication_id': self.id,
            'type': self.type,
            'creator': self.creator.get_dict(),
            'frequency': self.frequency,
            'monday': self.monday,
            'tuesday': self.tuesday,
            'wednesday': self.wednesday,
            'thursday': self.thursday,
            'friday': self.friday,
            'saturday': self.saturday,
            'sunday': self.sunday,
            'day_of_month': self.day_of_month,
            'publication_time': self.pub_time,
            'report_id': self.report_id,
            'notification_or_attachment': self.notification_or_attachment,
            'recipients': self.get_recipients()
            }
        return dict_format

    def get_recipients(self):
        return list(map(lambda obj: obj.get_dict(), self.contact_ids))

    def __repr__(self):
        return '<Publication {} for report {}'.format(self.type, self.report_id)


class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    email = db.Column(db.String(128))
    public = db.Column(db.Boolean)
    creator_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    publication_ids = db.relationship("Publication", secondary=publication_recipients, backref="recipients")

    def get_dict(self):
        dict_format = {
            'contact_id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'public': self.public,
            'creator': self.creator.get_dict(),
            }
        return dict_format

    def __repr__(self):
        return '<Recipient {}, {}'.format(self.last_name, self.first_name)


class TokenBlacklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False)

    def __repr__(self):
        return '<Blacklist jti: {}'.format(self.jti)
