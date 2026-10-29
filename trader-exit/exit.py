#!/usr/bin/env python3
"""Exit Planner for trader-exit (Indian Equities NSE/BSE).

Plans the Stop-Loss and Take-Profit targets BEFORE placing a trade.
Enforces Indian market rules (mandatory flat-by 15:15 IST before broker auto square-off).
Saves trade plan to trader/plan.json for timemachine, budget sizing, and risk checks.

Usage:
    python3 exit.py plan                                    # from trader/entry.json: ATR 1.5 stop, 2R target
    python3 exit.py plan --stop supertrend --target 2R --write
    python3 exit.py plan --stop vwap --target 1.5R --write
    python3 exit.py plan --symbol SBIN.NS --entry 971.90 --stop atr:1.5 --target 2R --write
    python3 exit.py show                                    # view current trader/plan.json
"""

import argparse
import datetime
import json
import os
import sys
from decimal import Decimal, ROUND_FLOOR, ROUND_HALF_UP

# Ensure project root is in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from trader_core.data_feed import fetch_bars
from trader_core.formatting import format_inr
from trader_core.universe import clean_symbol
from trader_indicators.indicators import TechnicalIndicators

DEFAULT_ENTRY_PATH = os.path.join(ROOT_DIR, "trader", "entry.json")
DEFAULT_PLAN_PATH = os.path.join(ROOT_DIR, "trader", "plan.json")
DEFAULT_CONFIG_PATH = os.path.join(ROOT_DIR, "trader", "config.json")


def load_config() -> dict:
    defaults = {"flat_by": "15:15", "min_reward_risk": 1.5}
    if os.path.exists(DEFAULT_CONFIG_PATH):
        try:
            with open(DEFAULT_CONFIG_PATH, "r") as f:
                user_cfg = json.load(f)
                defaults.update(user_cfg)
        except Exception:
            pass
    return defaults


def calculate_exit_plan(
    symbol: str | None = None,
    entry_price: float | None = None,
    stop_rule: str = "atr:1.5",
    target_rule: str = "2R",
    flat_by: str | None = None,
    write: bool = False,
) -> dict:
    """Compute risk, stop-loss, and target prices for a trade."""
    cfg = load_config()
    flat_by_time = flat_by or cfg.get("flat_by", "15:15")

    # If symbol or entry not provided, load from trader/entry.json
    entry_data = {}
    if symbol is None or entry_price is None:
        if not os.path.exists(DEFAULT_ENTRY_PATH):
            raise ValueError(f"No active entry found at {DEFAULT_ENTRY_PATH}. Provide --symbol and --entry explicitly.")
        with open(DEFAULT_ENTRY_PATH, "r") as f:
            entry_data = json.load(f)
        symbol = entry_data.get("symbol")
        entry_price = float(entry_data.get("trigger_price") or entry_data.get("latest_close"))

    symbol = clean_symbol(symbol)
    entry_dec = Decimal(str(round(entry_price, 2)))

    # Fetch bars for indicator-based stops (ATR, VWAP, SuperTrend, CPR)
    df = fetch_bars(symbol, period="5d", interval="15m", max_age_seconds=60)
    engine = TechnicalIndicators(df)
    all_ind = engine.compute_all()

    # 1. STOP CALCULATION
    stop_price = None
    stop_desc = ""

    if stop_rule.startswith("atr:"):
        mult = float(stop_rule.split(":")[1])
        atr_val = all_ind["volatility"]["atr14"]
        stop_val = entry_price - (mult * atr_val)
        stop_price = Decimal(str(round(stop_val, 2)))
        stop_desc = f"{mult}x ATR14 (₹{atr_val:.2f}) under entry"

    elif stop_rule == "supertrend":
        st_val = all_ind["trend"]["supertrend"]["value"]
        if st_val >= entry_price:
            st_val = entry_price * 0.99
        stop_price = Decimal(str(round(st_val, 2)))
        stop_desc = f"SuperTrend level (₹{st_val:.2f})"

    elif stop_rule == "vwap":
        vwap_val = all_ind["volume"]["vwap"]
        if vwap_val >= entry_price:
            vwap_val = entry_price * 0.99
        stop_price = Decimal(str(round(vwap_val, 2)))
        stop_desc = f"VWAP level (₹{vwap_val:.2f})"

    elif stop_rule == "cpr-bc":
        cpr_bc = all_ind["pivots"]["cpr"]["bc"]
        stop_price = Decimal(str(round(cpr_bc, 2)))
        stop_desc = f"Central Pivot Range BC (₹{cpr_bc:.2f})"

    elif stop_rule.startswith("pct:"):
        pct = float(stop_rule.split(":")[1])
        stop_val = entry_price * (1.0 - pct / 100.0)
        stop_price = Decimal(str(round(stop_val, 2)))
        stop_desc = f"{pct}% below entry"

    elif stop_rule.startswith("price:"):
        p = float(stop_rule.split(":")[1])
        stop_price = Decimal(str(round(p, 2)))
        stop_desc = f"Manual stop at ₹{p:.2f}"

    elif stop_rule == "suggested" and "suggested_stop" in entry_data:
        p = float(entry_data["suggested_stop"])
        stop_price = Decimal(str(round(p, 2)))
        stop_desc = f"Entry suggested stop at ₹{p:.2f}"

    else:
        # Default fallback: 1.5x ATR
        atr_val = all_ind["volatility"]["atr14"]
        stop_val = entry_price - (1.5 * atr_val)
        stop_price = Decimal(str(round(stop_val, 2)))
        stop_desc = f"1.5x ATR14 (₹{atr_val:.2f}) default stop"

    # Enforce stop price strictly below entry
    if stop_price >= entry_dec:
        stop_price = (entry_dec * Decimal("0.99")).quantize(Decimal("0.05"), rounding=ROUND_FLOOR)
        stop_desc += " (adjusted below entry)"

    risk_per_share = (entry_dec - stop_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if risk_per_share <= Decimal("0.10"):
        stop_price = (entry_dec * Decimal("0.995")).quantize(Decimal("0.05"), rounding=ROUND_FLOOR)
        risk_per_share = entry_dec - stop_price

    risk_pct = (risk_per_share / entry_dec) * Decimal("100")

    # 2. TARGET CALCULATION
    target_price = None
    target_desc = ""

    if target_rule.endswith("R"):
        r_mult = Decimal(target_rule[:-1])
        target_dec = entry_dec + (r_mult * risk_per_share)
        target_price = target_dec.quantize(Decimal("0.05"), rounding=ROUND_HALF_UP)
        target_desc = f"{r_mult}R Target ({float(r_mult):.1f}x Risk)"

    elif target_rule == "cpr-r1":
        r1 = Decimal(str(round(all_ind["pivots"]["cpr"]["r1"], 2)))
        target_price = r1
        target_desc = f"CPR Resistance R1 ({format_inr(float(r1))})"

    elif target_rule == "camarilla-h4":
        h4 = Decimal(str(round(all_ind["pivots"]["camarilla"]["h4"], 2)))
        target_price = h4
        target_desc = f"Camarilla H4 Breakout Target ({format_inr(float(h4))})"

    elif target_rule.startswith("price:"):
        p = Decimal(target_rule.split(":")[1])
        target_price = p
        target_desc = f"Manual target at ₹{float(p):.2f}"

    else:
        # Default: 2R
        target_price = (entry_dec + Decimal("2.0") * risk_per_share).quantize(Decimal("0.05"), rounding=ROUND_HALF_UP)
        target_desc = "2.0R Target (Default)"

    reward_per_share = target_price - entry_dec
    reward_risk_ratio = float(reward_per_share / risk_per_share) if risk_per_share > 0 else 0.0

    plan = {
        "symbol": symbol,
        "entry_price": float(entry_dec),
        "stop_price": float(stop_price),
        "target_price": float(target_price),
        "risk_per_share": float(risk_per_share),
        "risk_pct": round(float(risk_pct), 2),
        "reward_per_share": float(reward_per_share),
        "reward_risk_ratio": round(reward_risk_ratio, 2),
        "stop_rule": stop_rule,
        "stop_desc": stop_desc,
        "target_rule": target_rule,
        "target_desc": target_desc,
        "flat_by": flat_by_time,
        "plan_timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "vwap": all_ind["volume"]["vwap"],
        "atr14": all_ind["volatility"]["atr14"],
    }

    if write:
        os.makedirs(os.path.dirname(DEFAULT_PLAN_PATH), exist_ok=True)
        with open(DEFAULT_PLAN_PATH, "w") as f:
            json.dump(plan, f, indent=2)
        print(f"[*] Trade plan saved to {DEFAULT_PLAN_PATH}")

    return plan


def print_plan_terminal(plan: dict):
    print("=" * 72)
    print(f" TRADE EXIT & RISK PLAN: {plan['symbol']} | ENTRY: {format_inr(plan['entry_price'])}")
    print("=" * 72)
    print(f" Stop-Loss:      {format_inr(plan['stop_price']):<14} ({plan['stop_desc']})")
    print(f" Take-Profit:    {format_inr(plan['target_price']):<14} ({plan['target_desc']})")
    print("-" * 72)
    print(f" Risk per Share: {format_inr(plan['risk_per_share']):<14} ({plan['risk_pct']}% of stock price)")
    print(f" Reward / Share: {format_inr(plan['reward_per_share']):<14} (Reward:Risk = 1:{plan['reward_risk_ratio']:.2f})")
    print(f" Square-off:     {plan['flat_by']} IST (Mandatory intraday exit)")
    print("=" * 72)


def main():
    parser = argparse.ArgumentParser(description="Exit Planner for Indian Equities (NSE/BSE)")
    subparsers = parser.add_subparsers(dest="command")

    # Command: plan
    plan_p = subparsers.add_parser("plan", help="Compute trade plan")
    plan_p.add_argument("--symbol", help="Stock ticker (or reads trader/entry.json)")
    plan_p.add_argument("--entry", type=float, help="Entry price in INR")
    plan_p.add_argument("--stop", default="atr:1.5", help="Stop rule: atr:1.5, supertrend, vwap, cpr-bc, pct:1.0, price:X (default: atr:1.5)")
    plan_p.add_argument("--target", default="2R", help="Target rule: 1R, 1.5R, 2R, 3R, cpr-r1, camarilla-h4, price:X (default: 2R)")
    plan_p.add_argument("--flat-by", default="15:15", help="Mandatory square-off IST time (default: 15:15)")
    plan_p.add_argument("--write", action="store_true", help="Save plan to trader/plan.json")
    plan_p.add_argument("--json", action="store_true", help="Output JSON")

    # Command: show
    show_p = subparsers.add_parser("show", help="Display current trader/plan.json")

    args = parser.parse_args()

    if args.command == "plan" or args.command is None:
        try:
            plan = calculate_exit_plan(
                symbol=getattr(args, "symbol", None),
                entry_price=getattr(args, "entry", None),
                stop_rule=getattr(args, "stop", "atr:1.5"),
                target_rule=getattr(args, "target", "2R"),
                flat_by=getattr(args, "flat_by", "15:15"),
                write=getattr(args, "write", False),
            )
            if getattr(args, "json", False):
                print(json.dumps(plan, indent=2))
            else:
                print_plan_terminal(plan)
            sys.exit(0)
        except Exception as e:
            print(f"Error creating trade plan: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "show":
        if not os.path.exists(DEFAULT_PLAN_PATH):
            print(f"No plan file found at {DEFAULT_PLAN_PATH}. Run 'python3 exit.py plan --write' first.", file=sys.stderr)
            sys.exit(1)
        with open(DEFAULT_PLAN_PATH, "r") as f:
            plan = json.load(f)
        print_plan_terminal(plan)
        sys.exit(0)


if __name__ == "__main__":
    main()
