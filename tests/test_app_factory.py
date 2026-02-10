"""Tests for the Flask application factory and basic app setup."""
import pytest
from pathlib import Path

from gnucash_web import create_app


class TestCreateApp:
    """Tests for the create_app factory function."""

    def test_create_app_returns_flask_app(self, app):
        """App factory should return a Flask application."""
        from flask import Flask
        assert isinstance(app, Flask)

    def test_create_app_with_test_config(self, app):
        """App factory should apply test configuration."""
        assert app.config["TESTING"] is True

    def test_create_app_default_config(self):
        """App factory without test_config should load defaults."""
        application = create_app()
        assert application is not None
        assert application.config["DB_DRIVER"] == "sqlite"

    def test_app_has_secret_key(self, app):
        """App should have SECRET_KEY configured."""
        assert app.config["SECRET_KEY"] is not None

    def test_jinja_autoescape_enabled(self, app):
        """Jinja2 autoescape should be enabled for security."""
        assert app.jinja_env.autoescape is True

    def test_jinja_filters_registered(self, app):
        """All custom Jinja2 filters should be registered."""
        expected_filters = [
            "display",
            "cssescape",
            "parentaccounts",
            "money",
            "accounturl",
            "full_account_names",
            "contrasplits",
            "nth",
            "safe_balance",
        ]
        for name in expected_filters:
            assert name in app.jinja_env.filters, f"Missing filter: {name}"

    def test_jinja_globals_registered(self, app):
        """Jinja2 globals should include is_authenticated and pkg_version."""
        assert "is_authenticated" in app.jinja_env.globals
        assert "pkg_version" in app.jinja_env.globals

    def test_pkg_version_is_string(self, app):
        """pkg_version global should be a non-empty string."""
        version = app.jinja_env.globals["pkg_version"]
        assert isinstance(version, str)
        assert len(version) > 0

    def test_blueprints_registered(self, app):
        """Auth, book, and commodities blueprints should be registered."""
        assert "auth" in app.blueprints
        assert "book" in app.blueprints
        assert "commodities" in app.blueprints


class TestIndexRoute:
    """Tests for the root route /."""

    def test_index_redirects_to_book(self, client):
        """Root URL should redirect to the book accounts view."""
        response = client.get("/")
        assert response.status_code == 302
        assert "/book/accounts/" in response.headers["Location"]
