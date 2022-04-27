from app import app, db
from app.models import User, Domain, Cdrom, Volume, Image


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Domain': Domain, 'Cdrom': Cdrom}
