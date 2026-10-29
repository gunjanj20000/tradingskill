#!/usr/bin/env python3
"""Technical & Price Alert Engine for Indian Stocks (NSE/BSE).

Monitors stops, targets, VWAP crossovers, and the 15:15 IST mandatory square-off alert.
Maintains state in trader/alerts.json.

Usage:
    python3 alerts.py add --from-plan                       # adds stop, target, and 15:15 alert from plan
    python3 alerts.py add --symbol SBIN.NS --price 975.00 --condition above --note "Resistance test"
    python3 alerts.py check                                 # checks live prices and triggers alerts
    python3 alerts.py list                                  # lists active alerts
"""

import argparse
import datetime
import json
import os
import sys

# Ensure project root is in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from trader_core.data_feed import get_latest_price
from trader_core.formatting import format_inr
from trader_core.market_hours import now_ist
from trader_core.universe import clean_symbol

DEFAULT_PLAN_PATH = os.path.join(ROOT_DIR, "trader", "plan.json")
DEFAULT_ALERTS_PATH = os.path.join(ROOT_DIR, "trader", "alerts.json")


def load_alerts() -> list[dict]:
    if os.path.exists(DEFAULT_ALERTS_PATH):
        try:
            with open(DEFAULT_ALERTS_PATH, "r") as f:
                return json.load(f).get("alerts", [])
        except Exception:
            pass
    return []


def save_alerts(alerts: list[dict]):
    os.makedirs(os.path.dirname(DEFAULT_ALERTS_PATH), exist_ok=True)
    with open(DEFAULT_ALERTS_PATH, "w") as f:
        json.dump({"alerts": alerts, "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")}, f, indent=2)


def add_from_plan():
    if not os.path.exists(DEFAULT_PLAN_PATH):
        print(f"Plan file not found: {DEFAULT_PLAN_PATH}. Run exit.py plan --write first.", file=sys.stderr)
        sys.exit(1)

    with open(DEFAULT_PLAN_PATH, "r") as f:
        plan = json.load(f)

    sym = plan["symbol"]
    stop_p = plan["stop_price"]
    target_p = plan["target_price"]
    flat_by = plan.get("flat_by", "15:15")

    alerts = load_alerts()

    # Avoid duplicate plan alerts for same symbol
    alerts = [a for a in alerts if not (a.get("symbol") == sym and a.get("type") in ["stop", "target", "flat_by"])]

    alerts.append({
        "id": f"ALT-{sym}-STOP",
        "symbol": sym,
        "type": "stop",
        "threshold_price": stop_p,
        "condition": "below_or_equal",
        "note": f"STOP-LOSS HIT: Flatten {sym} immediately",
        "triggered": False,
    })
    alerts.append({
        "id": f"ALT-{sym}-TARGET",
        "symbol": sym,
        "type": "target",
        "threshold_price": target_p,
        "condition": "above_or_equal",
        "note": f"PROFIT TARGET REACHED: Take profit on {sym}",
        "triggered": False,
    })
    alerts.append({
        "id": f"ALT-{sym}-FLAT",
        "symbol": sym,
        "type": "time",
        "target_time": flat_by,
        "condition": "time_reached",
        "note": f"INTRADAY SQUARE-OFF CUTOFF: Flatten {sym} before {flat_by} IST broker penalty",
        "triggered": False,
    })

    save_alerts(alerts)
    print(f"[*] Added Stop ({format_inr(stop_p)}), Target ({format_inr(target_p)}), and {flat_by} IST flat-by alerts for {sym}.")


def check_alerts():
    alerts = load_alerts()
    if not alerts:
        print("No active alerts to monitor.")
        return

    curr_time = now_ist()
    time_str = curr_time.strftime("%H:%M")
    triggered_any = False

    print("=" * 76)
    print(f" PRICE & TECHNICAL ALERTS CHECK ({curr_time.strftime('%Y-%m-%d %H:%M:%S IST')})")
    print("=" * 76)

    for a in alerts:
        if a.get("triggered", False):
            continue

        a_type = a.get("type")
        sym = a.get("symbol")

        if a_type in ["stop", "target", "price"]:
            try:
                ltp = get_latest_price(sym)
            except Exception:
                continue

            th = float(a["threshold_price"])
            cond = a["condition"]
            is_hit = False

            if cond in ["below_or_equal", "below"] and ltp <= th:
                is_hit = True
            elif cond in ["above_or_equal", "above"] and ltp >= th:
                is_hit = True

            if is_hit:
                a["triggered"] = True
                a["triggered_at"] = curr_time.strftime("%Y-%m-%d %H:%M:%S IST")
                a["triggered_price"] = ltp
                triggered_any = True
                badge = "\033[91mSTOP HIT\033[0m" if a_type == "stop" else "\033[92mTARGET HIT\033[0m"
                print(f" [!] {badge}: {sym} LTP is {format_inr(ltp)} ({a['note']})")
            else:
                print(f"  [-] {sym:<12} LTP: {format_inr(ltp):<12} Target/Stop: {format_inr(th):<12} (Active)")

        elif a_type == "time":
            target_t = a.get("target_time", "15:15")
            if time_str >= target_t:
                a["triggered"] = True
                a["triggered_at"] = curr_time.strftime("%Y-%m-%d %H:%M:%S IST")
                triggered_any = True
                print(f" [!] \033[93mTIME CUTOFF REACHED\033[0m: {a['note']}")

    save_alerts(alerts)
    print("=" * 76)


def list_alerts():
    alerts = load_alerts()
    print("=" * 76)
    print(f" ACTIVE ALERTS MONITOR ({len(alerts)} ALERTS CONFIGURED)")
    print("=" * 76)
    if not alerts:
        print("  No alerts configured.")
    else:
        for a in alerts:
            status = "\033[91mTRIGGERED\033[0m" if a.get("triggered") else "\033[92mACTIVE\033[0m"
            desc = f"Price {format_inr(a.get('threshold_price'))}" if "threshold_price" in a else f"Time {a.get('target_time')}"
            print(f"  {a['id']:<24} {a['symbol']:<12} {desc:<18} [{status}] {a['note']}")
    print("=" * 76)


def main():
    parser = argparse.ArgumentParser(description="Alert Engine for Indian Equities")
    subparsers = parser.add_subparsers(dest="command")

    add_p = subparsers.add_parser("add", help="Add an alert")
    add_p.add_argument("--from-plan", action="store_true", help="Add stop/target from trader/plan.json")
    add_p.add_argument("--symbol", help="Stock ticker")
    add_p.add_argument("--price", type=float, help="Threshold price")
    add_p.add_argument("--condition", default="above", choices=["above", "below"])
    add_p.add_argument("--note", default="Price alert")

    subparsers.add_parser("check", help="Check and trigger alerts")
    subparsers.add_parser("list", help="List all alerts")

    args = parser.parse_args()

    if args.command == "add":
        if args.from_plan:
            add_from_plan()
        elif args.symbol and args.price:
            alerts = load_alerts()
            alerts.append({
                "id": f"ALT-{args.symbol}-{len(alerts)+1}",
                "symbol": clean_symbol(args.symbol),
                "type": "price",
                "threshold_price": args.price,
                "condition": args.condition,
                "note": args.note,
                "triggered": False,
            })
            save_alerts(alerts)
            print(f"[*] Added alert for {args.symbol} at {format_inr(args.price)}")
    elif args.command == "check" or args.command is None:
        check_alerts()
    elif args.command == "list":
        list_alerts()


if __name__ == "__main__":
    main()
