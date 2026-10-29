---
name: trader-scanner
description: "Market and chart scanner for Indian stocks (NSE/BSE). Scans Nifty 50, Nifty Bank, Nifty Next 50, and F&O universes for high-probability setups like ORB, Multi-Indicator Confluence, SuperTrend+VWAP, and CPR breakouts."
---

# Chart Scanner (`trader-scanner`)

Scans Indian stock universes for high-probability intraday and swing setups.

## Supported Setups
- `confluence`: Comprehensive multi-indicator confirmation (>= 70% bullish technical signals).
- `supertrend_vwap`: SuperTrend is bullish + Price > VWAP + Price > EMA20.
- `orb`: 15-minute or 30-minute Opening Range Breakout with volume confirmation.
- `cpr_breakout`: Central Pivot Range breakout (Narrow CPR setups for trending moves).
- `camarilla_h4`: Breakout above Camarilla H4 level for explosive momentum.
- `volume_shocker`: Relative volume >= 2.0x 20-period average with solid candle.
- `oversold_bounce`: RSI < 35 with bullish reversal candlestick.

## Universes
- `nifty50`: Top 50 bluechip liquid Indian stocks.
- `niftybank`: 12 liquid banking stocks.
- `niftynext50`: 50 large-to-midcap market leaders.
- `fno`: High-liquidity F&O trading universe.
- Custom symbols via `--symbols`.

## CLI Usage

```bash
# Scan Nifty 50 for SuperTrend + VWAP trend surge
python3 trader-scanner/scan.py --universe nifty50 --setup supertrend_vwap

# Scan Nifty Bank for Opening Range Breakout and write to watchlist
python3 trader-scanner/scan.py --universe niftybank --setup orb --write

# Confluence scan on custom stock list
python3 trader-scanner/scan.py --symbols RELIANCE.NS,TCS.NS,HDFCBANK.NS,SBIN.NS,INFY.NS --setup confluence --write

# Output JSON
python3 trader-scanner/scan.py --setup cpr_breakout --json
```
