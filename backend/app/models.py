from datetime import datetime
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

user_perms = db.Table('user_perms',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('usergroup_id', db.Integer, db.ForeignKey('usergroup.id'), primary_key=True)
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    queries = db.relationship('Query', backref='creator', lazy='dynamic')
    charts = db.relationship('Chart', backref='creator', lazy='dynamic')
    reports = db.relationship('Report', backref='creator', lazy='dynamic')
    contacts = db.relationship('Contact', backref='creator', lazy='dynamic')
    usergroups = db.relationship("Usergroup",
                    secondary=user_perms,
                    backref="users")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
# returns list of usergroup ids
    def get_usergroups(self):
        ug_tuple_list = db.session.query(user_perms).filter(user_perms.c.user_id==self.id).all()
        return list(map(lambda tup: tup[1], ug_tuple_list))

# takes table, returns list of ids
    def get_authorized_ids(self, table):
        usergroup_ids = self.get_usergroups()
        conn_tuple_list = db.session.query(table).filter(table.c.usergroup_id.in_(usergroup_ids)).all()
        return list(set(map(lambda tup: tup[1], conn_tuple_list)))

# returns list of connection dictionaries
    def get_connections(self):
        connection_ids = self.get_authorized_ids(connection_perms)
        connection_objects_list = Connection.query.filter(Connection.id.in_(connection_ids)).all()
        return list(map(lambda obj: {'label': obj.label,
                                    'db_type': obj.db_type,
                                    'host': obj.host,
                                    'port': obj.port,
                                    'username': obj.username,
                                    'password': obj.password,
                                    'db_name': obj.database_name,
                                    }, connection_objects_list))

# returns list of query dictionaries
    def get_queries(self):
        query_ids = self.get_authorized_ids(query_perms)
        query_objects_list = Query.query.filter(Query.id.in_(query_ids)).all()
        return list(map(lambda obj: {'label': obj.label,
                                    'raw_sql': obj.raw_sql,
                                    'creator_id': obj.user_id,
                                    }, query_objects_list))

# returns list of chart dictionaries
    def get_charts(self):
        chart_ids = self.get_authorized_ids(chart_perms)
        chart_objects_list = Chart.query.filter(Chart.id.in_(chart_ids)).all()
        return list(map(lambda obj: {'label': obj.label,
                                    'creator_id': obj.user_id,
                                    'type':obj.type,
                                    'parameters':obj.parameters,
                                    'query_id':obj.query_id,
                                    'connection_id':obj.connection_id,
                                    }, chart_objects_list))

# returns list of report dictionaries
    def get_reports(self):
        report_ids = self.get_authorized_ids(report_perms)
        report_objects_list = Report.query.filter(Report.id.in_(report_ids)).all()
        return list(map(lambda obj: {'label': obj.label,
                                    'creator_id': obj.user_id,
                                    'created_on':obj.created_on,
                                    'last_published':obj.last_published,
                                    'parameters':obj.parameters,
                                    'publications':obj.get_publications(),
                                    }, report_objects_list))

# returns list of contact dictionaries
    def get_contacts(self):
        public_contacts = Contact.query.filter(Contact.public==True).all()
        created_contacts = Contact.query.filter(Contact.user_id==self).all()
        report_ids = self.get_authorized_ids(report_perms)
        reports = Report.query.filter(Report.id.in_(report_ids)).all()
        report_publications = list(set(reduce(lambda x,y: x.publications + y.publications, reports)))
        report_contacts = list(set(reduce(lambda x,y: x.contact_ids + y.contact_ids, report_publications)))
        return list(map(lambda obj: {'first_name': obj.first_name,
                                    'last_name': obj.last_name,
                                    'email':obj.email,
                                    'public':obj.public,
                                    'creator_id':obj.user.id,
                                    }, public_contacts + created_contacts + report_contacts))


    def __repr__(self):
        return '<User {}>'.format(self.username)

class Usergroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), index=True, unique=True)

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

    def get_publications(self):
        return list(map(lambda obj: {'type': obj.type,
                                    'frequency': obj.frequency,
                                    'monday':obj.monday,
                                    'tuesday':obj.tuesday,
                                    'wednesday':obj.wednesday,
                                    'thursday':obj.thursday,
                                    'friday':obj.friday,
                                    'saturday':obj.saturday,
                                    'sunday':obj.sunday,
                                    'day_of_month':obj.day_of_month,
                                    'publication_time':obj.pub_time,
                                    'report_id':obj.report_id,
                                    'notification_or_attachment':obj.notification_or_attachment,
                                    'recipients':obj.get_recipients()
                                    }, self.publications))

    def __repr__(self):
        return '<Report {}>'.format(self.label)

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

    def get_recipients(self):
        return list(map(lambda obj: {'first_name': obj.first_name,
                                    'last_name': obj.last_name,
                                    'email':obj.email,
                                    'public':obj.public,
                                    'creator_id':obj.user.id,
                                    }, self.contact_ids))

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
