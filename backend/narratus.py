from backend.app import app, db
from backend.app.models import (User, Usergroup, Connection, SqlQuery,
                                Chart, Report, Publication, Contact, user_perms,
                                connection_perms)


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Usergroup': Usergroup,
            'Connection': Connection, 'SqlQuery': SqlQuery, 'Chart': Chart,
            'Report': Report, 'Publication': Publication,
            'Contact': Contact, 'user_perms': user_perms,
            'connection_perms': connection_perms}
