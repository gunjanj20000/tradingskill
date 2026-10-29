---
name: trader-alerts
description: "Price and level alert monitor for Indian stocks (NSE/BSE). Alerts on Stop-Loss, Profit Targets, and the mandatory 15:15 IST intraday square-off cutoff."
---

# Price & Technical Alerts (`trader-alerts`)

Monitors market prices and alerts when key risk thresholds or time cutoffs are reached.

## Features
- **Auto-Config from Plan**: Automatically imports Stop-Loss, Take-Profit, and 15:15 IST square-off levels from `trader/plan.json`.
- **Custom Price Triggers**: Supports alerts on break above resistance or break below support.
- **IST Square-off Notification**: Reminds you to close open intraday positions before broker auto-square-off fees.

## CLI Usage

```bash
# Add alerts directly from current trade plan
python3 trader-alerts/alerts.py add --from-plan

# Add custom price alert
python3 trader-alerts/alerts.py add --symbol SBIN.NS --price 980.00 --condition above --note "Breakout level"

# Check active alerts against live LTP
python3 trader-alerts/alerts.py check

# List configured alerts
python3 trader-alerts/alerts.py list
```
