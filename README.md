# Indian Day Trader Skill & Quantitative Trading Desk 🇮🇳

A modular, institutional-grade day-trading and quantitative analysis desk built specifically for **Indian Equities (NSE & BSE)**. Inspired by `day-trader-skill`, adapted for Indian market mechanics (IST hours, SEBI 5x MIS intraday margin rules, FII/DII institutional flows, CPR & Camarilla pivots), and loaded with **all major technical indicators**.

```
scanner -> indicators -> entry -> exit -> timemachine -> budget -> risk -> broker
alerts: stop, target, 15:15 IST flat-by cutoff                             (active trade)
news / analyst / fiidii                                                   (market context)
```

Free, MIT license, no mandatory API key required for core analysis, real-time data from free public feeds.

---

## 🚀 Key Highlights

1. **60+ Technical Indicators Engine**: Trend (SuperTrend, MACD, ADX, Aroon, Parabolic SAR, Ichimoku Cloud, Moving Averages 9 to 200), Momentum (RSI 14/9, Stochastic, StochRSI, Williams %R, CCI, MFI, TSI, Awesome Osc, CMO), Volatility (ATR, Bollinger Bands, Keltner, Donchian), Volume (Intraday anchored VWAP with ±1σ/±2σ bands, RVOL, CMF, OBV), Indian Intraday Pivots (CPR: Pivot/TC/BC/Width, Camarilla H1-H5/L1-L5), and Candlestick Pattern Recognition.
2. **Indian Stock Universes**: Nifty 50, Nifty Bank, Nifty Next 50, and high-liquidity F&O universe.
3. **Time Machine Replay Simulator**: Before risking ₹1, replays 10,000 Monte Carlo simulated sessions drawn from historical 5-minute bars on the National Stock Exchange of India (NSE).
4. **INR & SEBI Margin Compliant**: Sizes positions in ₹ using SEBI intraday MIS margin rules (maximum 5x leverage, 20% margin requirement).
5. **Strict Safety & Paper First**: Default paper trading simulator, cryptographic order fingerprinting, and mandatory human confirmation (`"yes"`) before order dispatch.
6. **Broker Integrations**: Ready-to-use payloads and code generators for **Zerodha Kite Connect**, **Angel One SmartAPI**, **Dhan HQ API**, and **Groww / Upstox / Fyers** webhooks.
7. **Institutional Smart Money Tracking (FII / DII)**: Daily Foreign & Domestic Institutional Cash Market flows in ₹ Crores, FII Index Futures Long/Short ratio, and NSE Bulk / Block deals.

---

## 🛠️ The 12 Modular Tools

| Command | Module | What It Does |
| :--- | :--- | :--- |
| `trader-indicators` | Indicator Engine | Computes 60+ technical indicators & builds a multi-indicator consensus rating (`STRONG BUY`, `BUY`, `NEUTRAL`, `SELL`, `STRONG SELL`). |
| `trader-scanner` | Market Scanner | Scans Nifty 50, Nifty Bank, or F&O stocks for setups (ORB, Confluence, SuperTrend+VWAP, CPR Breakout, Volume Shockers). |
| `trader-entry` | Entry Timer | Watches candles bar-by-bar (1m, 3m, 5m, 15m), checks candle close beyond levels, and enforces 09:20 - 14:45 IST entry windows. |
| `trader-exit` | Exit Planner | Calculates Stop-Loss and Target levels (ATR, SuperTrend, VWAP, CPR, Camarilla, R-multiples) and sets the 15:15 IST square-off cutoff. |
| `trader-timemachine`| Time Machine | Replays 10,000 simulated sessions from empirical NSE intraday bars to benchmark win rates and expected R. |
| `trader-budget` | Position Sizer | Sizes orders in INR (₹) based on max risk per trade and SEBI 5x MIS intraday margin rules. |
| `trader-risk` | Risk Manager | Pre-trade risk check (daily loss limits, reward:risk, trading hours, surveillance blocklist). |
| `trader-broker` | Order Executor | Paper trading simulator & export payloads for Zerodha Kite Connect, Angel One SmartAPI, and Dhan. |
| `trader-alerts` | Price Alerts | Monitors Stop-Loss, Targets, and the 15:15 IST square-off alert. |
| `trader-fiidii` | FII/DII Tracker | Tracks daily FII & DII cash flows (₹ Cr), index futures long ratio, and NSE bulk/block deals. |
| `trader-news` | News & Sentiment | Live Indian stock market headlines, corporate actions, and automated sentiment tagging. |
| `trader-analyst` | Fundamental Analyst | Fundamental valuation (P/E, P/B, EV/EBITDA), ROE, margins, and 52-week ranges. |

---

## 📊 Complete Technical Indicators Catalog

### 1. Trend Indicators
- **Moving Averages**: SMA (20, 50, 200), EMA (9, 20, 50, 200), WMA, HMA (Hull), DEMA (Double EMA), TEMA (Triple EMA), VWMA (Volume Weighted MA).
- **MACD**: MACD Line (12, 26), Signal Line (9), Histogram.
- **SuperTrend**: ATR Period 10, Multiplier 3.0, Trend direction (+1 Bullish / -1 Bearish).
- **ADX / DMI**: Average Directional Index (14), +DI, -DI.
- **Aroon**: Aroon Up, Aroon Down, Aroon Oscillator.
- **Parabolic SAR**: Step 0.02, Maximum 0.20, Trend direction.
- **Ichimoku Cloud**: Tenkan-sen (9), Kijun-sen (26), Senkou Span A, Senkou Span B (52), Chikou Span.
- **Vortex Indicator**: VI+, VI- (14-period).
- **Detrended Price Oscillator (DPO)**.

### 2. Momentum & Oscillators
- **RSI**: Relative Strength Index 14 & 9 with Wilder's Smoothing.
- **Stochastic Oscillator**: Fast %K, Slow %D with 3-period smoothing.
- **Stochastic RSI**: StochRSI Fast %K, Fast %D.
- **Williams %R**: 14-period normalized range oscillator.
- **CCI**: Commodity Channel Index (20-period).
- **Rate of Change (ROC)**: 14-period momentum rate.
- **Money Flow Index (MFI)**: Volume-weighted 14-period RSI.
- **Ultimate Oscillator**: Weighted 7, 14, and 28 period momentum.
- **Awesome Oscillator (AO)** & **Accelerator Oscillator (AC)**.
- **True Strength Index (TSI)**: Double-smoothed momentum.
- **Chande Momentum Oscillator (CMO)** & **Fisher Transform**.

### 3. Volatility Indicators
- **ATR & NATR**: Average True Range (14) and Normalized ATR % of close.
- **Bollinger Bands**: 20 SMA, 2.0 std dev (Upper, Mid, Lower, Bandwidth %, %B).
- **Keltner Channels**: 20 EMA, 2.0 ATR (Upper, Mid, Lower).
- **Donchian Channels**: 20-period High/Low/Mid channels.
- **Historical Volatility (HV)**: Annualized standard deviation of log returns.

### 4. Volume Indicators
- **Intraday Anchored VWAP**: Volume Weighted Average Price anchored to the 09:15 IST opening session.
- **VWAP Standard Deviation Bands**: ±1σ and ±2σ dynamic bands.
- **On-Balance Volume (OBV)** & **Accumulation/Distribution Line (ADL)**.
- **Chaikin Money Flow (CMF 20)**.
- **Relative Volume (RVOL)**: Current candle volume vs 20-period average volume.
- **Force Index** & **Ease of Movement (EOM)**.

### 5. Pivots & Levels (Indian Intraday Essentials)
- **Central Pivot Range (CPR)**:
  - Pivot (P) = $(High + Low + Close) / 3$
  - Bottom Central (BC) = $(High + Low) / 2$
  - Top Central (TC) = $(Pivot - BC) + Pivot$
  - CPR Width % (Narrow CPR indicates high probability trending move).
- **Camarilla Pivots**: H1 to H5, L1 to L5 (H3/L3 reversal zones, H4/L4 breakout targets).
- **Classical Floor Pivots & Fibonacci Pivots**: R1-R3, S1-S3.

### 6. Japanese Candlestick Patterns
- Doji (Dragonfly, Gravestone, Long-legged)
- Hammer, Inverted Hammer, Shooting Star, Hanging Man
- Bullish & Bearish Engulfing
- Morning Star & Evening Star
- Bullish & Bearish Marubozu
- Inside Bar (Harami) & Outside Bar
- Bullish & Bearish Pinbars (Rejection Wicks)

---

## ⚡ Quick Start & Usage

### 1. Unified Master CLI (`trader.py`)

```bash
# Run complete 9-step automated pipeline for a stock
python3 trader.py full-cycle SBIN.NS

# Calculate all 60+ technical indicators
python3 trader.py indicators RELIANCE.NS

# Scan Nifty 50 for SuperTrend + VWAP trend surges
python3 trader.py scan --universe nifty50 --setup supertrend_vwap

# Plan trade exit & risk levels
python3 trader.py plan SBIN.NS --stop atr:1.5 --target 2R

# Run Time Machine 10,000 Monte Carlo replay
python3 trader.py timemachine SBIN.NS

# Size position in INR using SEBI MIS 5x leverage
python3 trader.py budget

# Check pre-trade risk constraints
python3 trader.py risk --ignore-time-check

# View broker ticket and execute paper trade
python3 trader.py broker show
python3 trader.py broker execute --confirm "yes"

# Check active paper portfolio and P&L
python3 trader.py broker status

# View daily FII / DII net cash flows & bulk deals
python3 trader.py fiidii flows
python3 trader.py fiidii bulk

# Check news & fundamental analyst
python3 trader.py news SBIN.NS
python3 trader.py analyst SBIN.NS
```

### 2. Standalone Submodule Execution

You can also run any module directly:

```bash
python3 trader-indicators/indicators.py SBIN.NS --interval 15m
python3 trader-scanner/scan.py --universe niftybank --setup orb --write
python3 trader-entry/entry.py check SBIN.NS --setup confluence --write
python3 trader-exit/exit.py plan --stop supertrend --target 2R --write
python3 trader-timemachine/timemachine.py run --replays 5000 --write
python3 trader-budget/size.py --capital 200000 --max-risk 2000 --write
python3 trader-risk/check.py --ignore-time-check
python3 trader-broker/ticket.py execute --confirm "yes"
python3 trader-alerts/alerts.py add --from-plan
python3 trader-alerts/alerts.py check
```

---

## 🧪 Running Unit Tests

Run the complete offline test suite:

```bash
python3 -m unittest discover -s tests -v
```

All tests run deterministically and verify mathematical accuracy of indicators, pivot equations, SEBI margin formulas, order fingerprinting, and risk limits.

---

## 🔒 Safety & Regulatory Compliance

- **Paper Trading by Default**: Safeguards capital in `trader/state/portfolio.json`.
- **Explicit Human Approval**: No trade is ever placed without typing `--confirm "yes"`.
- **SEBI Margin Norms**: Strictly enforces 5x intraday MIS leverage (20% upfront margin).
- **IST Trading Hours**: Restricts intraday entries to 09:20 - 14:45 IST and enforces a mandatory 15:15 IST flat-by square-off before broker auto-squareoff penalties.
- **Disclaimer**: For research, algorithmic backtesting, and educational purposes. Not financial advice.
