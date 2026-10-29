#!/usr/bin/env python3
"""Pre-Trade Risk Manager for Indian Equities (NSE/BSE).

Inspects proposed orders in trader/orders.json against user rules (trader/config.json)
and today's execution state.
Grants PASS or BLOCK with specific reasons.
Records verified verdicts into trader/state/risk.json.

Usage:
    python3 check.py                                   # reads trader/orders.json
    python3 check.py --ignore-time-check              # for offline analysis / testing
    python3 check.py --json
"""

import argparse
import datetime
import hashlib
import json
import os
import sys

# Ensure project root is in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from trader_core.formatting import format_inr
from trader_core.market_hours import is_entry_allowed, now_ist
from trader_core.universe import clean_symbol

DEFAULT_CONFIG_PATH = os.path.join(ROOT_DIR, "trader", "config.json")
DEFAULT_ORDERS_PATH = os.path.join(ROOT_DIR, "trader", "orders.json")
DEFAULT_RISK_STATE_PATH = os.path.join(ROOT_DIR, "trader", "state", "risk.json")
DEFAULT_BROKER_STATE_PATH = os.path.join(ROOT_DIR, "trader", "state", "broker.json")


def load_config() -> dict:
    defaults = {
        "account_capital_inr": 100000.0,
        "max_risk_per_trade_inr": 1000.0,
        "max_daily_loss_inr": 3000.0,
        "max_trades_per_day": 5,
        "max_open_positions": 3,
        "min_reward_risk": 1.5,
        "no_entries_before": "09:20",
        "no_entries_after": "14:45",
        "flat_by": "15:15",
        "require_stop": True,
        "blocked_symbols": [],
    }
    if os.path.exists(DEFAULT_CONFIG_PATH):
        try:
            with open(DEFAULT_CONFIG_PATH, "r") as f:
                user_cfg = json.load(f)
                defaults.update(user_cfg)
        except Exception:
            pass
    return defaults


def get_order_fingerprint(order: dict) -> str:
    """Generate SHA256 signature for order integrity check."""
    s = f"{order.get('symbol')}:{order.get('transaction_type')}:{order.get('quantity')}:{order.get('price')}:{order.get('stop_loss')}:{order.get('take_profit')}"
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def run_risk_check(
    orders_path: str = DEFAULT_ORDERS_PATH,
    ignore_time_check: bool = False,
    write: bool = True,
) -> tuple[bool, list[dict]]:
    """Validate all orders against risk limits."""
    if not os.path.exists(orders_path):
        raise FileNotFoundError(f"Orders file not found at {orders_path}. Run trader-budget/size.py first.")

    with open(orders_path, "r") as f:
        orders_data = json.load(f)

    orders = orders_data.get("orders", [])
    if not orders:
        return True, []

    cfg = load_config()
    broker_history = []
    if os.path.exists(DEFAULT_BROKER_STATE_PATH):
        try:
            with open(DEFAULT_BROKER_STATE_PATH, "r") as f:
                broker_history = json.load(f).get("trades_today", [])
        except Exception:
            broker_history = []

    today_trades_count = len(broker_history)
    today_cumulative_risk = sum(float(t.get("risk_inr", 0.0)) for t in broker_history)

    verdicts = []
    all_passed = True

    for ord_item in orders:
        reasons_blocked = []
        warnings = []
        sym = clean_symbol(ord_item.get("symbol", ""))
        qty = int(ord_item.get("quantity", 0))
        entry_p = float(ord_item.get("price", 0.0))
        stop_p = float(ord_item.get("stop_loss", 0.0))
        target_p = float(ord_item.get("take_profit", 0.0))
        margin_req = float(ord_item.get("margin_required_inr", 0.0))
        total_risk = float(ord_item.get("total_risk_inr", 0.0))

        # 1. Format check
        if not sym or qty <= 0 or entry_p <= 0:
            reasons_blocked.append("Invalid order format (symbol, quantity, or price <= 0)")

        # 2. Blocked symbols (ASM/GSM list)
        if sym in cfg.get("blocked_symbols", []):
            reasons_blocked.append(f"Symbol '{sym}' is on your blocked list (ASM/GSM surveillance)")

        # 3. Stop requirement
        if cfg.get("require_stop", True):
            if stop_p <= 0:
                reasons_blocked.append("Stop-loss is required but missing or zero")
            elif stop_p >= entry_p:
                reasons_blocked.append(f"Stop-loss ({format_inr(stop_p)}) must be strictly below entry price ({format_inr(entry_p)})")

        # 4. Max risk per trade
        max_risk_limit = float(cfg.get("max_risk_per_trade_inr", 1000.0))
        if total_risk > (max_risk_limit * 1.05):  # allow 5% rounding tolerance
            reasons_blocked.append(f"Trade risk {format_inr(total_risk)} exceeds max allowed risk {format_inr(max_risk_limit)}")

        # 5. Reward to Risk
        risk_per_sh = entry_p - stop_p
        reward_per_sh = target_p - entry_p
        rr_ratio = reward_per_sh / risk_per_sh if risk_per_sh > 0 else 0.0
        min_rr = float(cfg.get("min_reward_risk", 1.5))
        if rr_ratio < (min_rr - 0.05):
            reasons_blocked.append(f"Reward:Risk ratio (1:{rr_ratio:.2f}) is below minimum required 1:{min_rr:.2f}")

        # 6. Cumulative Daily Loss Guard
        max_daily_loss = float(cfg.get("max_daily_loss_inr", 3000.0))
        if (today_cumulative_risk + total_risk) > max_daily_loss:
            reasons_blocked.append(f"Cumulative daily risk ({format_inr(today_cumulative_risk + total_risk)}) exceeds max daily loss {format_inr(max_daily_loss)}")

        # 7. Max trades per day
        max_trades = int(cfg.get("max_trades_per_day", 5))
        if today_trades_count >= max_trades:
            reasons_blocked.append(f"Reached max allowed trades per day ({max_trades})")

        # 8. Available Capital & Margin
        capital = float(cfg.get("account_capital_inr", 100000.0))
        if margin_req > capital:
            reasons_blocked.append(f"Margin required {format_inr(margin_req)} exceeds account capital {format_inr(capital)}")

        # 9. IST Market Window Check
        if not ignore_time_check:
            allowed, window_msg = is_entry_allowed(
                no_entries_before=cfg.get("no_entries_before", "09:20"),
                no_entries_after=cfg.get("no_entries_after", "14:45"),
            )
            if not allowed:
                reasons_blocked.append(f"Outside permitted trading window: {window_msg}")

        status = "BLOCK" if reasons_blocked else "PASS"
        if status == "BLOCK":
            all_passed = False

        fp = get_order_fingerprint(ord_item)
        verdicts.append({
            "symbol": sym,
            "status": status,
            "fingerprint": fp,
            "reasons": reasons_blocked if reasons_blocked else ["All risk constraints satisfied"],
            "warnings": warnings,
            "order": ord_item,
        })

    if write:
        os.makedirs(os.path.dirname(DEFAULT_RISK_STATE_PATH), exist_ok=True)
        with open(DEFAULT_RISK_STATE_PATH, "w") as f:
            json.dump({
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
                "all_passed": all_passed,
                "verdicts": verdicts,
            }, f, indent=2)
        print(f"[*] Risk check verdicts saved to {DEFAULT_RISK_STATE_PATH}")

    return all_passed, verdicts


def main():
    parser = argparse.ArgumentParser(description="Pre-Trade Risk Manager for Indian Equities")
    parser.add_argument("--orders", default=DEFAULT_ORDERS_PATH, help="Path to orders.json")
    parser.add_argument("--ignore-time-check", action="store_true", help="Bypass IST market hours window check")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    try:
        passed, verdicts = run_risk_check(
            orders_path=args.orders,
            ignore_time_check=args.ignore_time_check,
            write=True,
        )

        if args.json:
            print(json.dumps({"all_passed": passed, "verdicts": verdicts}, indent=2))
        else:
            print("=" * 72)
            print(" PRE-TRADE RISK CHECK VERDICTS (SEBI & ACCOUNT RULES)")
            print("=" * 72)
            for v in verdicts:
                status_color = "\033[92mPASS\033[0m" if v["status"] == "PASS" else "\033[91mBLOCK\033[0m"
                print(f" {v['symbol']:<15} -> {status_color} (Fingerprint: {v['fingerprint']})")
                for r in v["reasons"]:
                    prefix = "  [✓]" if v["status"] == "PASS" else "  [X]"
                    print(f"  {prefix} {r}")
                print("-" * 72)
            print(f" FINAL RESULT: {'ALL ORDERS APPROVED FOR EXECUTION' if passed else 'ONE OR MORE ORDERS BLOCKED'}")
            print("=" * 72)

        sys.exit(0 if passed else 1)
    except Exception as e:
        print(f"Error executing risk check: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
