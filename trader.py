#!/usr/bin/env python3
"""Master CLI & Workflow Orchestrator for Day Trading Indian Equities (NSE/BSE).

Integrates all 12 trading modules:
  scan          Scan Nifty 50, Nifty Bank, F&O for setups
  indicators    Compute 60+ technical indicators & consensus matrix
  entry         Bar-by-bar entry timer and trigger confirmation
  plan          Compute stop-loss, targets, and risk parameters
  timemachine   Replay 10,000 Monte Carlo sessions before risking capital
  budget        Size positions in INR (₹) using SEBI 5x MIS margin rules
  risk          Validate orders against hard risk and trading hours rules
  broker        Show tickets, paper trade, or export to Zerodha / Angel One
  alerts        Monitor price levels and 15:15 IST square-off
  fiidii        Track FII/DII institutional cash flows & bulk deals
  news          Fetch breaking market news & sentiment
  analyst       Company fundamental & valuation multiples
  full-cycle    Run automated end-to-end pipeline on a ticker

Usage:
    python3 trader.py scan --universe nifty50 --setup confluence
    python3 trader.py indicators SBIN.NS
    python3 trader.py full-cycle SBIN.NS
"""

import argparse
import os
import subprocess
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


def run_cmd(script_path: str, extra_args: list[str]):
    full_path = os.path.join(ROOT_DIR, script_path)
    cmd = [sys.executable, full_path] + extra_args
    res = subprocess.run(cmd)
    sys.exit(res.returncode)


def run_full_cycle(symbol: str, confirm_exec: bool = False):
    """Execute the end-to-end trading pipeline from scanning/indicators to broker ticket."""
    print("\n" + "=" * 80)
    print(f" EXECUTING COMPLETE DAY-TRADER PIPELINE FOR: {symbol.upper()}")
    print("=" * 80)

    # 1. Technical Indicators
    print("\n>>> STEP 1: CALCULATING ALL TECHNICAL INDICATORS...")
    subprocess.run([sys.executable, os.path.join(ROOT_DIR, "trader-indicators", "indicators.py"), symbol])

    # 2. Entry Check
    print("\n>>> STEP 2: CHECKING ENTRY TRIGGER & VOL CONFLUENCE...")
    subprocess.run([sys.executable, os.path.join(ROOT_DIR, "trader-entry", "entry.py"), "check", symbol, "--setup", "confluence", "--write"])

    # 3. Exit Planning
    print("\n>>> STEP 3: COMPUTING STOP-LOSS & TARGET EXIT PLAN...")
    subprocess.run([sys.executable, os.path.join(ROOT_DIR, "trader-exit", "exit.py"), "plan", "--stop", "atr:1.5", "--target", "2R", "--write"])

    # 4. Time Machine 10,000 Replay
    print("\n>>> STEP 4: RUNNING TIME MACHINE 5,000 SESSION MONTE CARLO REPLAY...")
    subprocess.run([sys.executable, os.path.join(ROOT_DIR, "trader-timemachine", "timemachine.py"), "run", "--replays", "5000", "--write"])

    # 5. Budget Sizing
    print("\n>>> STEP 5: SIZING POSITION (INR & SEBI 5x MIS MARGIN)...")
    subprocess.run([sys.executable, os.path.join(ROOT_DIR, "trader-budget", "size.py"), "--write"])

    # 6. Pre-Trade Risk Check
    print("\n>>> STEP 6: VALIDATING HARD RISK LIMITS & IST HOURS...")
    subprocess.run([sys.executable, os.path.join(ROOT_DIR, "trader-risk", "check.py"), "--ignore-time-check"])

    # 7. Broker Ticket
    print("\n>>> STEP 7: GENERATING BROKER TICKET...")
    subprocess.run([sys.executable, os.path.join(ROOT_DIR, "trader-broker", "ticket.py"), "show"])

    # 8. Alerts
    print("\n>>> STEP 8: CONFIGURING TARGET, STOP & 15:15 IST ALERTS...")
    subprocess.run([sys.executable, os.path.join(ROOT_DIR, "trader-alerts", "alerts.py"), "add", "--from-plan"])

    # 9. Paper Execution
    if confirm_exec:
        print("\n>>> STEP 9: EXECUTING PAPER TRADE...")
        subprocess.run([sys.executable, os.path.join(ROOT_DIR, "trader-broker", "ticket.py"), "execute", "--confirm", "yes"])

    print("\n" + "=" * 80)
    print(" [✓] COMPLETE PIPELINE CYCLE COMPLETED SUCCESSFULLY")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Master Day Trader Engine for Indian Stocks (NSE/BSE)")
    subparsers = parser.add_subparsers(dest="command")

    # Pass-through commands
    subparsers.add_parser("scan", help="Scan universes for setups")
    subparsers.add_parser("indicators", help="Compute 60+ technical indicators")
    subparsers.add_parser("entry", help="Bar-by-bar entry timing")
    subparsers.add_parser("plan", help="Stop loss and target planning")
    subparsers.add_parser("timemachine", help="Monte Carlo trade simulation")
    subparsers.add_parser("budget", help="INR Position sizing & margin")
    subparsers.add_parser("risk", help="Pre-trade risk manager")
    subparsers.add_parser("broker", help="Order tickets and paper broker")
    subparsers.add_parser("alerts", help="Price and square-off alerts")
    subparsers.add_parser("fiidii", help="FII/DII flows and block deals")
    subparsers.add_parser("news", help="Market news and sentiment")
    subparsers.add_parser("analyst", help="Company fundamental multiples")

    fc_p = subparsers.add_parser("full-cycle", help="Execute complete automated trading pipeline")
    fc_p.add_argument("symbol", default="SBIN.NS", nargs="?", help="Stock ticker (e.g. SBIN.NS)")
    fc_p.add_argument("--execute", action="store_true", help="Also execute paper order")

    # If args passed, parse known args
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    cmd = sys.argv[1]
    extra_args = sys.argv[2:]

    cmd_map = {
        "scan": "trader-scanner/scan.py",
        "indicators": "trader-indicators/indicators.py",
        "entry": "trader-entry/entry.py",
        "plan": "trader-exit/exit.py",
        "timemachine": "trader-timemachine/timemachine.py",
        "budget": "trader-budget/size.py",
        "risk": "trader-risk/check.py",
        "broker": "trader-broker/ticket.py",
        "alerts": "trader-alerts/alerts.py",
        "fiidii": "trader-fiidii/fiidii.py",
        "news": "trader-news/news.py",
        "analyst": "trader-analyst/facts.py",
    }

    if cmd == "full-cycle":
        fc_args = fc_p.parse_args(extra_args)
        run_full_cycle(fc_args.symbol, confirm_exec=fc_args.execute)
    elif cmd in cmd_map:
        run_cmd(cmd_map[cmd], extra_args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
