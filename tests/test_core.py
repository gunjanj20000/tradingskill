"""Unit tests for Core utilities, Risk checks, and Budget sizing."""

import datetime
import unittest
from zoneinfo import ZoneInfo

from trader_core.formatting import format_inr, format_lakh_crore, format_pct
from trader_core.market_hours import IST, is_entry_allowed, is_trading_day
from trader_core.universe import clean_symbol, get_universe
from trader_budget.size import calculate_position_size
from trader_risk.check import get_order_fingerprint


class TestCoreUtilities(unittest.TestCase):

    def test_inr_formatting(self):
        self.assertEqual(format_inr(1000), "₹1,000.00")
        self.assertEqual(format_inr(150000), "₹1,50,000.00")
        self.assertEqual(format_inr(1234567.89), "₹12,34,567.89")
        self.assertEqual(format_inr(-50000), "-₹50,000.00")

    def test_lakh_crore_formatting(self):
        self.assertEqual(format_lakh_crore(250000), "₹2.50 L")
        self.assertEqual(format_lakh_crore(15000000), "₹1.50 Cr")

    def test_market_hours_and_holidays(self):
        # 2026-01-26 is Republic Day in India (National Holiday)
        rep_day = datetime.datetime(2026, 1, 26, 10, 0, tzinfo=IST)
        self.assertFalse(is_trading_day(rep_day))

        # Regular Tuesday
        tue = datetime.datetime(2026, 10, 20, 10, 30, tzinfo=IST)
        # Dussehra is 2026-10-20
        self.assertFalse(is_trading_day(tue))

        # Wednesday 2026-10-21 (normal trading day)
        wed = datetime.datetime(2026, 10, 21, 10, 30, tzinfo=IST)
        self.assertTrue(is_trading_day(wed))
        allowed, _ = is_entry_allowed(wed, no_entries_before="09:20", no_entries_after="14:45")
        self.assertTrue(allowed)

    def test_universe(self):
        self.assertEqual(clean_symbol("RELIANCE"), "RELIANCE.NS")
        self.assertEqual(clean_symbol("sbi"), "SBI.NS")
        self.assertEqual(clean_symbol("TCS.NS"), "TCS.NS")

        nifty50 = get_universe("nifty50")
        self.assertEqual(len(nifty50), 50)
        self.assertIn("RELIANCE.NS", nifty50)

    def test_budget_position_sizing(self):
        plan = {
            "symbol": "SBIN.NS",
            "entry_price": 1000.0,
            "stop_price": 990.0,
            "target_price": 1020.0,
            "risk_per_share": 10.0,
        }
        order = calculate_position_size(
            plan=plan,
            capital=100000.0,
            max_risk=1000.0,
            leverage=5.0,
            product="MIS",
            write=False,
        )
        self.assertEqual(order["quantity"], 100)
        self.assertEqual(order["total_risk_inr"], 1000.0)
        self.assertEqual(order["notional_value_inr"], 100000.0)
        self.assertEqual(order["margin_required_inr"], 20000.0)

    def test_order_fingerprint(self):
        ord1 = {
            "symbol": "SBIN.NS",
            "transaction_type": "BUY",
            "quantity": 100,
            "price": 1000.0,
            "stop_loss": 990.0,
            "take_profit": 1020.0,
        }
        fp1 = get_order_fingerprint(ord1)
        fp2 = get_order_fingerprint(ord1)
        self.assertEqual(fp1, fp2)

        ord2 = dict(ord1)
        ord2["quantity"] = 101
        self.assertNotEqual(fp1, get_order_fingerprint(ord2))


if __name__ == "__main__":
    unittest.main()
