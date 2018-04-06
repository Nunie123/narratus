from backend.app import models
from backend.app import db


# takes list of usergroup objects, returns list of authorized user ids
def get_users_from_usergroups(usergroups):
    users_list_of_lists = list(map(lambda obj: obj.get_members(), usergroups))
    users = []
    list(map(users.extend, users_list_of_lists))   # this flattens the list of lists
    unique_users = list({user['user_id']: user for user in users}.values())
    return unique_users


# takes list of usergroup objects, returns list of usergroup dictionaries
def get_dicts_from_usergroups(usergroups):
    usergroup_list = list(map(lambda obj: obj.get_dict(), usergroups))
    return usergroup_list


def get_record_from_id(model, model_id):
    return model.query.filter(model.id == model_id).first()


def get_user_from_username(username):
    return models.User.query.filter(models.User.username == username).first()


def any_args_are_truthy(*args):
    for arg in args:
        if arg:
            return True
    return False


def requester_has_admin_privileges(requester):
    return requester['role'] in ['admin', 'superuser']


def requester_has_write_privileges(requester):
    return requester['role'] in ['writer', 'admin', 'superuser']


def create_user_from_dict(user_dict):
    user = models.User(username=user_dict.get('username', '').lower()
                       , role=user_dict.get('role', None)
                       , is_active=user_dict.get('is_active', None)
                       , email=user_dict.get('email', '').lower()
                       )

    user.set_password(user_dict['password'])
    for usergroup_id in user_dict['usergroup_ids']:
        usergroup = get_record_from_id(models.Usergroup, usergroup_id)
        user.usergroups.append(usergroup)

    usergroup = create_personal_usergroup_from_dict(user_dict)
    user.usergroups.append(usergroup)

    db.session.add(user)
    db.session.commit()
    return user


def create_personal_usergroup_from_dict(user_dict):
    usergroup_label = user_dict['username']
    usergroup = models.Usergroup(label=usergroup_label, personal_group=True)
    db.session.add(usergroup)
    db.session.commit()

    return usergroup


def edit_user_from_dict(user_dict):
    user = get_record_from_id(models.User, user_dict['user_id'])
    personal_usergroup = user.get_personal_usergroup()

    if user_dict.get('username'):
        user.username = user_dict.get('username', '').lower()
        personal_usergroup.label = user_dict.get('username', '').lower()

    if user_dict.get('password'):
        user.set_password(user_dict['password'])

    if user_dict.get('is_active') is not None:
        user.is_active = user_dict.get('is_active')

    if user_dict.get('email'):
        user.email = user_dict.get('email', '').lower()

    usergroup_ids = user_dict.get('usergroup_ids', [])
    if usergroup_ids:
        user.usergroups = []
        for usergroup_id in usergroup_ids:
            usergroup = get_record_from_id(models.Usergroup, usergroup_id)
            user.usergroups.append(usergroup)
        if personal_usergroup not in user.usergroups:
            user.usergroups.append(personal_usergroup)

    db.session.commit()
    return user


def create_usergroup_from_dict(usergroup_dict):
    usergroup = models.Usergroup(label=usergroup_dict.get('label').lower())

    for member_id in usergroup_dict.get('member_ids', []):
        member = get_record_from_id(models.User, member_id)
        usergroup.members.append(member)
        
    for connection_id in usergroup_dict.get('connection_ids', []):
        connection = get_record_from_id(models.Connection, connection_id)
        usergroup.connections.append(connection)
        
    for query_id in usergroup_dict.get('query_ids', []):
        query = get_record_from_id(models.SqlQuery, query_id)
        usergroup.queries.append(query)
        
    for chart_id in usergroup_dict.get('chart_ids', []):
        chart = get_record_from_id(models.Chart, chart_id)
        usergroup.charts.append(chart)
        
    for report_id in usergroup_dict.get('report_ids', []):
        report = get_record_from_id(models.Report, report_id)
        usergroup.reports.append(report)

    db.session.add(usergroup)
    db.session.commit()
    return usergroup


def edit_usergroup_from_dict(usergroup_dict):
    usergroup = get_record_from_id(models.Usergroup, usergroup_dict['usergroup_id'])
    
    if usergroup.personal_group:
        raise AssertionError('personal usergroups may not be edited')

    if usergroup_dict.get('label'):
        usergroup.label = usergroup_dict.get('label', '')
            
    member_ids = usergroup_dict.get('member_ids')
    if member_ids:
        usergroup.members = []
        for member_id in member_ids:
            member = get_record_from_id(models.User, member_id)
            usergroup.members.append(member)

    connection_ids = usergroup_dict.get('connection_ids')
    if connection_ids:
        usergroup.connections = []
        for connection_id in connection_ids:
            connection = get_record_from_id(models.Connection, connection_id)
            usergroup.connections.append(connection)

    query_ids = usergroup_dict.get('query_ids')
    if query_ids:
        usergroup.queries = []
        for query_id in query_ids:
            query = get_record_from_id(models.SqlQuery, query_id)
            usergroup.queries.append(query)

    chart_ids = usergroup_dict.get('chart_ids')
    if chart_ids:
        usergroup.charts = []
        for chart_id in chart_ids:
            chart = get_record_from_id(models.Chart, chart_id)
            usergroup.charts.append(chart)

    report_ids = usergroup_dict.get('report_ids')
    if report_ids:
        usergroup.reports = []
        for report_id in report_ids:
            report = get_record_from_id(models.Report, report_id)
            usergroup.reports.append(report)

    db.session.commit()
    return usergroup


def create_connection_from_dict(connection_dict, creator_id):
    creator = get_record_from_id(models.User, creator_id)
    connection = models.Connection(label=connection_dict.get('label')
                                   , db_type=connection_dict.get('db_type')
                                   , host=connection_dict.get('host')
                                   , port=connection_dict.get('port')
                                   , username=connection_dict.get('username')
                                   , password=connection_dict.get('password')
                                   , database_name=connection_dict.get('database_name')
                                   , creator=creator
                                   )

    usergroup_ids = connection_dict.get('usergroup_ids', [])
    if usergroup_ids:
        for usergroup_id in usergroup_ids:
            usergroup = get_record_from_id(models.Usergroup, usergroup_id)
            connection.usergroups.append(usergroup)
    else:
        usergroup = creator.get_personal_usergroup()
        connection.usergroups.append(usergroup)

    db.session.add(connection)
    db.session.commit()
    return connection


def edit_connection_from_dict(connection_dict):
    connection = get_record_from_id(models.Connection, connection_dict.get('connection_id'))

    if not connection:
        raise AssertionError('connection_id not found')

    if connection_dict.get('label'):
        connection.label = connection_dict.get('label')

    if connection_dict.get('db_type'):
        connection.db_type = connection_dict.get('db_type')

    if connection_dict.get('host'):
        connection.host = connection_dict.get('host')

    if connection_dict.get('port'):
        connection.port = connection_dict.get('port')

    if connection_dict.get('username'):
        connection.username = connection_dict.get('username')

    if connection_dict.get('password'):
        connection.password = connection_dict.get('password')

    if connection_dict.get('database_name'):
        connection.database_name = connection_dict.get('database_name')

    usergroup_ids = connection_dict.get('usergroup_ids', [])
    if usergroup_ids:
        connection.usergroups = []
    for usergroup_id in usergroup_ids:
        usergroup = get_record_from_id(models.Usergroup, usergroup_id)
        connection.usergroups.append(usergroup)

    db.session.add(connection)
    db.session.commit()
    return connection


def create_query_from_dict(query_dict, creator_id):
    creator = get_record_from_id(models.User, creator_id)
    query = models.SqlQuery(label=query_dict.get('label')
                            , raw_sql=query_dict.get('raw_sql')
                            , creator=creator
                            )

    usergroup_ids = query_dict.get('usergroup_ids', [])
    if usergroup_ids:
        for usergroup_id in usergroup_ids:
            usergroup = get_record_from_id(models.Usergroup, usergroup_id)
            query.usergroups.append(usergroup)
    else:
        usergroup = creator.get_personal_usergroup()
        query.usergroups.append(usergroup)

    db.session.add(query)
    db.session.commit()
    return query


def edit_query_from_dict(query_dict):
    query = get_record_from_id(models.SqlQuery, query_dict.get('query_id'))

    if not query:
        raise AssertionError('query_id not found')

    if query_dict.get('label'):
        query.label = query_dict.get('label')

    if query_dict.get('raw_sql'):
        query.db_type = query_dict.get('raw_sql')

    usergroup_ids = query_dict.get('usergroup_ids', [])
    if usergroup_ids:
        query.usergroups = []
    for usergroup_id in usergroup_ids:
        usergroup = get_record_from_id(models.Usergroup, usergroup_id)
        query.usergroups.append(usergroup)

    db.session.commit()
    return query


def create_chart_from_dict(chart_dict, creator_id):
    chart = models.Chart(label=chart_dict.get('label')
                         , type=chart_dict.get('type')
                         , parameters=chart_dict.get('parameters')
                         , connection_id=chart_dict.get('connection_id')
                         , sql_query_id=chart_dict.get('sql_query_id')
                         , creator_user_id=creator_id
                         )

    usergroup_ids = chart_dict.get('usergroup_ids', [])
    if usergroup_ids:
        for usergroup_id in usergroup_ids:
            usergroup = get_record_from_id(models.Usergroup, usergroup_id)
            chart.usergroups.append(usergroup)
    else:
        creator = get_record_from_id(models.User, creator_id)
        usergroup = creator.get_personal_usergroup()
        chart.usergroups.append(usergroup)

    db.session.add(chart)
    db.session.commit()
    return chart


def edit_chart_from_dict(chart_dict):
    chart = get_record_from_id(models.Chart, chart_dict.get('chart_id'))

    if not chart:
        raise AssertionError('chart_id not found')

    if chart_dict.get('label'):
        chart.label = chart_dict.get('label')

    if chart_dict.get('type'):
        chart.type = chart_dict.get('type')

    if chart_dict.get('parameters'):
        chart.parameters = chart_dict.get('parameters')

    if chart_dict.get('sql_query_id'):
        chart.sql_query_id = chart_dict.get('sql_query_id')

    if chart_dict.get('connection_id'):
        chart.connection_id = chart_dict.get('connection_id')

    usergroup_ids = chart_dict.get('usergroup_ids', [])
    if usergroup_ids:
        chart.usergroups = []
    for usergroup_id in usergroup_ids:
        usergroup = get_record_from_id(models.Usergroup, usergroup_id)
        chart.usergroups.append(usergroup)

    db.session.commit()
    return chart


def create_report_from_dict(report_dict, creator_id):
    report = models.Report(label=report_dict.get('label')
                           , parameters=report_dict.get('parameters')
                           , creator_user_id=creator_id
                           )

    usergroup_ids = report_dict.get('usergroup_ids', [])
    if usergroup_ids:
        for usergroup_id in usergroup_ids:
            usergroup = get_record_from_id(models.Usergroup, usergroup_id)
            report.usergroups.append(usergroup)
    else:
        creator = get_record_from_id(models.User, creator_id)
        usergroup = creator.get_personal_usergroup()
        report.usergroups.append(usergroup)

    db.session.add(report)
    db.session.commit()
    return report


def edit_report_from_dict(report_dict):
    report = get_record_from_id(models.Report, report_dict.get('report_id'))

    if not report:
        raise AssertionError('report_id not found')

    if report_dict.get('label'):
        report.label = report_dict.get('label')

    if report_dict.get('parameters'):
        report.parameters = report_dict.get('parameters')

    usergroup_ids = report_dict.get('usergroup_ids', [])
    if usergroup_ids:
        report.usergroups = []
    for usergroup_id in usergroup_ids:
        usergroup = get_record_from_id(models.Usergroup, usergroup_id)
        report.usergroups.append(usergroup)

    db.session.commit()
    return report


def create_publication_from_dict(publication_dict, creator_id):
    publication = models.Publication(type=publication_dict.get('type')
                                     , frequency=publication_dict.get('frequency')
                                     , monday=publication_dict.get('monday')
                                     , tuesday=publication_dict.get('tuesday')
                                     , wednesday=publication_dict.get('wednesday')
                                     , thursday=publication_dict.get('thursday')
                                     , friday=publication_dict.get('friday')
                                     , saturday=publication_dict.get('saturday')
                                     , sunday=publication_dict.get('sunday')
                                     , day_of_month=publication_dict.get('day_of_month')
                                     , pub_time=publication_dict.get('pub_time')
                                     , report_id=publication_dict.get('report_id')
                                     , creator_user_id=creator_id
                                     )

    contact_ids = publication_dict.get('contact_ids', [])
    if contact_ids:
        for contact_id in contact_ids:
            contact = get_record_from_id(models.Contact, contact_id)
            publication.recipients.append(contact)

    db.session.add(publication)
    db.session.commit()
    return publication


def edit_publication_from_dict(publication_dict):
    publication = get_record_from_id(models.Publication, publication_dict.get('publication_id'))

    if not publication:
        raise AssertionError('publication_id not found')

    if publication_dict.get('type'):
        publication.type = publication_dict.get('type')

    if publication_dict.get('frequency'):
        publication.frequency = publication_dict.get('frequency')

    if publication_dict.get('frequency') == 'days_of_week':
        publication.monday = publication_dict.get('monday')
        publication.monday = publication_dict.get('tuesday')
        publication.monday = publication_dict.get('wednesday')
        publication.monday = publication_dict.get('thursday')
        publication.monday = publication_dict.get('friday')
        publication.monday = publication_dict.get('saturday')
        publication.monday = publication_dict.get('sunday')

    if publication_dict.get('frequency') == 'day_of_month':
        publication.day_of_month = publication_dict.get('day_of_month')

    if publication_dict.get('pub_time'):
        publication.pub_time = publication_dict.get('pub_time')

    if publication_dict.get('report_id'):
        publication.report_id = publication_dict.get('report_id')

    contact_ids = publication_dict.get('contact_ids', [])
    if contact_ids:
        publication.recipients = []
    for contact_id in contact_ids:
        contact = get_record_from_id(models.Contact, contact_id)
        publication.recipients.append(contact)

    db.session.commit()
    return publication
