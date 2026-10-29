#!/usr/bin/env python3
"""Order Executor & Broker Connector for Indian Equities (NSE/BSE).

Presents formatted trade tickets, verifies trader-risk cryptographic approval,
and executes orders (paper trading by default; live export for Zerodha, Angel One, Groww, Dhan, Upstox, Fyers).
STRICT SAFETY CONTROL: Never places an order without explicit confirmation ("yes").

Usage:
    python3 ticket.py show                                # display tickets and readiness
    python3 ticket.py execute --confirm "yes"             # paper executes approved order
    python3 ticket.py export --broker zerodha             # generate Zerodha Kite Connect payload
    python3 ticket.py export --broker angelone            # generate Angel One SmartAPI payload
    python3 ticket.py status                              # view active positions & P&L
    python3 ticket.py squareoff --confirm "yes"           # square off open intraday position
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
from trader_core.formatting import format_inr, format_pct
from trader_core.universe import clean_symbol

DEFAULT_ORDERS_PATH = os.path.join(ROOT_DIR, "trader", "orders.json")
DEFAULT_RISK_PATH = os.path.join(ROOT_DIR, "trader", "state", "risk.json")
DEFAULT_BROKER_STATE = os.path.join(ROOT_DIR, "trader", "state", "broker.json")
DEFAULT_PORTFOLIO_PATH = os.path.join(ROOT_DIR, "trader", "state", "portfolio.json")
DEFAULT_CONFIG_PATH = os.path.join(ROOT_DIR, "trader", "config.json")


def load_risk_verdicts() -> dict:
    if not os.path.exists(DEFAULT_RISK_PATH):
        return {}
    with open(DEFAULT_RISK_PATH, "r") as f:
        data = json.load(f)
    return {v["fingerprint"]: v for v in data.get("verdicts", [])}


def load_orders() -> list[dict]:
    if not os.path.exists(DEFAULT_ORDERS_PATH):
        return []
    with open(DEFAULT_ORDERS_PATH, "r") as f:
        data = json.load(f)
    return data.get("orders", [])


def load_portfolio() -> dict:
    if os.path.exists(DEFAULT_PORTFOLIO_PATH):
        try:
            with open(DEFAULT_PORTFOLIO_PATH, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "cash_balance_inr": 100000.0,
        "positions": [],
        "closed_trades": [],
        "realized_pnl_inr": 0.0,
    }


def save_portfolio(p: dict):
    os.makedirs(os.path.dirname(DEFAULT_PORTFOLIO_PATH), exist_ok=True)
    with open(DEFAULT_PORTFOLIO_PATH, "w") as f:
        json.dump(p, f, indent=2)


def show_tickets():
    orders = load_orders()
    if not orders:
        print("No orders found in trader/orders.json. Run trader-budget/size.py first.")
        return

    verdicts = load_risk_verdicts()
    from trader_risk.check import get_order_fingerprint

    print("=" * 76)
    print(" ORDER EXECUTION TICKETS (PAPER TRADING DEFAULT)")
    print("=" * 76)

    for i, ord_item in enumerate(orders, 1):
        fp = get_order_fingerprint(ord_item)
        risk_v = verdicts.get(fp)
        is_ready = risk_v and risk_v.get("status") == "PASS"
        ready_badge = "\033[92mREADY TO EXECUTE\033[0m" if is_ready else "\033[91mNOT READY (Risk Check Required)\033[0m"

        print(f" Ticket #{i}: {ord_item['symbol']} | Status: {ready_badge}")
        print(f"  Order:     {ord_item['transaction_type']} {ord_item['quantity']} shares @ {format_inr(ord_item['price'])} ({ord_item['order_type']})")
        print(f"  Product:   {ord_item['product']} (Intraday MIS, {ord_item['leverage_used']}x leverage)")
        print(f"  Brackets:  Stop-Loss: {format_inr(ord_item['stop_loss'])} | Take-Profit: {format_inr(ord_item['take_profit'])}")
        print(f"  Financials:Risk: {format_inr(ord_item['total_risk_inr'])} | Reward: {format_inr(ord_item['total_reward_inr'])} | Margin: {format_inr(ord_item['margin_required_inr'])}")
        print(f"  Fingerprint: {fp}")
        if not is_ready:
            print("  Note: Run 'python3 trader-risk/check.py --ignore-time-check' to approve.")
        print("-" * 76)


def execute_paper_order(confirm: str):
    if confirm.lower() != "yes":
        print("Execution cancelled: You must supply --confirm 'yes' to place an order.", file=sys.stderr)
        sys.exit(1)

    orders = load_orders()
    if not orders:
        print("No orders to execute in trader/orders.json", file=sys.stderr)
        sys.exit(1)

    verdicts = load_risk_verdicts()
    from trader_risk.check import get_order_fingerprint

    portfolio = load_portfolio()
    executed_count = 0

    for ord_item in orders:
        fp = get_order_fingerprint(ord_item)
        risk_v = verdicts.get(fp)
        if not risk_v or risk_v.get("status") != "PASS":
            print(f"[-] Skipped {ord_item['symbol']}: Order has not passed trader-risk check.", file=sys.stderr)
            continue

        # Execute paper trade
        fill_price = ord_item["price"]
        qty = ord_item["quantity"]
        margin_used = ord_item["margin_required_inr"]

        position = {
            "order_id": f"ORD-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            "symbol": ord_item["symbol"],
            "side": ord_item["transaction_type"],
            "quantity": qty,
            "fill_price": fill_price,
            "stop_loss": ord_item["stop_loss"],
            "take_profit": ord_item["take_profit"],
            "product": ord_item["product"],
            "margin_used_inr": margin_used,
            "entry_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
            "status": "OPEN",
        }

        portfolio["positions"].append(position)
        portfolio["cash_balance_inr"] -= margin_used

        # Record in broker state
        os.makedirs(os.path.dirname(DEFAULT_BROKER_STATE), exist_ok=True)
        broker_state = {"trades_today": []}
        if os.path.exists(DEFAULT_BROKER_STATE):
            try:
                with open(DEFAULT_BROKER_STATE, "r") as f:
                    broker_state = json.load(f)
            except Exception:
                pass
        broker_state["trades_today"].append({
            "symbol": ord_item["symbol"],
            "quantity": qty,
            "price": fill_price,
            "risk_inr": ord_item["total_risk_inr"],
            "time": position["entry_time"],
        })
        with open(DEFAULT_BROKER_STATE, "w") as f:
            json.dump(broker_state, f, indent=2)

        executed_count += 1
        print("=" * 72)
        print(f" [✓] PAPER TRADE EXECUTED: {position['order_id']}")
        print(f"     BOUGHT {qty} {ord_item['symbol']} @ {format_inr(fill_price)}")
        print(f"     Stop-Loss: {format_inr(ord_item['stop_loss'])} | Target: {format_inr(ord_item['take_profit'])}")
        print(f"     Margin Allocated: {format_inr(margin_used)} | Remaining Cash: {format_inr(portfolio['cash_balance_inr'])}")
        print("=" * 72)

    save_portfolio(portfolio)
    sys.exit(0 if executed_count > 0 else 1)


def generate_broker_payload(broker_name: str):
    orders = load_orders()
    if not orders:
        print("No orders found to export.", file=sys.stderr)
        return

    ord_item = orders[0]
    nse_sym = ord_item["symbol"].replace(".NS", "").replace(".BO", "")
    qty = ord_item["quantity"]
    price = ord_item["price"]
    stop_p = ord_item["stop_loss"]
    target_p = ord_item["take_profit"]

    b = broker_name.lower()
    print("=" * 76)
    print(f" BROKER API PAYLOAD EXPORT: {broker_name.upper()} ({ord_item['symbol']})")
    print("=" * 76)

    if b == "zerodha":
        print("""# Zerodha Kite Connect Python SDK:
from kiteconnect import KiteConnect

kite = KiteConnect(api_key="your_api_key")
kite.set_access_token("your_access_token")

# 1. Main Entry Order (Intraday MIS)
order_id = kite.place_order(
    variety=kite.VARIETY_REGULAR,
    exchange=kite.EXCHANGE_NSE,
    tradingsymbol="{sym}",
    transaction_type=kite.TRANSACTION_TYPE_BUY,
    quantity={qty},
    product=kite.PRODUCT_MIS,
    order_type=kite.ORDER_TYPE_LIMIT,
    price={price}
)

# 2. Stop-Loss Trigger (SL-M)
sl_order = kite.place_order(
    variety=kite.VARIETY_REGULAR,
    exchange=kite.EXCHANGE_NSE,
    tradingsymbol="{sym}",
    transaction_type=kite.TRANSACTION_TYPE_SELL,
    quantity={qty},
    product=kite.PRODUCT_MIS,
    order_type=kite.ORDER_TYPE_SLM,
    trigger_price={stop_p}
)
""".format(sym=nse_sym, qty=qty, price=price, stop_p=stop_p))

    elif b == "angelone":
        print("""// Angel One SmartAPI JSON Payload:
{{
  "variety": "NORMAL",
  "tradingsymbol": "{sym}-EQ",
  "symboltoken": "3045",
  "transactiontype": "BUY",
  "exchange": "NSE",
  "ordertype": "LIMIT",
  "producttype": "INTRADAY",
  "duration": "DAY",
  "price": "{price}",
  "quantity": "{qty}"
}}
""".format(sym=nse_sym, qty=qty, price=price))

    elif b == "dhan":
        print("""// Dhan HQ API JSON Payload:
{{
  "dhanClientId": "your_client_id",
  "transactionType": "BUY",
  "exchangeSegment": "NSE_EQ",
  "productType": "INTRADAY",
  "orderType": "LIMIT",
  "tradingSymbol": "{sym}",
  "securityId": "11536",
  "quantity": {qty},
  "price": {price}
}}
""".format(sym=nse_sym, qty=qty, price=price))

    else:
        print("""// Generic Indian Broker Webhook:
{{
  "exchange": "NSE",
  "symbol": "{sym}",
  "side": "BUY",
  "quantity": {qty},
  "type": "LIMIT",
  "price": {price},
  "stop_loss": {stop_p},
  "take_profit": {target_p},
  "product": "MIS"
}}
""".format(sym=nse_sym, qty=qty, price=price, stop_p=stop_p, target_p=target_p))
    print("=" * 76)


def show_portfolio_status():
    p = load_portfolio()
    positions = p.get("positions", [])
    print("=" * 76)
    print(f" PAPER TRADING PORTFOLIO | Cash: {format_inr(p['cash_balance_inr'])} | Realized P&L: {format_inr(p['realized_pnl_inr'])}")
    print("=" * 76)

    if not positions:
        print("  No active open positions.")
    else:
        print(f" {'ORDER ID':<18} {'SYMBOL':<14} {'QTY':<8} {'FILL':<12} {'LTP':<12} {'UNREALIZED P&L':<16}")
        print("-" * 76)
        for pos in positions:
            sym = pos["symbol"]
            qty = pos["quantity"]
            fill_p = pos["fill_price"]
            try:
                ltp = get_latest_price(sym)
            except Exception:
                ltp = fill_p
            pnl = (ltp - fill_p) * qty
            pnl_color = "\033[92m" if pnl >= 0 else "\033[91m"
            reset = "\033[0m"
            pnl_str = f"{pnl_color}{format_inr(pnl)}{reset}"
            print(f" {pos['order_id']:<18} {sym:<14} {qty:<8} {format_inr(fill_p):<12} {format_inr(ltp):<12} {pnl_str:<16}")
    print("=" * 76)


def square_off_positions(confirm: str):
    if confirm.lower() != "yes":
        print("Square off cancelled: supply --confirm 'yes' to confirm.", file=sys.stderr)
        sys.exit(1)

    p = load_portfolio()
    positions = p.get("positions", [])
    if not positions:
        print("No open positions to square off.")
        return

    print("Square off initiated for all open intraday positions...")
    total_realized_this_run = 0.0
    for pos in positions:
        sym = pos["symbol"]
        qty = pos["quantity"]
        fill_p = pos["fill_price"]
        try:
            exit_p = get_latest_price(sym)
        except Exception:
            exit_p = fill_p
        trade_pnl = (exit_p - fill_p) * qty
        total_realized_this_run += trade_pnl
        p["cash_balance_inr"] += pos["margin_used_inr"] + trade_pnl
        p["closed_trades"].append({
            "order_id": pos["order_id"],
            "symbol": sym,
            "quantity": qty,
            "entry_price": fill_p,
            "exit_price": exit_p,
            "pnl_inr": trade_pnl,
            "exit_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        })
        print(f"  Closed {qty} {sym} @ {format_inr(exit_p)} (P&L: {format_inr(trade_pnl)})")

    p["realized_pnl_inr"] += total_realized_this_run
    p["positions"] = []
    save_portfolio(p)
    print(f"[*] All positions flattened. Total Realized P&L today: {format_inr(p['realized_pnl_inr'])}")


def main():
    parser = argparse.ArgumentParser(description="Order Executor & Broker Connector for Indian Equities")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("show", help="Display trade tickets and risk readiness")

    exec_p = subparsers.add_parser("execute", help="Execute approved paper order")
    exec_p.add_argument("--confirm", default="no", help="Explicit user confirmation ('yes')")

    export_p = subparsers.add_parser("export", help="Generate broker API code/payload")
    export_p.add_argument("--broker", default="zerodha", choices=["zerodha", "angelone", "dhan", "generic"])

    subparsers.add_parser("status", help="View active positions and P&L")

    sq_p = subparsers.add_parser("squareoff", help="Square off all open intraday positions")
    sq_p.add_argument("--confirm", default="no", help="Explicit user confirmation ('yes')")

    args = parser.parse_args()

    if args.command == "show" or args.command is None:
        show_tickets()
    elif args.command == "execute":
        execute_paper_order(args.confirm)
    elif args.command == "export":
        generate_broker_payload(args.broker)
    elif args.command == "status":
        show_portfolio_status()
    elif args.command == "squareoff":
        square_off_positions(args.confirm)


if __name__ == "__main__":
    main()
