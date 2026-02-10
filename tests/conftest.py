"""Shared test fixtures for GnuCash Web tests."""
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from gnucash_web import create_app


SAMPLE_DB = Path(__file__).parent.parent / "sample" / "sample.sqlite"


@pytest.fixture
def sample_db(tmp_path):
    """Provide a temporary copy of the sample SQLite database.

    Returns the path to the copy so tests can write to it without
    mutating the original.
    """
    dest = tmp_path / "test.sqlite"
    shutil.copy2(SAMPLE_DB, dest)
    return str(dest)


@pytest.fixture
def app(sample_db):
    """Create a Flask application configured for testing."""
    test_config = {
        "TESTING": True,
        "SECRET_KEY": b"\x00\x00\x00\x00",
        "DB_DRIVER": "sqlite",
        "DB_NAME": sample_db,
        "DB_HOST": "localhost",
        "AUTH_MECHANISM": None,
        "TRANSACTION_PAGE_LENGTH": 25,
        "PRESELECTED_CONTRA_ACCOUNT": None,
        "LOG_LEVEL": "DEBUG",
    }
    application = create_app(test_config)
    yield application


@pytest.fixture
def client(app):
    """Provide a Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Provide a Flask CLI test runner."""
    return app.test_cli_runner()


@pytest.fixture
def app_passthrough(sample_db):
    """Create a Flask app with passthrough auth enabled.

    Since SQLite doesn't actually use credentials, this tests the auth
    flow logic without needing a real PostgreSQL/MySQL database.
    We set AUTH_MECHANISM to 'passthrough' but use sqlite, which will
    raise ValueError in DB_URI — so tests using this fixture must
    mock open_book or DB_URI appropriately.
    """
    test_config = {
        "TESTING": True,
        "SECRET_KEY": b"\x00\x00\x00\x00",
        "DB_DRIVER": "postgresql",
        "DB_NAME": "testdb",
        "DB_HOST": "localhost",
        "AUTH_MECHANISM": "passthrough",
        "TRANSACTION_PAGE_LENGTH": 25,
        "PRESELECTED_CONTRA_ACCOUNT": None,
        "LOG_LEVEL": "DEBUG",
    }
    application = create_app(test_config)
    yield application


@pytest.fixture
def client_passthrough(app_passthrough):
    """Provide a Flask test client with passthrough auth."""
    return app_passthrough.test_client()
