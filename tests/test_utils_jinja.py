"""Tests for Jinja2 template utility functions."""
import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from gnucash_web import create_app
from gnucash_web.utils.jinja import (
    safe_display_string,
    css_escape,
    parent_accounts,
    money,
    account_url,
    full_account_names,
    contra_splits,
    nth,
    safe_balance,
)


class TestSafeDisplayString:
    """Tests for safe_display_string filter."""

    def test_normal_string_unchanged(self):
        """Non-empty strings should pass through unchanged."""
        assert safe_display_string("hello") == "hello"

    def test_empty_string_replaced(self):
        """Empty string should be replaced with '<blank string>'."""
        assert safe_display_string("") == "<blank string>"

    def test_whitespace_only_replaced(self):
        """Whitespace-only string should be replaced."""
        assert safe_display_string("   ") == "<blank string>"

    def test_tab_only_replaced(self):
        """Tab-only string should be replaced."""
        assert safe_display_string("\t") == "<blank string>"

    def test_string_with_content_preserved(self):
        """String with actual content should be kept as-is."""
        assert safe_display_string("Test Transaction") == "Test Transaction"


class TestCssEscape:
    """Tests for css_escape filter."""

    def test_simple_string_unchanged(self):
        """Simple alphanumeric strings should pass through."""
        assert css_escape("hello") == "hello"

    def test_colons_escaped(self):
        """Colons should be escaped for CSS selectors."""
        result = css_escape("Assets:Checking")
        assert "\\" in result

    def test_spaces_escaped(self):
        """Spaces should be escaped for CSS selectors."""
        result = css_escape("Current Assets")
        assert "\\" in result

    def test_underscores_preserved(self):
        """Underscores should not be escaped."""
        assert css_escape("my_account") == "my_account"

    def test_hyphens_preserved(self):
        """Hyphens should not be escaped."""
        assert css_escape("my-account") == "my-account"


class TestParentAccounts:
    """Tests for parent_accounts filter."""

    def test_none_yields_nothing(self):
        """None should yield no accounts."""
        result = list(parent_accounts(None))
        assert result == []

    def test_root_account_yields_self(self):
        """An account with no parent should yield only itself."""
        account = MagicMock()
        account.parent = None
        result = list(parent_accounts(account))
        assert result == [account]

    def test_nested_account_yields_chain(self):
        """Nested account should yield full parent chain."""
        root = MagicMock()
        root.parent = None
        child = MagicMock()
        child.parent = root
        grandchild = MagicMock()
        grandchild.parent = child

        result = list(parent_accounts(grandchild))
        assert result == [root, child, grandchild]


class TestMoney:
    """Tests for money filter."""

    def _render_money(self, app, amount, commodity):
        """Helper to render money through the Jinja environment."""
        with app.test_request_context():
            template = app.jinja_env.from_string("{{ amount|money(commodity) }}")
            return template.render(amount=amount, commodity=commodity)

    def test_positive_amount_rendered(self, app):
        """Positive amounts should render with secondary color class."""
        commodity = MagicMock()
        commodity.mnemonic = "EUR"
        result = self._render_money(app, Decimal("100.00"), commodity)
        assert "text-secondary" in result

    def test_negative_amount_rendered(self, app):
        """Negative amounts should render with danger color class."""
        commodity = MagicMock()
        commodity.mnemonic = "EUR"
        result = self._render_money(app, Decimal("-50.00"), commodity)
        assert "text-danger" in result

    def test_unknown_currency_uses_mnemonic(self, app):
        """Unknown currencies should use mnemonic as-is."""
        commodity = MagicMock()
        commodity.mnemonic = "LOYALTY_POINTS"
        result = self._render_money(app, Decimal("100"), commodity)
        assert "LOYALTY_POINTS" in result


class TestAccountUrl:
    """Tests for account_url filter."""

    def test_root_child_account(self, app):
        """URL for a direct child of root should be simple."""
        with app.test_request_context():
            root = MagicMock()
            root.parent = None
            root.name = "Root"
            account = MagicMock()
            account.parent = root
            account.name = "Assets"

            url = account_url(account)
            assert "Assets" in str(url)

    def test_nested_account_url(self, app):
        """URL for nested account should use slash separators."""
        with app.test_request_context():
            root = MagicMock()
            root.parent = None
            root.name = "Root"
            parent = MagicMock()
            parent.parent = root
            parent.name = "Assets"
            child = MagicMock()
            child.parent = parent
            child.name = "Checking"

            url = account_url(child)
            assert "Assets" in str(url)
            assert "Checking" in str(url)


class TestFullAccountNames:
    """Tests for full_account_names filter."""

    def test_single_component(self):
        """Single component name should return just that name."""
        result = list(full_account_names("Assets"))
        assert result == ["Assets"]

    def test_two_components(self):
        """Two-component name should return both levels."""
        result = list(full_account_names("Assets:Checking"))
        assert result == ["Assets", "Assets:Checking"]

    def test_three_components(self):
        """Three-component name should return all levels."""
        result = list(full_account_names("Assets:Current Assets:Checking"))
        assert result == [
            "Assets",
            "Assets:Current Assets",
            "Assets:Current Assets:Checking",
        ]

    def test_empty_string(self):
        """Empty string should return list with empty string."""
        result = list(full_account_names(""))
        assert result == [""]


class TestContraSplits:
    """Tests for contra_splits filter."""

    def test_two_split_transaction(self):
        """Standard 2-split transaction should identify the contra split."""
        split1 = MagicMock()
        split1.value = Decimal("100")
        split2 = MagicMock()
        split2.value = Decimal("-100")

        txn = MagicMock()
        txn.splits = [split1, split2]
        split1.transaction = txn
        split2.transaction = txn

        result = contra_splits(split1)
        assert split2 in result
        assert split1 not in result

    def test_contra_splits_from_negative_side(self):
        """Contra splits should also work from the negative-value split."""
        split1 = MagicMock()
        split1.value = Decimal("100")
        split2 = MagicMock()
        split2.value = Decimal("-100")

        txn = MagicMock()
        txn.splits = [split1, split2]
        split1.transaction = txn
        split2.transaction = txn

        result = contra_splits(split2)
        assert split1 in result
        assert split2 not in result


class TestNth:
    """Tests for nth filter."""

    def test_first_element(self):
        """nth(0) should return the first element."""
        assert nth([10, 20, 30], 0) == 10

    def test_second_element(self):
        """nth(1) should return the second element."""
        assert nth([10, 20, 30], 1) == 20

    def test_out_of_range_returns_default(self):
        """Out-of-range index should return default (None)."""
        assert nth([10], 5) is None

    def test_out_of_range_custom_default(self):
        """Out-of-range index should return custom default."""
        assert nth([10], 5, "missing") == "missing"

    def test_works_with_generators(self):
        """nth should work with generators, not just lists."""
        gen = (x for x in range(5))
        assert nth(gen, 3) == 3

    def test_empty_iterable(self):
        """Empty iterable should return default."""
        assert nth([], 0) is None


class TestSafeBalance:
    """Tests for safe_balance filter."""

    def test_normal_balance(self):
        """When get_balance succeeds, should return the balance directly."""
        account = MagicMock()
        account.get_balance.return_value = Decimal("1000.00")
        assert safe_balance(account) == Decimal("1000.00")

    def test_conversion_error_fallback(self):
        """When get_balance raises GncConversionError, should fall back."""
        from piecash._common import GncConversionError

        account = MagicMock()
        account.get_balance.side_effect = GncConversionError("Cannot convert")
        account.splits = []
        account.children = []

        result = safe_balance(account)
        assert result == 0

    def test_conversion_error_with_own_splits(self):
        """Fallback should sum the account's own splits."""
        from piecash._common import GncConversionError

        split1 = MagicMock()
        split1.value = Decimal("100")
        split2 = MagicMock()
        split2.value = Decimal("200")

        account = MagicMock()
        account.get_balance.side_effect = GncConversionError("Cannot convert")
        account.splits = [split1, split2]
        account.children = []

        result = safe_balance(account)
        assert result == Decimal("300")

    def test_fallback_includes_same_commodity_children(self):
        """Fallback should include children with same commodity (no conversion needed).

        This is the key bug fix: piecash's currency_conversion() raises
        GncConversionError when converting a commodity to itself (e.g., USD to USD).
        The fallback must detect this case and use a factor of 1.
        """
        from piecash._common import GncConversionError

        usd = MagicMock()

        # Child with same commodity (USD), get_balance works fine
        child_checking = MagicMock()
        child_checking.get_balance.return_value = Decimal("500.00")
        child_checking.commodity = usd

        # Child with inconvertible commodity (no prices)
        bad_commodity = MagicMock()
        bad_commodity.currency_conversion.side_effect = GncConversionError("Cannot convert")
        child_bad = MagicMock()
        child_bad.get_balance.return_value = Decimal("1000")
        child_bad.commodity = bad_commodity
        child_bad.children = []

        # Parent account: get_balance fails because of the bad child
        account = MagicMock()
        account.get_balance.side_effect = GncConversionError("Cannot convert")
        account.commodity = usd
        account.splits = []
        account.children = [child_checking, child_bad]

        result = safe_balance(account)
        # Should include child_checking's $500 but skip the inconvertible child
        assert result == Decimal("500.00")

    def test_fallback_includes_convertible_children(self):
        """Fallback should include children with different but convertible commodities."""
        from piecash._common import GncConversionError

        usd = MagicMock()
        stock_commodity = MagicMock()
        # Stock has a price: 1 share = $100
        stock_commodity.currency_conversion.return_value = Decimal("100.00")

        # Stock child: 10 shares
        child_stock = MagicMock()
        child_stock.get_balance.return_value = Decimal("10")
        child_stock.commodity = stock_commodity

        # USD child: $200
        child_usd = MagicMock()
        child_usd.get_balance.return_value = Decimal("200.00")
        child_usd.commodity = usd

        # Parent: fails due to some other inconvertible child
        bad_commodity = MagicMock()
        bad_commodity.currency_conversion.side_effect = GncConversionError("Cannot convert")
        child_bad = MagicMock()
        child_bad.get_balance.return_value = Decimal("9999")
        child_bad.commodity = bad_commodity
        child_bad.children = []

        account = MagicMock()
        account.get_balance.side_effect = GncConversionError("Cannot convert")
        account.commodity = usd
        account.splits = []
        account.children = [child_stock, child_usd, child_bad]

        result = safe_balance(account)
        # 10 shares * $100/share + $200 = $1200, bad child skipped
        assert result == Decimal("1200.00")

    def test_fallback_with_nested_fallback(self):
        """Fallback should work recursively when nested accounts also need fallback.

        Simulates: Assets (USD) -> Points (USD) -> [AA Points (convertible), Delta (not convertible)]
        """
        from piecash._common import GncConversionError

        usd = MagicMock()
        aa_commodity = MagicMock()
        aa_commodity.currency_conversion.return_value = Decimal("0.01")  # 1 point = $0.01
        delta_commodity = MagicMock()
        delta_commodity.currency_conversion.side_effect = GncConversionError("No price")

        # Leaf: AA Points (5000 points, convertible)
        child_aa = MagicMock()
        child_aa.get_balance.return_value = Decimal("5000")
        child_aa.commodity = aa_commodity
        child_aa.children = []

        # Leaf: Delta SkyMiles (10000 points, NOT convertible)
        child_delta = MagicMock()
        child_delta.get_balance.return_value = Decimal("10000")
        child_delta.commodity = delta_commodity
        child_delta.children = []

        # Points parent (USD): get_balance fails because of Delta
        points_account = MagicMock()
        points_account.get_balance.side_effect = GncConversionError("Cannot convert")
        points_account.commodity = usd
        points_account.splits = []
        points_account.children = [child_aa, child_delta]

        # Checking (USD): works fine
        checking = MagicMock()
        checking.get_balance.return_value = Decimal("1000.00")
        checking.commodity = usd

        # Assets parent (USD): get_balance fails because Points fails
        assets = MagicMock()
        assets.get_balance.side_effect = GncConversionError("Cannot convert")
        assets.commodity = usd
        assets.splits = []
        assets.children = [checking, points_account]

        result = safe_balance(assets)
        # Checking: $1000 (same commodity, factor = 1)
        # Points: safe_balance = 5000 * 0.01 = $50 (AA converted, Delta skipped)
        # Points has same commodity (USD), so factor = 1
        # Total: $1000 + $50 = $1050
        assert result == Decimal("1050.00")
