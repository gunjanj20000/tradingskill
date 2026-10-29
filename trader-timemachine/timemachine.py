#!/usr/bin/env python3
"""Time Machine Simulator for trader-timemachine (Indian Equities NSE/BSE).

Replays a planned day trade across 10,000 simulated sessions using historical 5m bars
from the stock's actual recent trading sessions on the National Stock Exchange (NSE).
Tells you the honest mathematical odds before you risk a single rupee (₹).

Usage:
    python3 timemachine.py run                              # from trader/plan.json, 10,000 replays
    python3 timemachine.py run --replays 5000 --seed 42 --write
    python3 timemachine.py run --symbol SBIN.NS --entry 971.90 --stop 968.06 --target 979.58
    python3 timemachine.py chart                            # ASCII fan chart of paths
"""

import argparse
import datetime
import json
import math
import os
import random
import sys

# Ensure project root is in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import numpy as np
import pandas as pd
from trader_core.data_feed import fetch_bars
from trader_core.formatting import format_inr
from trader_core.universe import clean_symbol

DEFAULT_PLAN_PATH = os.path.join(ROOT_DIR, "trader", "plan.json")
DEFAULT_OUTPUT_PATH = os.path.join(ROOT_DIR, "trader", "timemachine.json")


def run_simulation(
    symbol: str,
    entry: float,
    stop: float,
    target: float,
    replays: int = 10000,
    seed: int = 19,
    write: bool = False,
) -> dict:
    """Run 10,000 Monte Carlo replays using empirical historical 5-minute bar returns."""
    symbol = clean_symbol(symbol)
    random.seed(seed)
    np.random.seed(seed)

    risk = entry - stop
    reward = target - entry
    target_r = reward / risk if risk > 0 else 1.0

    # Fetch 60 days of 5m bars for Indian market
    df = fetch_bars(symbol, period="1mo", interval="5m", max_age_seconds=600)
    if df.empty or len(df) < 50:
        raise ValueError(f"Insufficient historical 5m bars to build simulation pool for {symbol}")

    # Calculate bar percentage returns: (High/Open, Low/Open, Close/Open)
    opens = df["Open"].values
    highs = df["High"].values
    lows = df["Low"].values
    closes = df["Close"].values

    valid_mask = opens > 0
    h_ratios = highs[valid_mask] / opens[valid_mask]
    l_ratios = lows[valid_mask] / opens[valid_mask]
    c_ratios = closes[valid_mask] / opens[valid_mask]

    pool_size = len(h_ratios)
    if pool_size < 30:
        raise ValueError(f"Pool size too small ({pool_size}) for realistic simulation")

    # Day trade walking from entry to EOD (typical remaining 5m bars: ~30 to 50 bars)
    session_bars = 45  # ~3.75 hours of trading
    
    target_hits = 0
    stop_hits = 0
    open_eod = 0
    end_prices = []
    r_multiples = []

    # Select paths for fan chart (50 paths)
    fan_paths = []

    for sim_idx in range(replays):
        curr_price = entry
        hit = None
        path = [curr_price]

        # Draw random indices from empirical bar return pool
        rand_indices = np.random.randint(0, pool_size, size=session_bars)

        for bar_idx in range(session_bars):
            idx = rand_indices[bar_idx]
            bar_open = curr_price
            bar_high = bar_open * h_ratios[idx]
            bar_low = bar_open * l_ratios[idx]
            bar_close = bar_open * c_ratios[idx]

            # Conservative rule: check stop first if bar touched both
            if bar_low <= stop:
                hit = "stop"
                curr_price = stop
                path.append(curr_price)
                break
            elif bar_high >= target:
                hit = "target"
                curr_price = target
                path.append(curr_price)
                break
            else:
                curr_price = bar_close
                path.append(curr_price)

        if hit == "target":
            target_hits += 1
            r_multiples.append(target_r)
        elif hit == "stop":
            stop_hits += 1
            r_multiples.append(-1.0)
        else:
            open_eod += 1
            final_r = (curr_price - entry) / risk if risk > 0 else 0.0
            r_multiples.append(final_r)

        end_prices.append(curr_price)
        if sim_idx < 40:
            fan_paths.append(path)

    # Statistical summaries
    pct_target = (target_hits / replays) * 100.0
    pct_stop = (stop_hits / replays) * 100.0
    pct_open = (open_eod / replays) * 100.0
    mean_r = float(np.mean(r_multiples))
    median_end_price = float(np.median(end_prices))
    p5_end_price = float(np.percentile(end_prices, 5))
    p95_end_price = float(np.percentile(end_prices, 95))

    # Breakeven share required at this R
    # At 1R, need 50% target / (target + stop). At 2R, need 33.3%
    decided_runs = target_hits + stop_hits
    target_share = (target_hits / decided_runs * 100.0) if decided_runs > 0 else 50.0
    breakeven_share = (1.0 / (1.0 + target_r)) * 100.0
    edge = target_share - breakeven_share

    if edge >= 12.0:
        verdict = "STRONGLY TOWARD TARGET (High edge setup)"
    elif edge >= 4.0:
        verdict = "LEANS TOWARD TARGET (Positive mathematical expectation)"
    elif edge <= -12.0:
        verdict = "STRONGLY TOWARD STOP (Unfavorable odds - caution advised)"
    elif edge <= -4.0:
        verdict = "LEANS TOWARD STOP (Sub-optimal risk profile)"
    else:
        verdict = "CLOSE TO COIN FLIP (Even odds / balanced distribution)"

    result = {
        "symbol": symbol,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "risk": round(risk, 2),
        "target_r": round(target_r, 2),
        "replays": replays,
        "seed": seed,
        "verdict": verdict,
        "edge_pct": round(edge, 1),
        "outcomes": {
            "target_first_pct": round(pct_target, 1),
            "stop_first_pct": round(pct_stop, 1),
            "open_at_close_pct": round(pct_open, 1),
            "expected_r": round(mean_r, 2),
        },
        "price_distribution": {
            "p5": round(p5_end_price, 2),
            "median": round(median_end_price, 2),
            "p95": round(p95_end_price, 2),
        },
        "fan_paths": fan_paths[:10],
    }

    if write:
        os.makedirs(os.path.dirname(DEFAULT_OUTPUT_PATH), exist_ok=True)
        with open(DEFAULT_OUTPUT_PATH, "w") as f:
            json.dump(result, f, indent=2)
        print(f"[*] Time Machine simulation saved to {DEFAULT_OUTPUT_PATH}")

    return result


def print_ascii_fan_chart(result: dict):
    """Render an ASCII visual representation of the Monte Carlo paths."""
    print("\n TIME MACHINE FAN CHART & DISTRIBUTION:")
    print("=" * 72)
    entry = result["entry"]
    stop = result["stop"]
    target = result["target"]
    p5 = result["price_distribution"]["p5"]
    p95 = result["price_distribution"]["p95"]
    med = result["price_distribution"]["median"]

    min_p = min(stop * 0.99, p5)
    max_p = max(target * 1.01, p95)
    rng = max_p - min_p if max_p > min_p else 1.0

    def to_col(p):
        col = int(((p - min_p) / rng) * 45)
        return max(0, min(45, col))

    # Print levels
    print(f" Target  ({format_inr(target):<10}): " + " " * to_col(target) + "[TARGET +2R]")
    print(f" 95th Pct({format_inr(p95):<10}): " + " " * to_col(p95) + "|--- High Band")
    print(f" Entry   ({format_inr(entry):<10}): " + " " * to_col(entry) + "*--- ENTRY POINT")
    print(f" Median  ({format_inr(med):<10}): " + " " * to_col(med) + "M--- MEDIAN EXIT")
    print(f" Stop    ({format_inr(stop):<10}): " + " " * to_col(stop) + "[STOP -1R]")
    print(f" 5th Pct ({format_inr(p5):<10}): " + " " * to_col(p5) + "|--- Low Band")
    print("-" * 72)


def main():
    parser = argparse.ArgumentParser(description="Time Machine Simulator for Indian Equities")
    subparsers = parser.add_subparsers(dest="command")

    run_p = subparsers.add_parser("run", help="Run Monte Carlo simulation")
    run_p.add_argument("--symbol", help="Stock ticker (e.g. SBIN.NS)")
    run_p.add_argument("--entry", type=float, help="Entry price in INR")
    run_p.add_argument("--stop", type=float, help="Stop price in INR")
    run_p.add_argument("--target", type=float, help="Target price in INR")
    run_p.add_argument("--replays", type=int, default=10000, help="Number of simulated sessions (default: 10000)")
    run_p.add_argument("--seed", type=int, default=19, help="Random seed (default: 19)")
    run_p.add_argument("--write", action="store_true", help="Save output to trader/timemachine.json")
    run_p.add_argument("--json", action="store_true", help="Output JSON")

    chart_p = subparsers.add_parser("chart", help="Display ASCII fan chart from saved run")

    args = parser.parse_args()

    if args.command == "run" or args.command is None:
        sym = getattr(args, "symbol", None)
        entry = getattr(args, "entry", None)
        stop = getattr(args, "stop", None)
        target = getattr(args, "target", None)

        if sym is None or entry is None or stop is None or target is None:
            if not os.path.exists(DEFAULT_PLAN_PATH):
                print(f"No trade plan found at {DEFAULT_PLAN_PATH}. Run 'python3 exit.py plan --write' first.", file=sys.stderr)
                sys.exit(1)
            with open(DEFAULT_PLAN_PATH, "r") as f:
                plan = json.load(f)
            sym = plan["symbol"]
            entry = plan["entry_price"]
            stop = plan["stop_price"]
            target = plan["target_price"]

        res = run_simulation(
            symbol=sym,
            entry=entry,
            stop=stop,
            target=target,
            replays=getattr(args, "replays", 10000),
            seed=getattr(args, "seed", 19),
            write=getattr(args, "write", False),
        )

        if getattr(args, "json", False):
            print(json.dumps(res, indent=2))
        else:
            print("=" * 72)
            print(f" TIME MACHINE 10,000 RUN REPLAY: {res['symbol']} | ENTRY {format_inr(res['entry'])}")
            print("=" * 72)
            print(f" Verdict:        \033[92m{res['verdict']}\033[0m")
            print(f" Edge vs BE:     {res['edge_pct']:+.1f}% points")
            print(f" Expected Value: {res['outcomes']['expected_r']:+.2f}R per trade")
            print("-" * 72)
            print(f" Target First:   {res['outcomes']['target_first_pct']}% of sessions")
            print(f" Stop First:     {res['outcomes']['stop_first_pct']}% of sessions")
            print(f" Open at Close:  {res['outcomes']['open_at_close_pct']}% of sessions")
            print("-" * 72)
            print(f" 5th - 95th Pct: {format_inr(res['price_distribution']['p5'])} to {format_inr(res['price_distribution']['p95'])}")
            print(f" Median Price:   {format_inr(res['price_distribution']['median'])}")
            print("=" * 72)
            print_ascii_fan_chart(res)
        sys.exit(0)

    elif args.command == "chart":
        if not os.path.exists(DEFAULT_OUTPUT_PATH):
            print("No timemachine.json found. Run 'timemachine.py run --write' first.", file=sys.stderr)
            sys.exit(1)
        with open(DEFAULT_OUTPUT_PATH, "r") as f:
            res = json.load(f)
        print_ascii_fan_chart(res)
        sys.exit(0)


if __name__ == "__main__":
    main()
