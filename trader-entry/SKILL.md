---
name: trader-entry
description: "Bar-by-bar entry timing system for Indian stocks (NSE/BSE). Confirms exact candle close trigger, volume confirmation, and technical indicator alignment while respecting IST trading hours."
---

# Entry Timer (`trader-entry`)

Monitors setup execution bar-by-bar and confirms the exact moment to enter a trade on Indian exchanges.

## Features
- **Candle Close Validation**: Enforces full candle close to eliminate wick fakeouts.
- **Volume Confirmation**: Verifies volume multiplier against opening range or average volume.
- **Multi-Indicator Confluence Check**: Requires price > VWAP, SuperTrend alignment, and high bullish confluence.
- **NSE Trading Hours Guard**: Enforces entry windows (09:20 - 14:45 IST) and flags expired setups.
- **Automated Workflow**: Writes `trader/entry.json` upon trigger confirmation to feed downstream exit and budget sizing.

## CLI Usage

```bash
# Check single symbol entry status
python3 trader-entry/entry.py check SBIN.NS --setup confluence --write

# Check Opening Range Breakout (ORB)
python3 trader-entry/entry.py check RELIANCE.NS --setup orb --interval 5m

# Check specific price level breakout
python3 trader-entry/entry.py check INFY.NS --setup level --level 1150.00

# Continuous bar-by-bar watch until trigger or cutoff
python3 trader-entry/entry.py watch SBIN.NS --every 30 --until 15:15

# Check all candidates from the latest watchlist
python3 trader-entry/entry.py watchlist --write
```
