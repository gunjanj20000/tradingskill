---
name: trader-timemachine
description: "Time Machine simulator for Indian stocks (NSE/BSE). Replays 10,000 Monte Carlo paths of a trade before risking real capital, drawing on historical 5m bars from the National Stock Exchange."
---

# Time Machine Simulator (`trader-timemachine`)

Replays planned day trades using empirical 5-minute historical bar returns from the National Stock Exchange of India (NSE).

## Features
- **10,000 Monte Carlo Replays**: Walks the remaining intraday bars from entry to the 15:15 IST square-off.
- **Conservative Stop Evaluation**: If a simulated candle touches both the stop and target, the stop is registered first.
- **Statistical Probability Breakdown**:
  - Target Hit % (Take-profit reached first).
  - Stop Hit % (Stop-loss reached first).
  - Open at Close % (Position remaining active until 15:15 IST).
  - Expected R (Expected value per trade in terms of risk units).
- **Fan Chart & Percentiles**: Displays 5th, 50th (median), and 95th price percentiles.
- **Honest Mathematical Verdict**: Benchmarks the empirical target hit rate against the theoretical breakeven requirement.

## CLI Usage

```bash
# Replay active plan in trader/plan.json
python3 trader-timemachine/timemachine.py run --write

# Custom number of replays and seed
python3 trader-timemachine/timemachine.py run --replays 10000 --seed 42 --write

# Custom parameters without reading plan.json
python3 trader-timemachine/timemachine.py run --symbol SBIN.NS --entry 971.90 --stop 968.06 --target 979.58

# Display ASCII fan chart
python3 trader-timemachine/timemachine.py chart
```
