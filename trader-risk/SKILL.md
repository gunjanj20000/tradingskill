---
name: trader-risk
description: "Pre-trade risk manager for Indian stocks (NSE/BSE). Hard-checks proposed orders against account rules, daily loss limits, SEBI guidelines, and IST trading windows before allowing execution."
---

# Risk Manager (`trader-risk`)

Checks every order against your capital limits, maximum loss per trade, SEBI guidelines, and trading windows.

## Enforcement Rules
- **Format & Leg Validity**: Verifies valid ticker, positive quantity, valid limit price, and stop-loss leg.
- **Stop Requirement**: Requires stop-loss strictly below entry for longs (`require_stop: true`).
- **Max Loss Per Trade**: Caps potential loss at stop to `max_risk_per_trade_inr` (e.g. ₹1,000).
- **Reward to Risk**: Mandates minimum `min_reward_risk` (e.g. 1:1.5).
- **Cumulative Daily Loss Guard**: Restricts additional entries once total risk reaches `max_daily_loss_inr`.
- **Trading Window Guard**: Blocks entries outside permitted hours (09:20 - 14:45 IST).
- **Surveillance & Blocklist**: Blocks any tickers flagged under SEBI ASM/GSM surveillance.
- **Cryptographic Fingerprint**: Writes approved order hashes to `trader/state/risk.json`.

## CLI Usage

```bash
# Run risk check against trader/orders.json
python3 trader-risk/check.py

# Test or run off-hours
python3 trader-risk/check.py --ignore-time-check

# Output JSON
python3 trader-risk/check.py --json
```
