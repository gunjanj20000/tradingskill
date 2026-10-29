---
name: trader-exit
description: "Exit & Target Planner for Indian stocks (NSE/BSE). Sets stop-loss and profit targets (ATR, SuperTrend, VWAP, CPR, Camarilla, R-multiples) before entering, and enforces Indian market 15:15 IST square-off."
---

# Exit Planner (`trader-exit`)

Calculates exact Stop-Loss and Take-Profit price levels before risking capital.

## Features
- **Dynamic Indicator Stops**:
  - `atr:K`: K times 14-period ATR below entry (e.g. `atr:1.5`).
  - `supertrend`: Recent SuperTrend support level.
  - `vwap`: Intraday VWAP support level.
  - `cpr-bc`: Central Pivot Range Bottom Central.
  - `pct:X` or `price:X`: Percentage or fixed price stop.
- **Target Multiples**:
  - `1R`, `1.5R`, `2R`, `3R`: Multiple of risk per share.
  - `cpr-r1`: Central Pivot Range Resistance 1.
  - `camarilla-h4`: Camarilla H4 explosive breakout level.
- **SEBI / Indian Broker Rules**:
  - Mandatory Intraday MIS Square-Off cutoff (`flat_by: 15:15` IST).
  - Minimum Reward-to-Risk ratio enforcement (default >= 1.5).
- **Automated Workflow**:
  - Reads `trader/entry.json` and writes `trader/plan.json`.

## CLI Usage

```bash
# Plan from latest trader/entry.json
python3 trader-exit/exit.py plan --stop atr:1.5 --target 2R --write

# SuperTrend stop with Camarilla H4 target
python3 trader-exit/exit.py plan --stop supertrend --target camarilla-h4 --write

# Explicit symbol and price plan
python3 trader-exit/exit.py plan --symbol SBIN.NS --entry 971.90 --stop atr:1.5 --target 2R --write

# View active plan
python3 trader-exit/exit.py show
```
