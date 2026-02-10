"""Tests for GnuCash Web configuration management."""
import os
import pytest
import tempfile
from unittest.mock import patch

from gnucash_web import create_app
from gnucash_web.config import GnuCashWebConfig


class TestGnuCashWebConfig:
    """Tests for the GnuCashWebConfig class."""

    def test_default_db_driver(self, app):
        """Default DB_DRIVER should be sqlite."""
        assert app.config["DB_DRIVER"] == "sqlite"

    def test_default_transaction_page_length(self, app):
        """Default TRANSACTION_PAGE_LENGTH should be 25."""
        assert app.config["TRANSACTION_PAGE_LENGTH"] == 25

    def test_config_attribute_access(self, app):
        """Config should support attribute-style access."""
        assert app.config.DB_DRIVER == "sqlite"

    def test_config_dict_access(self, app):
        """Config should support dict-style access."""
        assert app.config["DB_DRIVER"] == "sqlite"

    def test_config_contains_existing_key(self, app):
        """Config should support 'in' operator for existing keys."""
        assert "DB_DRIVER" in app.config
        assert "TESTING" in app.config

    def test_config_contains_missing_key_raises(self, app):
        """Config __contains__ for missing keys raises KeyError due to __getattr__."""
        with pytest.raises(KeyError):
            "NONEXISTENT_KEY_12345" in app.config

    def test_test_config_overrides_defaults(self):
        """Test config should override default values."""
        test_config = {
            "TRANSACTION_PAGE_LENGTH": 50,
            "DB_DRIVER": "sqlite",
            "DB_NAME": "test.sqlite",
            "DB_HOST": "localhost",
            "AUTH_MECHANISM": None,
            "LOG_LEVEL": "DEBUG",
            "SECRET_KEY": b"\x00",
            "PRESELECTED_CONTRA_ACCOUNT": None,
        }
        application = create_app(test_config)
        assert application.config["TRANSACTION_PAGE_LENGTH"] == 50


class TestDBUri:
    """Tests for the DB_URI method."""

    def test_sqlite_uri_no_credentials(self, app):
        """SQLite URI should be generated without credentials."""
        uri = app.config.DB_URI(None, None)
        assert uri.startswith("sqlite:///")
        assert app.config["DB_NAME"] in uri

    def test_sqlite_uri_rejects_credentials(self, app):
        """SQLite should raise ValueError when credentials are provided."""
        with pytest.raises(ValueError, match="does not accept credentials"):
            app.config.DB_URI("user", "pass")

    def test_postgres_uri_with_credentials(self, app_passthrough):
        """PostgreSQL URI should include credentials."""
        uri = app_passthrough.config.DB_URI("myuser", "mypass")
        assert "postgresql://" in uri
        assert "myuser" in uri
        assert "mypass" in uri

    def test_postgres_uri_includes_host_and_db(self, app_passthrough):
        """PostgreSQL URI should include host and database name."""
        uri = app_passthrough.config.DB_URI("user", "pass")
        assert "localhost" in uri
        assert "testdb" in uri

    def test_postgres_uri_without_password(self, app_passthrough):
        """PostgreSQL URI with user only should still work."""
        uri = app_passthrough.config.DB_URI("user", None)
        assert "user@" in uri


class TestConfigFromEnvVars:
    """Tests for configuration loaded from environment variables."""

    def test_env_var_db_driver(self):
        """DB_DRIVER should be readable from environment."""
        with patch.dict(os.environ, {"DB_DRIVER": "postgresql"}):
            from importlib import reload
            from gnucash_web.config import default as default_module
            reload(default_module)
            try:
                application = create_app({
                    "SECRET_KEY": b"\x00",
                    "LOG_LEVEL": "DEBUG",
                    "AUTH_MECHANISM": None,
                    "PRESELECTED_CONTRA_ACCOUNT": None,
                })
                assert application.config["DB_DRIVER"] == "postgresql"
            finally:
                reload(default_module)

    def test_env_var_transaction_page_length(self):
        """TRANSACTION_PAGE_LENGTH should be readable from environment."""
        with patch.dict(os.environ, {"TRANSACTION_PAGE_LENGTH": "10"}):
            from importlib import reload
            from gnucash_web.config import default as default_module
            reload(default_module)
            try:
                application = create_app({
                    "SECRET_KEY": b"\x00",
                    "LOG_LEVEL": "DEBUG",
                    "AUTH_MECHANISM": None,
                    "DB_DRIVER": "sqlite",
                    "DB_NAME": "test.sqlite",
                    "DB_HOST": "localhost",
                    "PRESELECTED_CONTRA_ACCOUNT": None,
                })
                assert application.config["TRANSACTION_PAGE_LENGTH"] == 10
            finally:
                reload(default_module)

    def test_config_from_file(self, tmp_path):
        """Config should be loadable from a Python file via GNUCASH_WEB_CONFIG."""
        config_file = tmp_path / "custom_config.py"
        config_file.write_text("CUSTOM_VALUE = 'hello'\n")

        with patch.dict(os.environ, {"GNUCASH_WEB_CONFIG": str(config_file)}):
            application = create_app({
                "SECRET_KEY": b"\x00",
                "LOG_LEVEL": "DEBUG",
                "AUTH_MECHANISM": None,
                "DB_DRIVER": "sqlite",
                "DB_NAME": "test.sqlite",
                "DB_HOST": "localhost",
                "PRESELECTED_CONTRA_ACCOUNT": None,
            })
            assert application.config["CUSTOM_VALUE"] == "hello"
