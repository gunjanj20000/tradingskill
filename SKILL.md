---
name: indian-day-trader-skill
description: "Comprehensive Day-Trading & Quantitative Analysis Desk for Indian Stocks (NSE/BSE). Includes 60+ technical indicators, automated chart scanner, bar-by-bar entry timer, ATR/CPR exit planner, Monte Carlo Time Machine simulator, SEBI 5x MIS position sizer, pre-trade risk checks, paper trading engine, Zerodha/Angel One payloads, FII/DII institutional flows, and breaking news sentiment."
---

# Indian Day Trader Skill (`indian-day-trader-skill`)

Turn your agent into a professional quantitative trading desk for Indian equities (NSE & BSE).

## Key Modules & Tools

| Module | Command | Purpose |
| :--- | :--- | :--- |
| **`trader-indicators`** | `python3 trader.py indicators <SYMBOL>` | Calculates **60+ technical indicators** across Trend, Momentum, Volatility, Volume, Pivots (CPR, Camarilla), and Candlestick patterns with consensus scoring. |
| **`trader-scanner`** | `python3 trader.py scan --universe nifty50` | Scans Nifty 50, Nifty Bank, Nifty Next 50, and F&O stocks for setups (ORB, Multi-Indicator Confluence, SuperTrend+VWAP, CPR Breakouts, Volume Spikes). |
| **`trader-entry`** | `python3 trader.py entry check <SYMBOL>` | Bar-by-bar entry timing, candle close confirmation, volume filter, and IST trading windows (09:20 - 14:45 IST). |
| **`trader-exit`** | `python3 trader.py plan --stop atr:1.5 --target 2R` | Stop-loss and target planner with ATR, SuperTrend, VWAP, CPR, Camarilla, and mandatory 15:15 IST flat-by cutoff. |
| **`trader-timemachine`**| `python3 trader.py timemachine <SYMBOL>` | Replays 10,000 Monte Carlo sessions using empirical 5m bars from the National Stock Exchange (NSE). |
| **`trader-budget`** | `python3 trader.py budget` | Sizes positions in INR (₹) using SEBI 5x MIS intraday margin rules and max risk per trade. |
| **`trader-risk`** | `python3 trader.py risk` | Pre-trade risk check (daily loss limits, reward:risk, trading hours, surveillance blocklist). |
| **`trader-broker`** | `python3 trader.py broker show / execute` | Paper trading simulator & export payloads for Zerodha Kite Connect, Angel One SmartAPI, and Dhan. |
| **`trader-alerts`** | `python3 trader.py alerts check` | Monitors Stop-Loss, Targets, and the 15:15 IST square-off alert. |
| **`trader-fiidii`** | `python3 trader.py fiidii flows` | Tracks daily FII & DII cash flows (₹ Cr), index futures long ratio, and NSE bulk/block deals. |
| **`trader-news`** | `python3 trader.py news <SYMBOL>` | Live Indian stock market headlines, corporate actions, and automated sentiment tagging. |
| **`trader-analyst`** | `python3 trader.py analyst <SYMBOL>` | Fundamental valuation (P/E, P/B, EV/EBITDA), ROE, margins, and 52-week ranges. |
| **`full-cycle`** | `python3 trader.py full-cycle <SYMBOL>` | Runs the complete 9-step automated pipeline from indicator calculation to broker ticket generation. |

## Quick Start

```bash
# 1. Calculate all 60+ technical indicators on an Indian stock
python3 trader.py indicators RELIANCE.NS

# 2. Scan Nifty 50 for SuperTrend + VWAP trend breakouts
python3 trader.py scan --universe nifty50 --setup supertrend_vwap

# 3. Run complete automated day trading pipeline on State Bank of India
python3 trader.py full-cycle SBIN.NS
```
