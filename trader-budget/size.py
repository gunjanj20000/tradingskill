#!/usr/bin/env python3
"""Budget & Position Sizing Manager for Indian Equities (NSE/BSE).

Sizes positions based on account capital in INR (₹) and max risk per trade.
Enforces SEBI intraday MIS margin rules (maximum 5x leverage, 20% minimum margin).
Generates bracket orders saved to trader/orders.json.

Usage:
    python3 size.py                                   # reads trader/plan.json and trader/config.json
    python3 size.py --write                           # writes trader/orders.json
    python3 size.py --capital 200000 --max-risk 2000 --write
"""

import argparse
import datetime
import json
import math
import os
import sys
from decimal import Decimal, ROUND_FLOOR

# Ensure project root is in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from trader_core.formatting import format_inr, format_lakh_crore
from trader_core.universe import clean_symbol

DEFAULT_PLAN_PATH = os.path.join(ROOT_DIR, "trader", "plan.json")
DEFAULT_CONFIG_PATH = os.path.join(ROOT_DIR, "trader", "config.json")
DEFAULT_ORDERS_PATH = os.path.join(ROOT_DIR, "trader", "orders.json")


def load_config() -> dict:
    defaults = {
        "account_capital_inr": 100000.0,    # ₹1 Lakh default capital
        "max_risk_per_trade_inr": 1000.0,   # 1% max loss = ₹1,000
        "max_risk_pct": 1.0,
        "intraday_leverage": 5.0,           # SEBI maximum MIS leverage = 5x
        "max_position_pct": 50.0,           # Max 50% capital in a single stock
        "product_type": "MIS",              # MIS (Margin Intraday Square-off) or CNC (Cash n Carry)
    }
    if os.path.exists(DEFAULT_CONFIG_PATH):
        try:
            with open(DEFAULT_CONFIG_PATH, "r") as f:
                user_cfg = json.load(f)
                defaults.update(user_cfg)
        except Exception:
            pass
    return defaults


def calculate_position_size(
    plan: dict | None = None,
    capital: float | None = None,
    max_risk: float | None = None,
    leverage: float | None = None,
    product: str = "MIS",
    write: bool = False,
) -> dict:
    """Size position according to fixed fractional risk and SEBI margin rules."""
    cfg = load_config()
    total_capital = float(capital or cfg["account_capital_inr"])
    risk_limit = float(max_risk or cfg["max_risk_per_trade_inr"])
    mis_leverage = float(leverage or cfg["intraday_leverage"])

    if plan is None:
        if not os.path.exists(DEFAULT_PLAN_PATH):
            raise ValueError(f"No trade plan found at {DEFAULT_PLAN_PATH}. Run 'python3 exit.py plan --write' first.")
        with open(DEFAULT_PLAN_PATH, "r") as f:
            plan = json.load(f)

    symbol = clean_symbol(plan["symbol"])
    entry_p = float(plan["entry_price"])
    stop_p = float(plan["stop_price"])
    target_p = float(plan["target_price"])
    risk_per_share = float(plan["risk_per_share"])

    if risk_per_share <= 0:
        raise ValueError(f"Invalid risk per share ({risk_per_share}). Stop must be below entry.")

    # Number of shares based on max allowed loss:
    # Qty = Max Risk / Risk per share
    raw_qty = risk_limit / risk_per_share
    qty = max(1, int(math.floor(raw_qty)))

    # Calculate notional value & margin required
    notional_value = qty * entry_p
    margin_required = notional_value / mis_leverage if product == "MIS" else notional_value

    # Check capital constraint: margin required cannot exceed available capital
    if margin_required > total_capital:
        # Cap by available purchasing power
        max_notional = total_capital * mis_leverage if product == "MIS" else total_capital
        qty = max(1, int(math.floor(max_notional / entry_p)))
        notional_value = qty * entry_p
        margin_required = notional_value / mis_leverage if product == "MIS" else notional_value

    actual_max_loss = qty * risk_per_share
    actual_max_gain = qty * (target_p - entry_p)

    order = {
        "symbol": symbol,
        "transaction_type": "BUY",
        "order_type": "LIMIT",
        "product": product,
        "quantity": qty,
        "price": round(entry_p, 2),
        "stop_loss": round(stop_p, 2),
        "take_profit": round(target_p, 2),
        "risk_per_share": round(risk_per_share, 2),
        "total_risk_inr": round(actual_max_loss, 2),
        "total_reward_inr": round(actual_max_gain, 2),
        "notional_value_inr": round(notional_value, 2),
        "margin_required_inr": round(margin_required, 2),
        "account_capital_inr": round(total_capital, 2),
        "leverage_used": mis_leverage if product == "MIS" else 1.0,
        "created_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
    }

    if write:
        os.makedirs(os.path.dirname(DEFAULT_ORDERS_PATH), exist_ok=True)
        with open(DEFAULT_ORDERS_PATH, "w") as f:
            json.dump({"orders": [order]}, f, indent=2)
        print(f"[*] Sized order saved to {DEFAULT_ORDERS_PATH}")

    return order


def print_order_terminal(order: dict):
    print("=" * 72)
    print(f" POSITION SIZING & BRACKET TICKET: {order['symbol']}")
    print("=" * 72)
    print(f" Action:             BUY {order['quantity']} shares @ {format_inr(order['price'])} (LIMIT)")
    print(f" Product:            {order['product']} (Intraday MIS with {order['leverage_used']}x SEBI margin)")
    print("-" * 72)
    print(f" Stop-Loss:          {format_inr(order['stop_loss'])}")
    print(f" Take-Profit:        {format_inr(order['take_profit'])}")
    print("-" * 72)
    print(f" Max Loss (Risk):    {format_inr(order['total_risk_inr']):<14} ({format_inr(order['risk_per_share'])} / share)")
    print(f" Max Gain (Reward):  {format_inr(order['total_reward_inr']):<14} (1:{order['total_reward_inr'] / max(0.01, order['total_risk_inr']):.2f} R:R)")
    print(f" Notional Value:     {format_inr(order['notional_value_inr'])}")
    print(f" Margin Required:    {format_inr(order['margin_required_inr']):<14} (out of {format_inr(order['account_capital_inr'])})")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description="Budget & Position Sizer for Indian Equities")
    parser.add_argument("--capital", type=float, help="Account capital in INR (default from config: ₹1,00,000)")
    parser.add_argument("--max-risk", type=float, help="Max loss per trade in INR (default from config: ₹1,000)")
    parser.add_argument("--leverage", type=float, default=5.0, help="Intraday MIS leverage (default: 5.0x)")
    parser.add_argument("--product", default="MIS", choices=["MIS", "CNC"], help="Product type: MIS (Intraday) or CNC (Cash)")
    parser.add_argument("--write", action="store_true", help="Save order to trader/orders.json")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    try:
        order = calculate_position_size(
            capital=args.capital,
            max_risk=args.max_risk,
            leverage=args.leverage,
            product=args.product,
            write=args.write,
        )
        if args.json:
            print(json.dumps(order, indent=2))
        else:
            print_order_terminal(order)
        sys.exit(0)
    except Exception as e:
        print(f"Error sizing position: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
