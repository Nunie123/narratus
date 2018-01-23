from app import app, db
from app.models import (User, Usergroup, Connection, Query,
    Chart, Report, Publication, Contact)

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Usergroup': Usergroup,
        'Connection': Connection, 'Query': Query, 'Chart': Chart,
        'Report': Report, 'Publication': Publication,
        'Contact': Contact}
