"""Data feed manager for Indian stocks (NSE/BSE).

Fetches historical and intraday candle data via yfinance / Yahoo Finance v8 JSON,
with local disk caching and support for offline playback.
"""

import datetime
import json
import os
import time
import warnings
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import yfinance as yf

from trader_core.universe import clean_symbol

warnings.filterwarnings("ignore")

IST = ZoneInfo("Asia/Kolkata")
CACHE_DIR = Path("/home/ubuntu/tradingskill/trader/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def fetch_bars(
    symbol: str,
    period: str = "5d",
    interval: str = "5m",
    max_age_seconds: int = 60,
    offline_file: str | None = None,
) -> pd.DataFrame:
    """Fetch OHLCV dataframe for an Indian stock.
    
    Columns returned: ['Open', 'High', 'Low', 'Close', 'Volume']
    Index is DatetimeIndex in Asia/Kolkata timezone.
    """
    symbol = clean_symbol(symbol)
    
    if offline_file and os.path.exists(offline_file):
        with open(offline_file, "r") as f:
            data = json.load(f)
        if isinstance(data, list):
            df = pd.DataFrame(data)
            df["Datetime"] = pd.to_datetime(df["Datetime"])
            df.set_index("Datetime", inplace=True)
            return df

    # Check local disk cache
    cache_key = f"{symbol}_{period}_{interval}.json"
    cache_path = CACHE_DIR / cache_key
    if cache_path.exists():
        mtime = cache_path.stat().st_mtime
        if (time.time() - mtime) < max_age_seconds:
            try:
                cached_df = pd.read_json(cache_path)
                if not cached_df.empty:
                    if not isinstance(cached_df.index, pd.DatetimeIndex):
                        cached_df.index = pd.to_datetime(cached_df.index)
                    if cached_df.index.tz is None:
                        cached_df.index = cached_df.index.tz_localize("UTC").tz_convert(IST)
                    else:
                        cached_df.index = cached_df.index.tz_convert(IST)
                    return cached_df
            except Exception:
                pass

    # Download via yfinance
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
    except Exception as e:
        # If cache exists even if old, use it as fallback
        if cache_path.exists():
            df = pd.read_json(cache_path)
            if not isinstance(df.index, pd.DatetimeIndex):
                df.index = pd.to_datetime(df.index)
            return df
        raise RuntimeError(f"Failed to fetch data for {symbol}: {e}")

    if df.empty:
        raise ValueError(f"No price bars returned for symbol '{symbol}' ({period}, {interval})")

    # Clean columns
    keep_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
    df = df[keep_cols].copy()
    df.dropna(inplace=True)

    # Ensure index is in IST
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC").tz_convert(IST)
    else:
        df.index = df.index.tz_convert(IST)

    # Cache locally
    try:
        df.to_json(cache_path, date_format="iso")
    except Exception:
        pass

    return df


def get_latest_price(symbol: str) -> float:
    """Get the latest traded price (LTP) in INR for a symbol."""
    df = fetch_bars(symbol, period="1d", interval="1m", max_age_seconds=30)
    if not df.empty:
        return float(df["Close"].iloc[-1])
    raise ValueError(f"Could not retrieve price for {symbol}")
