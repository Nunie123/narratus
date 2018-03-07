from datetime import datetime
import re
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy.orm import validates
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
    connections = db.relationship('Connection', backref='creator', lazy='dynamic')
    queries = db.relationship('SqlQuery', backref='creator', lazy='dynamic')
    charts = db.relationship('Chart', backref='creator', lazy='dynamic')
    reports = db.relationship('Report', backref='creator', lazy='dynamic')
    publications = db.relationship('Publication', backref='creator', lazy='dynamic')
    contacts = db.relationship('Contact', backref='creator', lazy='dynamic')
    usergroups = db.relationship("Usergroup", secondary=user_perms, backref="usergroup_users")

    @validates('username')
    def validate_username(self, key, username):
        if not username:
            raise AssertionError('No username provided')

        is_string = isinstance(username, str)
        is_unique = not User.query.filter(User.username == username).first()
        # is_only_numbers_and_letters = re.match("^[a-zA-Z0-9]+$", username)
        is_more_than_5_characters = len(username) >= 5
        is_less_than_20_characters = len(username) <= 20

        if not is_string:
            raise AssertionError('Provided username is invalid')

        if not is_unique:
            raise AssertionError('Provided username is already in use')

        # if not is_only_numbers_and_letters:
        #     raise AssertionError('Usernames may only contain letters and numbers')

        if not is_more_than_5_characters:
            raise AssertionError('Username must be 5 or more characters')

        if not is_less_than_20_characters:
            raise AssertionError('Usernames may only be 20 characters or less')

        return username

    @validates('email')
    def validate_email(self, key, email):
        if not email:
            raise AssertionError('No email provided')
        if not re.match("[^@]+@[^@]+\.[^@]+", email):
            raise AssertionError('Provided email is not an email address')

        return email

    @validates('role')
    def validate_email(self, key, role):
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
            "role": self.role
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
        ug_tuple_list = db.session.query(user_perms).filter(user_perms.c.user_id==self.id).all()
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
        return list(map(lambda obj: {'id': obj.id,
                                    'label': obj.label,
                                    }, usergroup_objects_list))

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
        public_contacts = Contact.query.filter(Contact.public==True).all()
        created_contacts = Contact.query.filter(Contact.creator_user_id==self.id).all()
        return list(map(lambda obj: obj.get_dict(), public_contacts + created_contacts))

    def __repr__(self):
        return '<User {}>'.format(self.username)


class Usergroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    members = db.relationship("User", secondary=user_perms, backref="user_usergroups")

# returns list or users associated with usergroup
    def get_members(self):
        return list(map(lambda obj: obj.get_dict(), self.members))

    def get_dict(self):
        dict_format = {
            'usergroup_id': self.id,
            'label': self.label,
            'members': self.get_members(),
            }
        return dict_format

    def __repr__(self):
        return '<Usergroup id:{} label:{}>'.format(self.id, self.label)


connection_perms = db.Table('connection_perms',
    db.Column('connection_id', db.Integer, db.ForeignKey('connection.id'), primary_key=True),
    db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
)

class Connection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    db_type = db.Column(db.String(64))
    host = db.Column(db.String(256))
    port = db.Column(db.Integer)
    username = db.Column(db.String(128))
    password = db.Column(db.String(128))
    database_name = db.Column(db.String(256))
    charts = db.relationship('Chart', backref='chart_connection', lazy='dynamic')
    creator_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    usergroups = db.relationship("Usergroup",
                    secondary=connection_perms,
                    backref="connections")

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
            'usergroups': helpers.get_dicts_from_usergroups(self.usergroups),
            'authorized_users': helpers.get_users_from_usergroups(self.usergroups),
            }
        return dict_format

    def __repr__(self):
        return '<Connection label: {}>'.format(self.label)


query_perms = db.Table('query_perms',
    db.Column('query_id', db.Integer, db.ForeignKey('sql_query.id'), primary_key=True),
    db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
)


class SqlQuery(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    raw_sql = db.Column(db.Text)
    creator_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    charts = db.relationship('Chart', backref='sql_query', lazy='dynamic')
    usergroups = db.relationship("Usergroup",
                    secondary=query_perms,
                    backref="queries")

    def get_dict(self):
        dict_format = {
            'query_id': self.id,
            'label': self.label,
            'raw_sql': self.raw_sql,
            'creator': self.creator.get_dict(),
            'usergroups': helpers.get_dicts_from_usergroups(self.usergroups),
            'authorized_users': helpers.get_users_from_usergroups(self.usergroups),
        }
        return dict_format

    def __repr__(self):
        return '<SqlQuery {}'.format(self.label)

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
    usergroups = db.relationship("Usergroup",
                    secondary=chart_perms,
                    backref="charts")

    def get_dict(self):
        dict_format =   {
            'chart_id': self.id,
            'label': self.label,
            'creator': self.creator.get_dict(),
            'type': self.type,
            'parameters': self.parameters,
            'sql_query': self.sql_query.get_dict(),
            'connection': self.chart_connection.get_dict(),
            'usergroups': helpers.get_dicts_from_usergroups(self.usergroups),
            'authorized_users': helpers.get_users_from_usergroups(self.usergroups),
            }
        return dict_format

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
    usergroups = db.relationship("Usergroup",
                    secondary=report_perms,
                    backref="reports")

    def get_dict(self):
        dict_format = {
            'report_id': self.id,
            'label': self.label,
            'creator': self.creator.get_dict(),
            'created_on': self.created_on,
            'last_published':self.last_published,
            'parameters':self.parameters,
            'publications':self.get_publications(),
            'usergroups': helpers.get_dicts_from_usergroups(self.usergroups),
            'authorized_users': helpers.get_users_from_usergroups(self.usergroups),
            }
        return dict_format

    def get_publications(self):
        return list(map(lambda obj: obj.get_dict(), self.publications))

    def __repr__(self):
        return '<Report {}>'.format(self.label)

publication_recipients = db.Table('publication_recipients',
    db.Column('contact_id', db.Integer, db.ForeignKey('contact.id'), primary_key=True),
    db.Column('publication_id', db.Integer, db.ForeignKey('publication.id'), primary_key=True)
)

class Publication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(128))
    creator_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    frequency = db.Column(db.Enum('manual', 'days_of_week', 'day_of_month', 'daily', 'hourly', 'every_ten_min', name='pub_frequency'), default='manual')
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
    contact_ids = db.relationship("Contact",
                    secondary=publication_recipients,
                    backref="publications")

    def get_dict(self):
        dict_format = {
            'publication_id': self.id,
            'type': self.type,
            'creator': self.creator.get_dict(),
            'frequency': self.frequency,
            'monday':self.monday,
            'tuesday':self.tuesday,
            'wednesday':self.wednesday,
            'thursday':self.thursday,
            'friday':self.friday,
            'saturday':self.saturday,
            'sunday':self.sunday,
            'day_of_month':self.day_of_month,
            'publication_time':self.pub_time,
            'report_id':self.report_id,
            'notification_or_attachment':self.notification_or_attachment,
            'recipients':self.get_recipients()
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
    publication_ids = db.relationship("Publication",
                    secondary=publication_recipients,
                    backref="recipients")

    def get_dict(self):
        dict_format = {
            'contact_id': self.id,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email':self.email,
            'public':self.public,
            'creator':self.creator.get_dict(),
            }
        return dict_format

    def __repr__(self):
        return '<Reicpient {}, {}'.format(self.last_name, self.first_name)

class TokenBlacklist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False)

    def __repr__(self):
        return '<Blacklist jti: {}'.format(self.jti)
