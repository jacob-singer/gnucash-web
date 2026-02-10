"""Tests for authentication module."""
import pytest
from unittest.mock import patch, MagicMock

from gnucash_web import create_app


class TestNoAuth:
    """Tests for authentication when AUTH_MECHANISM is None (no auth)."""

    def test_no_auth_is_authenticated(self, client):
        """Without auth mechanism, user should always be authenticated."""
        with client.application.test_request_context():
            from gnucash_web.auth import is_authenticated
            assert is_authenticated() is True

    def test_no_auth_get_db_credentials(self, client):
        """Without auth mechanism, credentials should be (None, None)."""
        with client.application.test_request_context():
            from gnucash_web.auth import get_db_credentials
            assert get_db_credentials() == (None, None)

    def test_no_auth_authenticate_always_true(self, client):
        """Without auth mechanism, authenticate should always return True."""
        with client.application.test_request_context():
            from gnucash_web.auth import authenticate
            assert authenticate("anyone", "anything") is True

    def test_no_auth_end_session_noop(self, client):
        """Without auth mechanism, end_session should be a no-op."""
        with client.application.test_request_context():
            from gnucash_web.auth import end_session
            end_session()

    def test_no_auth_accounts_accessible(self, client):
        """Without auth mechanism, accounts should be directly accessible."""
        response = client.get("/book/accounts/")
        assert response.status_code == 200

    def test_no_auth_login_page_shows_user(self, client):
        """Login page without auth should show 'logged in as no one'."""
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert b"no one" in response.data


class TestPassthroughAuth:
    """Tests for passthrough authentication mechanism."""

    def test_passthrough_requires_login(self, client_passthrough):
        """With passthrough auth, unauthenticated requests should redirect to login."""
        response = client_passthrough.get("/book/accounts/")
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_passthrough_login_page_renders(self, client_passthrough):
        """Login page should render a form for passthrough auth."""
        response = client_passthrough.get("/auth/login")
        assert response.status_code == 200
        assert b"username" in response.data.lower() or b"login" in response.data.lower()

    @patch("gnucash_web.auth.open_book")
    def test_passthrough_login_success(self, mock_open_book, client_passthrough):
        """Successful login should set session and redirect."""
        mock_open_book.return_value.__enter__ = MagicMock()
        mock_open_book.return_value.__exit__ = MagicMock(return_value=False)

        response = client_passthrough.post(
            "/auth/login",
            data={"username": "testuser", "password": "testpass"},
            follow_redirects=False,
        )
        assert response.status_code == 302

    @patch("gnucash_web.auth.open_book")
    def test_passthrough_login_sets_session(self, mock_open_book, client_passthrough):
        """After login, user should be able to access protected routes."""
        mock_open_book.return_value.__enter__ = MagicMock()
        mock_open_book.return_value.__exit__ = MagicMock(return_value=False)

        with client_passthrough.session_transaction() as sess:
            sess["username"] = "testuser"
            sess["password"] = "testpass"

        with client_passthrough.application.test_request_context():
            with client_passthrough.session_transaction() as sess:
                assert "username" in sess

    @patch("gnucash_web.auth.open_book")
    def test_passthrough_login_failure(self, mock_open_book, client_passthrough):
        """Failed login should redirect back to login page."""
        from gnucash_web.utils.gnucash import AccessDenied
        mock_open_book.side_effect = AccessDenied("Access denied")

        response = client_passthrough.post(
            "/auth/login",
            data={"username": "baduser", "password": "badpass"},
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_passthrough_get_credentials_raises_without_session(self, client_passthrough):
        """get_db_credentials should raise KeyError if session is empty."""
        with client_passthrough.application.test_request_context():
            from gnucash_web.auth import get_db_credentials
            with pytest.raises(KeyError):
                get_db_credentials()

    def test_passthrough_is_not_authenticated_initially(self, client_passthrough):
        """User should not be authenticated without logging in first."""
        with client_passthrough.application.test_request_context():
            from gnucash_web.auth import is_authenticated
            assert is_authenticated() is False

    def test_unsupported_auth_mechanism(self):
        """Unsupported auth mechanism should raise NotImplementedError."""
        test_config = {
            "TESTING": True,
            "SECRET_KEY": b"\x00",
            "DB_DRIVER": "sqlite",
            "DB_NAME": "test.sqlite",
            "DB_HOST": "localhost",
            "AUTH_MECHANISM": "kerberos",
            "LOG_LEVEL": "DEBUG",
            "TRANSACTION_PAGE_LENGTH": 25,
            "PRESELECTED_CONTRA_ACCOUNT": None,
        }
        application = create_app(test_config)
        with application.test_request_context():
            from gnucash_web.auth import get_db_credentials
            with pytest.raises(NotImplementedError, match="Only passthrough"):
                get_db_credentials()


class TestLogout:
    """Tests for the logout functionality."""

    def test_logout_redirects_to_login(self, client_passthrough):
        """Logout should redirect to login page."""
        with client_passthrough.session_transaction() as sess:
            sess["username"] = "testuser"
            sess["password"] = "testpass"

        response = client_passthrough.post("/auth/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/auth/login" in response.headers["Location"]

    def test_logout_clears_session(self, client_passthrough):
        """Logout should clear username and password from session."""
        with client_passthrough.session_transaction() as sess:
            sess["username"] = "testuser"
            sess["password"] = "testpass"

        client_passthrough.post("/auth/logout")

        with client_passthrough.session_transaction() as sess:
            assert "username" not in sess
            assert "password" not in sess


class TestRequiresAuth:
    """Tests for the @requires_auth decorator."""

    def test_decorated_route_redirects_when_unauthenticated(self, client_passthrough):
        """Protected routes should redirect to login when not authenticated."""
        response = client_passthrough.get("/book/accounts/")
        assert response.status_code == 302
        assert "login" in response.headers["Location"]

    def test_decorated_route_includes_return_url(self, client_passthrough):
        """Redirect to login should include the return_url parameter."""
        response = client_passthrough.get("/book/accounts/")
        assert response.status_code == 302
        assert "return_url" in response.headers["Location"]
