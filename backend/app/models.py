from datetime import datetime
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    usergroup_id = db.Column(db.Integer, db.ForeignKey('usergroup.id'))
    queries = db.relationship('Query', backref='creator', lazy='dynamic')
    charts = db.relationship('Chart', backref='creator', lazy='dynamic')
    reports = db.relationship('Report', backref='creator', lazy='dynamic')
    contacts = db.relationship('Contact', backref='creator', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)

class Usergroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)
    users = db.relationship('User', backref='usergroup', lazy='dynamic')

    def __repr__(self):
        return '<Usergroup id:{} name:{}>'.format(self.id, self.name)

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
    charts = db.relationship('Chart', backref='connection', lazy='dynamic')
    usergroups = db.relationship("Usergroup",
                    secondary=connection_perms,
                    backref="connections")

    def __repr__(self):
        return '<Connection {}'.format(self.label)

query_perms = db.Table('query_perms',
    db.Column('query_id', db.Integer, db.ForeignKey('query.id'), primary_key=True),
    db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
)

class Query(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    raw_sql = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    charts = db.relationship('Chart', backref='query', lazy='dynamic')
    usergroups = db.relationship("Usergroup",
                    secondary=query_perms,
                    backref="queries")

    def __repr__(self):
        return '<Query {}'.format(self.label)

chart_perms = db.Table('chart_perms',
    db.Column('chart_id', db.Integer, db.ForeignKey('chart.id'), primary_key=True),
    db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
)

class Chart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    type = db.Column(db.String(128))
    parameters = db.Column(db.Text)
    query_id = db.Column(db.Integer, db.ForeignKey('query.id'))
    connection_id = db.Column(db.Integer, db.ForeignKey('connection.id'))
    usergroups = db.relationship("Usergroup",
                    secondary=chart_perms,
                    backref="charts")

    def __repr__(self):
        return '<Chart {}'.format(self.label)

report_perms = db.Table('report_perms',
    db.Column('report_id', db.Integer, db.ForeignKey('report.id'), primary_key=True),
    db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
)

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(64), index=True, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    created_on = db.Column(db.DateTime, default=datetime.utcnow)
    last_published = db.Column(db.DateTime)
    parameters = db.Column(db.Text)
    publications = db.relationship('Publication', backref='report', lazy='dynamic')
    usergroups = db.relationship("Usergroup",
                    secondary=report_perms,
                    backref="reports")

    def __repr__(self):
        return '<Report {}'.format(self.label)

publication_recipients = db.Table('publication_recipients',
    db.Column('contact_id', db.Integer, db.ForeignKey('contact.id'), primary_key=True),
    db.Column('publication_id', db.Integer, db.ForeignKey('publication.id'), primary_key=True)
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
    contact_ids = db.relationship("Contact",
                    secondary=publication_recipients,
                    backref="publications")

    def __repr__(self):
        return '<Publication {} for report {}'.format(self.type, self.report_id)

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    email = db.Column(db.String(128))
    public = db.Column(db.Boolean)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), index=True)
    publication_ids = db.relationship("Publication",
                    secondary=publication_recipients,
                    backref="recipients")

    def __repr__(self):
        return '<Reicpient {}, {}'.format(self.last_name, self.first_name)
