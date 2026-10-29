---
name: trader-analyst
description: "Fundamental and quarterly financial analyst for Indian companies (NSE/BSE). Evaluates valuation multiples (P/E, P/B), profitability (ROE, margins), market cap classification, and 52-week ranges."
---

# Fundamental Analyst (`trader-analyst`)

Analyzes fundamental health, valuation, and quarterly metrics for Indian equities.

## Key Metrics Evaluated
- **Market Cap Tier**: Categorizes as Large Cap (> ₹20,000 Cr), Mid Cap (₹5,000 - ₹20,000 Cr), or Small Cap (< ₹5,000 Cr).
- **Valuation**: Trailing P/E, Forward P/E, Price-to-Book (P/B), Dividend Yield.
- **Profitability**: Return on Equity (ROE), Net Profit Margin (PAT %).
- **Range & Solvency**: 52-Week High/Low and Debt-to-Equity.

## CLI Usage

```bash
# Fundamental analysis of an Indian stock
python3 trader-analyst/facts.py SBIN.NS
python3 trader-analyst/facts.py RELIANCE.NS

# Output JSON
python3 trader-analyst/facts.py TCS.NS --json
```
