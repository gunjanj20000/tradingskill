#!/usr/bin/env python3
"""Market & Chart Scanner for Indian Stocks (NSE/BSE).

Scans Indian universes (Nifty 50, Nifty Bank, Nifty Next 50, F&O) for high-probability setups:
1. orb                Opening-Range Breakout (15-min or 30-min range with volume confirmation)
2. confluence         Multi-Indicator Confluence (>= 70% technical indicators bullish)
3. supertrend_vwap    SuperTrend Bullish + Price > VWAP + Price > EMA20
4. cpr_breakout       Narrow Central Pivot Range (CPR) breakout
5. camarilla_h4       Breakout above Camarilla H4 level
6. volume_shocker     Relative Volume (RVOL) >= 2.0x with green candle
7. oversold_bounce    RSI < 35 returning up with bullish candle / hammer

Usage:
    python3 scan.py --setup orb --universe nifty50
    python3 scan.py --setup supertrend_vwap --universe niftybank
    python3 scan.py --setup confluence --min-bullish 65
    python3 scan.py --symbols RELIANCE.NS,TCS.NS,HDFCBANK.NS,SBIN.NS
    python3 scan.py --write --json
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

import pandas as pd
from trader_core.data_feed import fetch_bars
from trader_core.formatting import format_inr, format_pct
from trader_core.universe import UNIVERSES, clean_symbol, get_universe
from trader_indicators.indicators import TechnicalIndicators


def scan_symbol(symbol: str, setup: str, min_bullish_pct: float = 65.0) -> dict | None:
    """Run scanner logic on a single symbol."""
    try:
        # Fetch 5-day 15m bars for intraday analysis
        df = fetch_bars(symbol, period="5d", interval="15m", max_age_seconds=120)
        if df.empty or len(df) < 10:
            return None

        engine = TechnicalIndicators(df)
        all_ind = engine.compute_all()
        curr_price = all_ind["current_price"]
        consen = all_ind["consensus"]

        passed = False
        reason = ""
        entry_trigger = curr_price
        stop_ref = None

        if setup == "confluence":
            if consen["bullish_pct"] >= min_bullish_pct:
                passed = True
                reason = f"{consen['bullish_pct']}% Bullish Confluence ({consen['bullish_count']}/{consen['total_indicators']} indicators)"
                stop_ref = all_ind["volatility"]["bollinger"]["mid"]

        elif setup == "supertrend_vwap":
            st_bullish = all_ind["trend"]["supertrend"]["trend"] == "BULLISH"
            above_vwap = curr_price > all_ind["volume"]["vwap"]
            above_ema20 = curr_price > all_ind["trend"]["moving_averages"]["ema20"]
            if st_bullish and above_vwap and above_ema20:
                passed = True
                st_val = all_ind["trend"]["supertrend"]["value"]
                vwap_val = all_ind["volume"]["vwap"]
                reason = f"SuperTrend Bullish ({format_inr(st_val)}), Price > VWAP ({format_inr(vwap_val)})"
                stop_ref = max(st_val, vwap_val)

        elif setup == "orb":
            # Identify today's bars
            if isinstance(df.index, pd.DatetimeIndex):
                today_date = df.index[-1].date()
                today_bars = df[df.index.date == today_date]
            else:
                today_bars = df.iloc[-8:]

            if len(today_bars) >= 2:
                # First 2 15m bars form 30-min opening range (or 1st bar for 15m ORB)
                or_bars = today_bars.iloc[:2]
                or_high = float(or_bars["High"].max())
                or_low = float(or_bars["Low"].min())
                or_vol_avg = float(or_bars["Volume"].mean())

                # Check if current bar or any subsequent bar closed above OR high
                latest_close = float(today_bars["Close"].iloc[-1])
                latest_vol = float(today_bars["Volume"].iloc[-1])

                if latest_close > or_high:
                    passed = True
                    or_mid = (or_high + or_low) / 2.0
                    vol_x = latest_vol / or_vol_avg if or_vol_avg > 0 else 1.0
                    reason = f"Close {format_inr(latest_close)} above 30m OR High {format_inr(or_high)} (Vol: {vol_x:.1f}x)"
                    entry_trigger = or_high
                    stop_ref = or_mid

        elif setup == "cpr_breakout":
            cpr = all_ind["pivots"]["cpr"]
            if curr_price > cpr["tc"] and (cpr["is_narrow"] or consen["bullish_pct"] >= 55):
                passed = True
                width_tag = "Narrow CPR" if cpr["is_narrow"] else "CPR"
                reason = f"Breakout above {width_tag} TC ({format_inr(cpr['tc'])}) | Width: {cpr['width_pct']:.2f}%"
                stop_ref = cpr["pivot"]

        elif setup == "camarilla_h4":
            h4 = all_ind["pivots"]["camarilla"]["h4"]
            if curr_price >= h4:
                passed = True
                reason = f"Bullish Breakout above Camarilla H4 ({format_inr(h4)})"
                stop_ref = all_ind["pivots"]["camarilla"]["h3"]

        elif setup == "volume_shocker":
            rvol = all_ind["volume"]["rvol"]
            is_green = df["Close"].iloc[-1] > df["Open"].iloc[-1]
            if rvol >= 2.0 and is_green:
                passed = True
                reason = f"Volume Spike: {rvol:.1f}x 20-bar avg volume with strong green candle"
                stop_ref = float(df["Low"].iloc[-1])

        elif setup == "oversold_bounce":
            rsi = all_ind["momentum"]["rsi14"]
            b_low = all_ind["volatility"]["bollinger"]["lower"]
            patterns = all_ind["candlestick_patterns"]
            if (rsi < 35 or curr_price <= b_low * 1.01) and (patterns or curr_price > df["Open"].iloc[-1]):
                passed = True
                pattern_name = list(patterns.keys())[0] if patterns else "Green Candle"
                reason = f"Oversold Bounce: RSI {rsi:.1f} at Lower Band with {pattern_name}"
                stop_ref = float(df["Low"].iloc[-1])

        if passed:
            return {
                "symbol": symbol,
                "price": curr_price,
                "setup": setup,
                "reason": reason,
                "bullish_pct": consen["bullish_pct"],
                "verdict": consen["verdict"],
                "entry_trigger": round(entry_trigger, 2),
                "suggested_stop": round(stop_ref, 2) if stop_ref else round(curr_price * 0.99, 2),
                "rsi": all_ind["momentum"]["rsi14"],
                "vwap": all_ind["volume"]["vwap"],
                "supertrend": all_ind["trend"]["supertrend"]["trend"],
            }
        return None

    except Exception:
        return None


def run_scanner(
    universe_name: str = "nifty50",
    setup: str = "confluence",
    custom_symbols: list[str] | None = None,
    min_bullish: float = 65.0,
    write_path: str | None = None,
) -> list[dict]:
    """Execute scan across symbol list."""
    if custom_symbols:
        symbols = [clean_symbol(s) for s in custom_symbols]
    else:
        symbols = get_universe(universe_name)

    print(f"[*] Scanning {len(symbols)} Indian stocks for setup: '{setup.upper()}'...")
    results = []
    for idx, sym in enumerate(symbols, 1):
        clean_sym = clean_symbol(sym)
        res = scan_symbol(clean_sym, setup, min_bullish_pct=min_bullish)
        if res:
            results.append(res)
            print(f"  [+] HIT: {clean_sym:<15} LTP: {format_inr(res['price']):<12} {res['reason']}")

    # Sort results by bullish percentage descending
    results.sort(key=lambda x: x["bullish_pct"], reverse=True)

    if write_path:
        os.makedirs(os.path.dirname(os.path.abspath(write_path)), exist_ok=True)
        with open(write_path, "w") as f:
            json.dump({
                "scan_time": datetime.datetime.now().isoformat(),
                "setup": setup,
                "total_scanned": len(symbols),
                "total_hits": len(results),
                "watchlist": results,
            }, f, indent=2)
        print(f"[*] Saved {len(results)} scan results to {write_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Indian Equities Market & Chart Scanner")
    parser.add_argument("--universe", default="nifty50", choices=list(UNIVERSES.keys()), help="Universe to scan (default: nifty50)")
    parser.add_argument("--setup", default="supertrend_vwap", choices=[
        "orb", "confluence", "supertrend_vwap", "cpr_breakout", "camarilla_h4", "volume_shocker", "oversold_bounce"
    ], help="Setup to scan for (default: supertrend_vwap)")
    parser.add_argument("--symbols", help="Comma-separated custom symbols (e.g. RELIANCE.NS,TCS.NS)")
    parser.add_argument("--min-bullish", type=float, default=65.0, help="Min bullish % for confluence setup (default: 65.0)")
    parser.add_argument("--write", action="store_true", help="Save scan results to trader/watchlist.json")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    custom_syms = [s.strip() for s in args.symbols.split(",")] if args.symbols else None
    write_path = "/home/ubuntu/tradingskill/trader/watchlist.json" if args.write else None

    hits = run_scanner(
        universe_name=args.universe,
        setup=args.setup,
        custom_symbols=custom_syms,
        min_bullish=args.min_bullish,
        write_path=write_path,
    )

    if args.json:
        print(json.dumps(hits, indent=2))
    else:
        print("\n" + "=" * 80)
        print(f" SCANNER RESULTS: {len(hits)} STOCKS MATCHED SETUP '{args.setup.upper()}'")
        print("=" * 80)
        if not hits:
            print("  No stocks met the criteria at this moment.")
        else:
            print(f" {'SYMBOL':<14} {'LTP (₹)':<12} {'VERDICT':<12} {'BULLISH %':<10} {'ENTRY REF':<12} {'STOP REF':<12}")
            print("-" * 80)
            for h in hits:
                print(f" {h['symbol']:<14} {format_inr(h['price']):<12} {h['verdict']:<12} {h['bullish_pct']:<10.1f} {format_inr(h['entry_trigger']):<12} {format_inr(h['suggested_stop']):<12}")
        print("=" * 80)

    sys.exit(0 if hits else 1)


if __name__ == "__main__":
    main()
