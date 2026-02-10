"""Tests for the book blueprint (accounts and transactions)."""
import shutil
import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock

import piecash

from gnucash_web import create_app


SAMPLE_DB = "sample/sample.sqlite"


class TestShowAccount:
    """Tests for the show_account route."""

    def test_show_root_account(self, client):
        """GET /book/accounts/ should display the root account."""
        response = client.get("/book/accounts/")
        assert response.status_code == 200

    def test_show_root_contains_top_level_accounts(self, client):
        """Root account page should list top-level accounts."""
        response = client.get("/book/accounts/")
        assert b"Assets" in response.data
        assert b"Liabilities" in response.data
        assert b"Income" in response.data
        assert b"Expenses" in response.data
        assert b"Equity" in response.data

    def test_show_child_account(self, client):
        """GET /book/accounts/Assets should display the Assets account."""
        response = client.get("/book/accounts/Assets")
        assert response.status_code == 200
        assert b"Assets" in response.data

    def test_show_nested_account(self, client):
        """GET /book/accounts/Assets/Current+Assets should work."""
        response = client.get("/book/accounts/Assets/Current+Assets")
        assert response.status_code == 200
        assert b"Current Assets" in response.data

    def test_show_deeply_nested_account(self, client):
        """GET should work for deeply nested accounts."""
        response = client.get("/book/accounts/Assets/Current+Assets/Checking+Account")
        assert response.status_code == 200
        assert b"Checking Account" in response.data

    def test_show_nonexistent_account_404(self, client):
        """Requesting a non-existent account should return 404."""
        response = client.get("/book/accounts/NonExistent")
        assert response.status_code == 404

    def test_show_account_with_pagination(self, client):
        """Page parameter should be accepted."""
        response = client.get("/book/accounts/?page=1")
        assert response.status_code == 200

    def test_show_account_invalid_page_param(self, client):
        """Invalid page parameter should return 400."""
        response = client.get("/book/accounts/?page=abc")
        assert response.status_code == 400

    def test_show_account_negative_page_param(self, client):
        """Negative page number should return 400."""
        response = client.get("/book/accounts/?page=-1")
        assert response.status_code == 400

    def test_show_account_zero_page_param(self, client):
        """Zero page number should return 400."""
        response = client.get("/book/accounts/?page=0")
        assert response.status_code == 400

    def test_show_account_page_too_high(self, client):
        """Page number beyond last page should return 400."""
        response = client.get("/book/accounts/?page=9999")
        assert response.status_code == 400

    def test_show_expenses_account(self, client):
        """Expenses account should render sub-accounts."""
        response = client.get("/book/accounts/Expenses")
        assert response.status_code == 200
        assert b"Groceries" in response.data or b"Expenses" in response.data


class TestAddTransaction:
    """Tests for the add_transaction route."""

    def test_add_transaction_success(self, client, sample_db):
        """POST /book/add_transaction should create a transaction and redirect."""
        response = client.post(
            "/book/add_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "date": "2024-01-15",
                "description": "Test salary deposit",
                "value": "1000.00",
                "contra_account_name": "Income:Salary",
                "sign": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_add_transaction_creates_entry(self, client, sample_db):
        """New transaction should be visible when viewing the account."""
        client.post(
            "/book/add_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "date": "2024-01-15",
                "description": "Unique Test Transaction 12345",
                "value": "500.00",
                "contra_account_name": "Income:Salary",
                "sign": "1",
            },
        )
        response = client.get("/book/accounts/Assets/Current+Assets/Checking+Account")
        assert b"Unique Test Transaction 12345" in response.data

    def test_add_transaction_negative_value_rejected(self, client):
        """Negative transaction values should be rejected."""
        response = client.post(
            "/book/add_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "date": "2024-01-15",
                "description": "Bad value",
                "value": "-100.00",
                "contra_account_name": "Income:Salary",
                "sign": "1",
            },
        )
        assert response.status_code == 400

    def test_add_transaction_invalid_date(self, client):
        """Invalid date format should be rejected."""
        response = client.post(
            "/book/add_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "date": "not-a-date",
                "description": "Bad date",
                "value": "100.00",
                "contra_account_name": "Income:Salary",
                "sign": "1",
            },
        )
        assert response.status_code == 400

    def test_add_transaction_invalid_value(self, client):
        """Non-numeric value should be rejected."""
        response = client.post(
            "/book/add_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "date": "2024-01-15",
                "description": "Bad value",
                "value": "not-a-number",
                "contra_account_name": "Income:Salary",
                "sign": "1",
            },
        )
        assert response.status_code == 400

    def test_add_transaction_invalid_sign(self, client):
        """Non-integer sign should be rejected."""
        response = client.post(
            "/book/add_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "date": "2024-01-15",
                "description": "Bad sign",
                "value": "100.00",
                "contra_account_name": "Income:Salary",
                "sign": "abc",
            },
        )
        assert response.status_code == 400

    def test_add_transaction_nonexistent_account(self, client):
        """Transaction with non-existent account should fail."""
        response = client.post(
            "/book/add_transaction",
            data={
                "account_name": "NonExistent:Account",
                "date": "2024-01-15",
                "description": "Test",
                "value": "100.00",
                "contra_account_name": "Income:Salary",
                "sign": "1",
            },
        )
        assert response.status_code == 404

    def test_add_transaction_nonexistent_contra_account(self, client):
        """Transaction with non-existent contra account should fail."""
        response = client.post(
            "/book/add_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "date": "2024-01-15",
                "description": "Test",
                "value": "100.00",
                "contra_account_name": "NonExistent:ContraAccount",
                "sign": "1",
            },
        )
        assert response.status_code == 404

    def test_add_transaction_placeholder_account_rejected(self, client):
        """Transactions should not be addable to placeholder accounts."""
        response = client.post(
            "/book/add_transaction",
            data={
                "account_name": "Assets",
                "date": "2024-01-15",
                "description": "Test",
                "value": "100.00",
                "contra_account_name": "Income:Salary",
                "sign": "1",
            },
        )
        assert response.status_code == 400

    def test_add_withdrawal_transaction(self, client, sample_db):
        """Withdrawal (sign=-1) should create a negative-value split."""
        response = client.post(
            "/book/add_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "date": "2024-01-15",
                "description": "Test withdrawal",
                "value": "50.00",
                "contra_account_name": "Expenses:Groceries",
                "sign": "-1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302


class TestEditTransaction:
    """Tests for the edit_transaction route."""

    def _create_transaction(self, client):
        """Helper to create a transaction and return its GUID."""
        client.post(
            "/book/add_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "date": "2024-01-15",
                "description": "Transaction to edit",
                "value": "100.00",
                "contra_account_name": "Income:Salary",
                "sign": "1",
            },
        )
        with piecash.open_book(
            uri_conn=f"sqlite:///{client.application.config['DB_NAME']}",
            readonly=True,
            open_if_lock=True,
        ) as book:
            txn = book.transactions[-1]
            return txn.guid

    def test_edit_transaction_success(self, client, sample_db):
        """Editing a transaction should succeed and redirect."""
        guid = self._create_transaction(client)
        response = client.post(
            "/book/edit_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "guid": guid,
                "date": "2024-02-20",
                "description": "Edited transaction",
                "value": "200.00",
                "contra_account_name": "Income:Salary",
                "sign": "1",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_edit_transaction_updates_description(self, client, sample_db):
        """Edited transaction should have updated description."""
        guid = self._create_transaction(client)
        client.post(
            "/book/edit_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "guid": guid,
                "date": "2024-02-20",
                "description": "Updated description XYZ",
                "value": "200.00",
                "contra_account_name": "Income:Salary",
                "sign": "1",
            },
        )
        response = client.get("/book/accounts/Assets/Current+Assets/Checking+Account")
        assert b"Updated description XYZ" in response.data

    def test_edit_transaction_invalid_value(self, client, sample_db):
        """Editing with invalid value should return 400."""
        guid = self._create_transaction(client)
        response = client.post(
            "/book/edit_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "guid": guid,
                "date": "2024-02-20",
                "description": "Bad edit",
                "value": "not-a-number",
                "contra_account_name": "Income:Salary",
                "sign": "1",
            },
        )
        assert response.status_code == 400

    def test_edit_transaction_negative_value_rejected(self, client, sample_db):
        """Editing with negative value should return 400."""
        guid = self._create_transaction(client)
        response = client.post(
            "/book/edit_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "guid": guid,
                "date": "2024-02-20",
                "description": "Negative edit",
                "value": "-50.00",
                "contra_account_name": "Income:Salary",
                "sign": "1",
            },
        )
        assert response.status_code == 400


class TestDeleteTransaction:
    """Tests for the del_transaction route."""

    def _create_transaction(self, client):
        """Helper to create a transaction and return its GUID."""
        client.post(
            "/book/add_transaction",
            data={
                "account_name": "Assets:Current Assets:Checking Account",
                "date": "2024-01-15",
                "description": "Transaction to delete",
                "value": "100.00",
                "contra_account_name": "Income:Salary",
                "sign": "1",
            },
        )
        with piecash.open_book(
            uri_conn=f"sqlite:///{client.application.config['DB_NAME']}",
            readonly=True,
            open_if_lock=True,
        ) as book:
            txn = book.transactions[-1]
            return txn.guid

    def test_delete_transaction_success(self, client, sample_db):
        """Deleting a transaction should succeed and redirect."""
        guid = self._create_transaction(client)
        response = client.post(
            "/book/del_transaction",
            data={
                "guid": guid,
                "account_name": "Assets:Current Assets:Checking Account",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_delete_transaction_removes_entry(self, client, sample_db):
        """Deleted transaction should no longer appear in the ledger."""
        guid = self._create_transaction(client)
        client.post(
            "/book/del_transaction",
            data={
                "guid": guid,
                "account_name": "Assets:Current Assets:Checking Account",
            },
        )
        response = client.get("/book/accounts/Assets/Current+Assets/Checking+Account")
        assert b"Transaction to delete" not in response.data


class TestErrorHandlers:
    """Tests for error handler pages."""

    def test_account_not_found_renders_error_page(self, client):
        """404 for missing accounts should render the error template."""
        response = client.get("/book/accounts/No/Such/Account")
        assert response.status_code == 404
        assert b"No" in response.data or b"not found" in response.data.lower()

    def test_database_locked_error(self, client):
        """DatabaseLocked should render the locked error page with ignore option."""
        from gnucash_web.utils.gnucash import DatabaseLocked

        with patch("gnucash_web.book.open_book") as mock_open:
            mock_open.side_effect = DatabaseLocked()
            response = client.get("/book/accounts/")
            assert response.status_code == 423
            assert b"open_if_lock" in response.data
