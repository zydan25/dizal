import builtins
import flask_security

# Flask-Security's AsaList type can be emitted by Alembic migrations as
# flask_security.datastore.AsaList(). Make it available to migration modules
# that were generated before the import was included in the revision header.
builtins.flask_security = flask_security

from app import create_app

app = create_app()
