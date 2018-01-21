from datetime import datetime
from app import db

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    usergroup_id = db.Column(db.Integer, db.ForeignKey('usergroup.id'))

    def __repr__(self):
        return '<User {}>'.format(self.username)

class Usergroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)

    def __repr__(self):
        return '<Usergroup {}>'.format(self.name)

class Connection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    db_type = db.Column(db.String(64))
    host = db.Column(db.String(256))
    port = db.Column(db.Integer)
    username = db.Column(db.String(128))
    password = db.Column(db.String(128))
    database_name = db.Column(db.String(256))

    def __repr__(self):
        return '<Connection {}'.format(self.label)

connection_perms = db.Table('connection_perms',
    db.Column('connection_id', db.Integer, db.ForeignKey('connection.id'), primary_key=True),
    db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
)

class Query(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    raw_sql = db.Column(db.Text)
    creator = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    usergroup_ids = db.relationship('Usergroup', backref='id', lazy='dynamic')

    def __repr__(self):
        return '<Query {}'.format(self.label)

query_perms = db.Table('query_perms',
    db.Column('query_id', db.Integer, db.ForeignKey('query.id'), primary_key=True),
    db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
)

class Chart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    creator = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    type = db.Column(db.String(128))
    parameters = db.Column(db.Text)
    query_id = db.Column(db.Integer, db.ForeignKey('query.id'))
    connection_id = db.Column(db.Integer, db.ForeignKey('connection.id'))
    report_ids = db.relationship('Dashboard', backref='id', lazy='dynamic')
    usergroup_ids = db.relationship('Usergroup', backref='id', lazy='dynamic')

    def __repr__(self):
        return '<Chart {}'.format(self.label)

chart_perms = db.Table('chart_perms',
    db.Column('chart_id', db.Integer, db.ForeignKey('chart.id'), primary_key=True),
    db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    creator = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    last_published = db.Column(db.DateTime)
    parameters = db.Column(db.Text)
    usergroup_ids = db.relationship('Usergroup', backref='id', lazy='dynamic')

    def __repr__(self):
        return '<Report {}'.format(self.label)

report_perms = db.Table('report_perms',
    db.Column('report_id', db.Integer, db.ForeignKey('report.id'), primary_key=True),
    db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
)

class Publication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(128))
    frequency = db.Column(db.String(64))
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

    def __repr__(self):
        return '<Publication {} for report {}'.format(self.type, self.report_id)

class PublicationRecipient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    email = db.Column(db.String(128))

    def __repr__(self):
        return '<Reicpient {}, {}'.format(self.last_name, self.first_name)

pub_recipient_list = db.Table('pub_recipient_list',
    db.Column('pub_recipient_id', db.Integer, db.ForeignKey('publication_recipient.id'), primary_key=True),
    db.Column('publication_id', db.Integer, db.ForeignKey('publication.id'), primary_key=True)
)
