from app import app, db
from app.models import (User, Usergroup, Connection, Query,
    Chart, Report, Publication, Contact, user_perms,
    connection_perms)

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Usergroup': Usergroup,
        'Connection': Connection, 'Query': Query, 'Chart': Chart,
        'Report': Report, 'Publication': Publication,
        'Contact': Contact, 'user_perms': user_perms,
        'connection_perms': connection_perms}
