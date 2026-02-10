"""WSGI Entry point for Flask app."""
import warnings
from sqlalchemy.exc import SAWarning

# Suppress harmless relationship overlap warnings from piecash
warnings.filterwarnings("ignore", category=SAWarning, message="relationship '.*' will copy column")

from . import create_app

app = create_app()
