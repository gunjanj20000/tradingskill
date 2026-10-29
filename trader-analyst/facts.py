#!/usr/bin/env python3
"""Fundamental & Quarterly Earnings Analyst for Indian Stocks (NSE/BSE).

Extracts key valuation multiples (P/E, P/B, EV/EBITDA), profitability (ROE, ROCE),
solvency (Debt/Equity), quarterly performance, and shareholding pattern for Indian companies.

Usage:
    python3 facts.py SBIN.NS
    python3 facts.py RELIANCE.NS
    python3 facts.py TCS.NS --json
"""

import argparse
import json
import os
import sys

# Ensure project root is in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import yfinance as yf
from trader_core.formatting import format_inr, format_lakh_crore, format_pct
from trader_core.universe import clean_symbol


def analyze_company_fundamentals(symbol: str) -> dict:
    """Extract key fundamentals and financial metrics for an Indian stock."""
    sym = clean_symbol(symbol)
    ticker = yf.Ticker(sym)
    info = ticker.info or {}

    mcap = info.get("marketCap", 0)
    pe = info.get("trailingPE")
    forward_pe = info.get("forwardPE")
    pb = info.get("priceToBook")
    roe = info.get("returnOnEquity")
    profit_margin = info.get("profitMargins")
    debt_equity = info.get("debtToEquity")
    high52 = info.get("fiftyTwoWeekHigh")
    low52 = info.get("fiftyTwoWeekLow")
    dividend_yield = info.get("dividendYield")
    sector = info.get("sector", "Diversified")
    industry = info.get("industry", "Indian Equities")
    currency = info.get("currency", "INR")
    company_name = info.get("longName", sym)

    # Classify market cap tier in Indian terms
    # Large Cap > ₹20,000 Cr; Mid Cap ₹5,000 - ₹20,000 Cr; Small Cap < ₹5,000 Cr
    mcap_cr = (mcap / 10_000_000.0) if mcap else 0.0
    if mcap_cr >= 20000:
        cap_category = "LARGE CAP"
    elif mcap_cr >= 5000:
        cap_category = "MID CAP"
    else:
        cap_category = "SMALL CAP"

    facts = {
        "symbol": sym,
        "company_name": company_name,
        "sector": sector,
        "industry": industry,
        "cap_category": cap_category,
        "market_cap_inr": mcap,
        "market_cap_formatted": format_lakh_crore(mcap),
        "valuation": {
            "trailing_pe": round(pe, 2) if pe else "N/A",
            "forward_pe": round(forward_pe, 2) if forward_pe else "N/A",
            "price_to_book": round(pb, 2) if pb else "N/A",
            "dividend_yield_pct": f"{(dividend_yield * 100 if dividend_yield < 1.0 else dividend_yield):.2f}%" if dividend_yield else "0.0%",
        },
        "profitability": {
            "roe_pct": round(roe * 100, 2) if roe else "N/A",
            "net_margin_pct": round(profit_margin * 100, 2) if profit_margin else "N/A",
            "debt_to_equity": round(debt_equity / 100.0, 2) if debt_equity else "N/A",
        },
        "range_52w": {
            "high": round(high52, 2) if high52 else "N/A",
            "low": round(low52, 2) if low52 else "N/A",
        },
    }
    return facts


def print_facts_terminal(facts: dict):
    print("=" * 76)
    print(f" COMPANY FUNDAMENTALS: {facts['company_name']} ({facts['symbol']})")
    print(f" Sector: {facts['sector']} | Industry: {facts['industry']} | Cap: {facts['cap_category']}")
    print("=" * 76)
    print(f" Market Capitalization: {facts['market_cap_formatted']}")
    print(f" 52-Week Range:         Low: {format_inr(facts['range_52w']['low'])}  -  High: {format_inr(facts['range_52w']['high'])}")
    print("-" * 76)
    v = facts["valuation"]
    p = facts["profitability"]
    print(" VALUATION & EARNINGS MULTIPLES:")
    print(f"  Trailing P/E:         {v['trailing_pe']}x")
    print(f"  Forward P/E:          {v['forward_pe']}x")
    print(f"  Price-to-Book (P/B):  {v['price_to_book']}x")
    print(f"  Dividend Yield:       {v['dividend_yield_pct']}")
    print("-" * 76)
    print(" FINANCIAL HEALTH & PROFITABILITY:")
    print(f"  Return on Equity (ROE): {p['roe_pct']}%")
    print(f"  Net Profit Margin:      {p['net_margin_pct']}%")
    print(f"  Debt-to-Equity:         {p['debt_to_equity']}")
    print("=" * 76)


def main():
    parser = argparse.ArgumentParser(description="Fundamental Analyst for Indian Stocks")
    parser.add_argument("symbol", nargs="?", default="SBIN.NS", help="NSE stock ticker (e.g. SBIN.NS, RELIANCE.NS)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    try:
        facts = analyze_company_fundamentals(args.symbol)
        if args.json:
            print(json.dumps(facts, indent=2))
        else:
            print_facts_terminal(facts)
        sys.exit(0)
    except Exception as e:
        print(f"Error fetching fundamentals for {args.symbol}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
