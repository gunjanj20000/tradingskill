---
name: trader-budget
description: "Position sizing and capital management for Indian stocks (NSE/BSE). Sizes orders in INR (₹) based on risk per trade, SEBI 5x MIS intraday margin rules, and writes trader/orders.json."
---

# Budget & Position Sizing Manager (`trader-budget`)

Sizes every trade according to your account capital, maximum risk per trade, and SEBI margin rules.

## Features
- **Fixed Fractional Risk Sizing**:
  - `Quantity = Max Risk (₹) / Risk per share (₹)`
  - Exact loss capped at the stop-loss price.
- **SEBI MIS Intraday Margin Compliance**:
  - 5x intraday equity leverage (minimum 20% margin requirement).
  - Automatically bounds notional size to account buying power.
- **Bracket Order Structure**:
  - Pre-binds Entry (Limit/Market), Stop-Loss, and Take-Profit legs.
- **Automated Workflow**:
  - Reads `trader/plan.json` and outputs `trader/orders.json`.

## CLI Usage

```bash
# Size trade from active plan.json and config.json
python3 trader-budget/size.py --write

# Custom account capital and max risk
python3 trader-budget/size.py --capital 200000 --max-risk 1500 --write

# Cash n Carry (CNC) delivery order (1x leverage, 100% margin)
python3 trader-budget/size.py --product CNC --write
```
