#!/usr/bin/env python3
"""Entry Timer for trader-entry (Indian Equities NSE/BSE).

Watches a setup bar-by-bar and confirms the exact moment to enter.
Validates candle close (avoids wick fakeouts), volume threshold, and technical indicator confirmation.
Enforces Indian market hours (09:15 to 15:30 IST; entry cutoff default: 14:45 IST).

Usage:
    python3 entry.py check SBIN.NS                          # Checks latest setup status
    python3 entry.py check INFY.NS --setup orb --write      # Writes trader/entry.json on trigger
    python3 entry.py check RELIANCE.NS --setup level --level 1175.00
    python3 entry.py watch SBIN.NS --every 15               # Live polling bar-by-bar until triggered
    python3 entry.py watchlist                             # Checks all symbols in trader/watchlist.json
"""

import argparse
import datetime
import json
import os
import sys
import time

# Ensure project root is in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import pandas as pd
from trader_core.data_feed import fetch_bars
from trader_core.formatting import format_inr
from trader_core.market_hours import IST, is_entry_allowed, is_market_open, now_ist
from trader_core.universe import clean_symbol
from trader_indicators.indicators import TechnicalIndicators

DEFAULT_CONFIG_PATH = os.path.join(ROOT_DIR, "trader", "config.json")
DEFAULT_ENTRY_PATH = os.path.join(ROOT_DIR, "trader", "entry.json")
DEFAULT_WATCHLIST_PATH = os.path.join(ROOT_DIR, "trader", "watchlist.json")


def load_config() -> dict:
    """Load configuration with default fallback."""
    defaults = {
        "no_entries_before": "09:20",
        "no_entries_after": "14:45",
        "flat_by": "15:15",
        "min_volume_multiplier": 1.1,
    }
    if os.path.exists(DEFAULT_CONFIG_PATH):
        try:
            with open(DEFAULT_CONFIG_PATH, "r") as f:
                user_cfg = json.load(f)
                defaults.update(user_cfg)
        except Exception:
            pass
    return defaults


def check_entry(
    symbol: str,
    setup: str = "confluence",
    target_level: float | None = None,
    interval: str = "5m",
    min_volume_x: float = 1.0,
    write: bool = False,
) -> dict:
    """Check if entry condition has triggered for a symbol."""
    symbol = clean_symbol(symbol)
    cfg = load_config()

    allowed, msg = is_entry_allowed(
        no_entries_before=cfg.get("no_entries_before", "09:20"),
        no_entries_after=cfg.get("no_entries_after", "14:45"),
    )

    try:
        df = fetch_bars(symbol, period="5d", interval=interval, max_age_seconds=30)
    except Exception as e:
        return {
            "symbol": symbol,
            "status": "no-data",
            "reason": f"Unable to fetch price bars: {e}",
            "triggered": False,
        }

    if df.empty or len(df) < 5:
        return {
            "symbol": symbol,
            "status": "no-data",
            "reason": "Insufficient bars available",
            "triggered": False,
        }

    latest_bar = df.iloc[-1]
    latest_close = float(latest_bar["Close"])
    latest_high = float(latest_bar["High"])
    latest_low = float(latest_bar["Low"])
    latest_open = float(latest_bar["Open"])
    latest_vol = float(latest_bar["Volume"])
    bar_time = df.index[-1].strftime("%Y-%m-%d %H:%M:%S IST")

    engine = TechnicalIndicators(df)
    all_ind = engine.compute_all()
    vwap_val = all_ind["volume"]["vwap"]
    supertrend_bullish = all_ind["trend"]["supertrend"]["trend"] == "BULLISH"
    st_val = all_ind["trend"]["supertrend"]["value"]
    bullish_pct = all_ind["consensus"]["bullish_pct"]

    triggered = False
    status = "waiting"
    reason = ""
    trigger_price = latest_close
    stop_ref = None

    if setup == "level":
        if target_level is None:
            raise ValueError("Must specify --level for level setup")
        if latest_close >= target_level:
            triggered = True
            status = "triggered"
            reason = f"Completed candle closed at {format_inr(latest_close)} above level {format_inr(target_level)}"
            trigger_price = latest_close
            stop_ref = target_level * 0.99
        else:
            status = "waiting"
            reason = f"Current close {format_inr(latest_close)} below trigger level {format_inr(target_level)}"

    elif setup == "orb":
        # First 3 5m bars = 15m opening range (09:15 - 09:30)
        today_date = df.index[-1].date()
        today_bars = df[df.index.date == today_date]
        if len(today_bars) < 3:
            status = "waiting"
            reason = f"Opening range still forming ({len(today_bars)}/3 bars completed)"
        else:
            or_bars = today_bars.iloc[:3]
            or_high = float(or_bars["High"].max())
            or_low = float(or_bars["Low"].min())
            or_mid = (or_high + or_low) / 2.0
            avg_vol = float(or_bars["Volume"].mean())
            vol_mult = latest_vol / avg_vol if avg_vol > 0 else 1.0

            if latest_close > or_high:
                if vol_mult >= min_volume_x:
                    triggered = True
                    status = "triggered"
                    reason = f"ORB Long: Close {format_inr(latest_close)} > OR High {format_inr(or_high)} (Vol: {vol_mult:.2f}x)"
                    trigger_price = latest_close
                    stop_ref = or_mid
                else:
                    status = "waiting"
                    reason = f"Price {format_inr(latest_close)} > OR High but volume {vol_mult:.2f}x < required {min_volume_x}x"
            else:
                status = "waiting"
                reason = f"Waiting for close above OR High {format_inr(or_high)} (current {format_inr(latest_close)})"

    elif setup == "confluence":
        if bullish_pct >= 65 and latest_close > vwap_val and supertrend_bullish:
            triggered = True
            status = "triggered"
            reason = f"High Confluence ({bullish_pct}% Bullish) + Price > VWAP ({format_inr(vwap_val)}) + SuperTrend Bullish"
            trigger_price = latest_close
            stop_ref = max(vwap_val, st_val)
        else:
            status = "waiting"
            reason = f"Confluence score {bullish_pct}% (Need >= 65% + Price > VWAP + SuperTrend Bullish)"

    # Market timing validation
    if not allowed and status == "waiting":
        status = "expired"
        reason = f"Entry window expired ({msg})"

    result = {
        "symbol": symbol,
        "setup": setup,
        "status": status,
        "triggered": triggered,
        "trigger_price": round(trigger_price, 2),
        "suggested_stop": round(stop_ref, 2) if stop_ref else round(trigger_price * 0.99, 2),
        "bar_time": bar_time,
        "interval": interval,
        "latest_close": round(latest_close, 2),
        "vwap": round(vwap_val, 2),
        "supertrend": "BULLISH" if supertrend_bullish else "BEARISH",
        "bullish_pct": bullish_pct,
        "reason": reason,
    }

    if write and triggered:
        os.makedirs(os.path.dirname(DEFAULT_ENTRY_PATH), exist_ok=True)
        with open(DEFAULT_ENTRY_PATH, "w") as f:
            json.dump(result, f, indent=2)
        print(f"[*] Trigger confirmed! Saved entry record to {DEFAULT_ENTRY_PATH}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Entry Timer for Indian Stocks (NSE/BSE)")
    subparsers = parser.add_subparsers(dest="command")

    # Command: check
    check_p = subparsers.add_parser("check", help="Check entry trigger condition")
    check_p.add_argument("symbol", help="NSE stock ticker (e.g. SBIN.NS, RELIANCE)")
    check_p.add_argument("--setup", default="confluence", choices=["confluence", "orb", "level"])
    check_p.add_argument("--level", type=float, help="Target price level for level setup")
    check_p.add_argument("--interval", default="5m", help="Candle interval (default: 5m)")
    check_p.add_argument("--min-volume-x", type=float, default=1.0, help="Min volume multiplier (default: 1.0)")
    check_p.add_argument("--write", action="store_true", help="Save trader/entry.json on trigger")
    check_p.add_argument("--json", action="store_true", help="Output JSON")

    # Command: watch
    watch_p = subparsers.add_parser("watch", help="Poll bar-by-bar until entry triggers")
    watch_p.add_argument("symbol", help="Stock ticker to watch")
    watch_p.add_argument("--setup", default="confluence", choices=["confluence", "orb", "level"])
    watch_p.add_argument("--every", type=int, default=30, help="Poll interval in seconds")
    watch_p.add_argument("--until", default="15:15", help="Stop watching at this IST time")

    # Command: watchlist
    wl_p = subparsers.add_parser("watchlist", help="Check all symbols in trader/watchlist.json")
    wl_p.add_argument("--write", action="store_true", help="Save the first triggered entry")

    args = parser.parse_args()

    if args.command == "check":
        res = check_entry(
            symbol=args.symbol,
            setup=args.setup,
            target_level=args.level,
            interval=args.interval,
            min_volume_x=args.min_volume_x,
            write=args.write,
        )
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            status_tag = f"\033[92mTRIGGERED\033[0m" if res["triggered"] else f"\033[93m{res['status'].upper()}\033[0m"
            print("=" * 70)
            print(f" ENTRY MONITOR: {res['symbol']} [{res['setup'].upper()}] -> Status: {status_tag}")
            print(f" Last Bar: {res['bar_time']} | Close: {format_inr(res['latest_close'])}")
            print(f" Trigger Price: {format_inr(res['trigger_price'])} | Suggested Stop: {format_inr(res['suggested_stop'])}")
            print(f" Context: VWAP {format_inr(res['vwap'])}, SuperTrend {res['supertrend']}, Bullish: {res['bullish_pct']}%")
            print(f" Details: {res['reason']}")
            print("=" * 70)
        sys.exit(0 if res["triggered"] else 1)

    elif args.command == "watchlist":
        if not os.path.exists(DEFAULT_WATCHLIST_PATH):
            print(f"Watchlist file not found: {DEFAULT_WATCHLIST_PATH}. Run scan first.", file=sys.stderr)
            sys.exit(1)
        with open(DEFAULT_WATCHLIST_PATH, "r") as f:
            wl_data = json.load(f)
        items = wl_data.get("watchlist", [])
        print(f"[*] Checking entry conditions for {len(items)} watchlist stocks...")
        triggered_any = False
        for it in items:
            sym = it["symbol"]
            setup = it.get("setup", "confluence")
            res = check_entry(sym, setup=setup, write=args.write and not triggered_any)
            tag = "TRIGGERED" if res["triggered"] else res["status"].upper()
            print(f"  {sym:<15} [{tag:<10}] LTP: {format_inr(res['latest_close']):<12} {res['reason']}")
            if res["triggered"]:
                triggered_any = True
        sys.exit(0 if triggered_any else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
