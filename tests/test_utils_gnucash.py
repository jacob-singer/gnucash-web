"""Tests for GnuCash utility functions."""
import pytest
from unittest.mock import patch, MagicMock

from gnucash_web import create_app
from gnucash_web.utils.gnucash import (
    AccessDenied,
    AccountNotFound,
    DatabaseLocked,
    open_book,
    get_account,
)


class TestExceptions:
    """Tests for custom exception classes."""

    def test_access_denied_is_exception(self):
        """AccessDenied should be an Exception."""
        exc = AccessDenied("test")
        assert isinstance(exc, Exception)

    def test_account_not_found_is_not_found(self):
        """AccountNotFound should be a werkzeug NotFound (404)."""
        from werkzeug.exceptions import NotFound
        exc = AccountNotFound("Assets:Missing")
        assert isinstance(exc, NotFound)
        assert exc.code == 404

    def test_account_not_found_stores_name(self):
        """AccountNotFound should store the account name."""
        exc = AccountNotFound("Assets:Missing:Account")
        assert exc.account_name == "Assets:Missing:Account"

    def test_database_locked_is_locked(self):
        """DatabaseLocked should be a werkzeug Locked (423)."""
        from werkzeug.exceptions import Locked
        exc = DatabaseLocked()
        assert isinstance(exc, Locked)
        assert exc.code == 423


class TestOpenBook:
    """Tests for the open_book context manager."""

    def test_open_book_success(self, app, sample_db):
        """open_book should successfully open a SQLite database."""
        with app.test_request_context():
            with open_book(
                uri_conn=f"sqlite:///{sample_db}",
                readonly=True,
                open_if_lock=True,
            ) as book:
                assert book is not None
                assert book.root_account is not None

    def test_open_book_reads_accounts(self, app, sample_db):
        """open_book should provide access to accounts."""
        with app.test_request_context():
            with open_book(
                uri_conn=f"sqlite:///{sample_db}",
                readonly=True,
                open_if_lock=True,
            ) as book:
                accounts = book.accounts
                assert len(list(accounts)) > 0

    @patch("gnucash_web.utils.gnucash.piecash.open_book")
    def test_open_book_lock_raises_database_locked(self, mock_piecash_open, app):
        """open_book should raise DatabaseLocked when the file is locked."""
        from piecash import GnucashException
        mock_piecash_open.side_effect = GnucashException("Lock on the file is active")

        with app.test_request_context():
            with pytest.raises(DatabaseLocked):
                with open_book(
                    uri_conn="sqlite:///dummy.sqlite",
                    readonly=True,
                    open_if_lock=False,
                ) as book:
                    pass

    @patch("gnucash_web.utils.gnucash.piecash.open_book")
    def test_open_book_access_denied(self, mock_piecash_open, app):
        """open_book should raise AccessDenied on OperationalError."""
        import sqlalchemy.exc
        mock_piecash_open.side_effect = sqlalchemy.exc.OperationalError(
            "SELECT 1", {}, Exception("Access denied for user 'bad'@'localhost'")
        )

        with app.test_request_context():
            with pytest.raises(AccessDenied):
                with open_book(
                    uri_conn="sqlite:///dummy.sqlite",
                    readonly=True,
                    open_if_lock=True,
                ) as book:
                    pass

    @patch("gnucash_web.utils.gnucash.piecash.open_book")
    def test_open_book_reraises_unknown_gnucash_exception(self, mock_piecash_open, app):
        """Unknown GnucashExceptions should be re-raised as-is."""
        from piecash import GnucashException
        mock_piecash_open.side_effect = GnucashException("Some other error")

        with app.test_request_context():
            with pytest.raises(GnucashException, match="Some other error"):
                with open_book(
                    uri_conn="sqlite:///dummy.sqlite",
                    readonly=True,
                    open_if_lock=True,
                ) as book:
                    pass

    @patch("gnucash_web.utils.gnucash.piecash.open_book")
    def test_open_book_reraises_unknown_operational_error(self, mock_piecash_open, app):
        """Unknown OperationalErrors should be re-raised as-is."""
        import sqlalchemy.exc
        mock_piecash_open.side_effect = sqlalchemy.exc.OperationalError(
            "SELECT 1", {}, Exception("Connection refused")
        )

        with app.test_request_context():
            with pytest.raises(sqlalchemy.exc.OperationalError):
                with open_book(
                    uri_conn="sqlite:///dummy.sqlite",
                    readonly=True,
                    open_if_lock=True,
                ) as book:
                    pass

    def test_open_book_reads_open_if_lock_from_request(self, app, sample_db):
        """open_book should read open_if_lock from request args if not provided."""
        with app.test_request_context("/?open_if_lock=True"):
            with open_book(
                uri_conn=f"sqlite:///{sample_db}",
                readonly=True,
            ) as book:
                assert book is not None


class TestGetAccount:
    """Tests for the get_account function."""

    def test_get_account_success(self, app, sample_db):
        """get_account should return an existing account."""
        with app.test_request_context():
            with open_book(
                uri_conn=f"sqlite:///{sample_db}",
                readonly=True,
                open_if_lock=True,
            ) as book:
                account = get_account(book, fullname="Assets")
                assert account.name == "Assets"

    def test_get_account_nested(self, app, sample_db):
        """get_account should find nested accounts by fullname."""
        with app.test_request_context():
            with open_book(
                uri_conn=f"sqlite:///{sample_db}",
                readonly=True,
                open_if_lock=True,
            ) as book:
                account = get_account(book, fullname="Assets:Current Assets:Checking Account")
                assert account.name == "Checking Account"

    def test_get_account_not_found_raises(self, app, sample_db):
        """get_account should raise AccountNotFound for missing accounts."""
        with app.test_request_context():
            with open_book(
                uri_conn=f"sqlite:///{sample_db}",
                readonly=True,
                open_if_lock=True,
            ) as book:
                with pytest.raises(AccountNotFound):
                    get_account(book, fullname="NonExistent:Account")
