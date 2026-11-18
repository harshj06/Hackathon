import os
import tempfile
from pathlib import Path

# Set the database before any application module is imported during collection.
_database = tempfile.TemporaryDirectory(prefix='cognify-tests-')
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(_database.name) / 'test.db')
