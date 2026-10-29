---
name: trader-indicators
description: "Comprehensive Technical Indicator Engine for Indian Stocks (NSE/BSE). Computes 60+ indicators across Trend, Momentum, Volatility, Volume, Pivots (CPR, Camarilla), and Candlestick patterns with consensus scoring."
---

# Technical Indicator Engine (`trader-indicators`)

Calculates 60+ technical indicators specifically designed for Indian equities (NSE/BSE).

## Features
- **Trend Indicators**: SMA (20, 50, 200), EMA (9, 20, 50, 200), WMA, HMA, DEMA, TEMA, VWMA, MACD, SuperTrend (ATR 10, mult 3.0), ADX (+DI, -DI), Aroon, Parabolic SAR, Ichimoku Cloud (Tenkan, Kijun, Span A/B), Vortex, DPO.
- **Momentum & Oscillators**: RSI 14 & 9 (Wilder's), Stochastic (%K, %D), StochRSI, Williams %R, CCI, ROC, Momentum, Money Flow Index (MFI), Ultimate Oscillator, Awesome Oscillator (AO), Accelerator Oscillator (AC), True Strength Index (TSI), Chande Momentum Oscillator (CMO), Fisher Transform.
- **Volatility**: ATR 14, NATR %, Bollinger Bands (Upper, Mid, Lower, Bandwidth, %B), Keltner Channels, Donchian Channels, Annualized Historical Volatility, Chaikin Volatility.
- **Volume**: Intraday Anchored VWAP, VWAP Standard Deviation Bands (±1σ, ±2σ), On-Balance Volume (OBV), Chaikin Money Flow (CMF 20), Accumulation/Distribution Line (ADL), Force Index, Ease of Movement (EOM), Relative Volume (RVOL).
- **Indian Pivots & Levels**:
  - **CPR (Central Pivot Range)**: Pivot, TC, BC, Width %, and Narrow vs Wide classification (Narrow CPR = High probability trending day).
  - **Camarilla Pivots**: H1-H5, L1-L5 (H3/L3 reversal levels, H4/L4 explosive breakout levels).
  - **Classical Floor Pivots & Fibonacci Pivots**: R1-R3, S1-S3.
- **Candlestick Patterns**: Bullish/Bearish Engulfing, Hammer, Inverted Hammer, Shooting Star, Hanging Man, Doji (Dragonfly, Gravestone), Morning/Evening Star, Marubozu, Inside/Outside Bar, Pinbars.
- **Consensus Scoring**: Aggregates all indicators into Bullish, Bearish, and Neutral tallies to generate a final rating: `STRONG BUY`, `BUY`, `NEUTRAL`, `SELL`, `STRONG SELL`.

## CLI Usage

```bash
# Analyze an Indian stock (default 15m intraday bars)
python3 trader-indicators/indicators.py RELIANCE.NS

# Different interval and period
python3 trader-indicators/indicators.py TCS.NS --interval 5m --period 5d
python3 trader-indicators/indicators.py HDFCBANK.NS --interval 1d --period 1mo

# Output JSON format
python3 trader-indicators/indicators.py INFY.NS --json
```
