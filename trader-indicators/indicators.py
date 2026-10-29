#!/usr/bin/env python3
"""Technical Indicator Engine for Indian Stocks (NSE/BSE).

Calculates 60+ technical indicators across:
1. Trend (SMA, EMA, WMA, HMA, DEMA, TEMA, VWMA, MACD, SuperTrend, ADX/+DI/-DI, Aroon, Parabolic SAR, Ichimoku, Vortex, DPO)
2. Momentum (RSI, Stochastic %K/%D, StochRSI, Williams %R, CCI, ROC, MOM, MFI, Ultimate Osc, Awesome Osc, Accelerator Osc, TSI, CMO, Fisher Transform)
3. Volatility (ATR, NATR, Bollinger Bands, Keltner Channels, Donchian Channels, Historical Volatility, Chaikin Volatility)
4. Volume (Intraday VWAP, VWAP Bands ±1/2/3σ, OBV, CMF, ADL, Force Index, EOM, Volume ROC, RVOL)
5. Pivots & Levels (CPR: Pivot/TC/BC/Width, Camarilla H1-H5/L1-L5, Classical Floor Pivots, Fibonacci Pivots, Woodie Pivots)
6. Candlestick Patterns (Doji, Hammer, Shooting Star, Engulfing, Morning/Evening Star, Marubozu, Pinbars, Inside/Outside Bars)
7. Multi-Indicator Consensus & Confluence Scoring (STRONG BUY, BUY, NEUTRAL, SELL, STRONG SELL)

Usage:
    python3 indicators.py RELIANCE.NS
    python3 indicators.py TCS.NS --interval 15m --period 5d
    python3 indicators.py HDFCBANK.NS --category trend,volume,pivots
    python3 indicators.py INFY.NS --json
"""

import argparse
import json
import math
import os
import sys

# Ensure project root is in python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import numpy as np
import pandas as pd

from trader_core.data_feed import fetch_bars
from trader_core.formatting import format_inr, format_pct
from trader_core.universe import clean_symbol


class TechnicalIndicators:
    """Comprehensive technical indicators calculation engine."""

    def __init__(self, df: pd.DataFrame):
        if df.empty or len(df) < 5:
            raise ValueError("Insufficient price bars to compute indicators (minimum 5 required)")
        self.df = df.copy()
        self.open = df["Open"].to_numpy(copy=True).astype(float)
        self.high = df["High"].to_numpy(copy=True).astype(float)
        self.low = df["Low"].to_numpy(copy=True).astype(float)
        self.close = df["Close"].to_numpy(copy=True).astype(float)
        self.volume = df["Volume"].to_numpy(copy=True).astype(float)
        self.n = len(self.df)

    # -------------------------------------------------------------
    # 1. TREND INDICATORS
    # -------------------------------------------------------------
    def sma(self, period: int = 20) -> np.ndarray:
        """Simple Moving Average."""
        s = pd.Series(self.close)
        return s.rolling(window=period, min_periods=1).mean().to_numpy(copy=True)

    def ema(self, period: int = 20) -> np.ndarray:
        """Exponential Moving Average."""
        s = pd.Series(self.close)
        return s.ewm(span=period, adjust=False).mean().to_numpy(copy=True)

    def wma(self, period: int = 20) -> np.ndarray:
        """Weighted Moving Average."""
        weights = np.arange(1, period + 1)
        res = np.zeros(self.n)
        for i in range(self.n):
            if i < period - 1:
                w = np.arange(1, i + 2)
                res[i] = np.dot(self.close[:i + 1], w) / w.sum()
            else:
                res[i] = np.dot(self.close[i - period + 1:i + 1], weights) / weights.sum()
        return res

    def hma(self, period: int = 20) -> np.ndarray:
        """Hull Moving Average."""
        half_period = int(period / 2)
        sqrt_period = int(math.sqrt(period))
        wma_half = self.wma(half_period)
        wma_full = self.wma(period)
        diff = 2 * wma_half - wma_full
        
        # WMA of the diff with sqrt_period
        weights = np.arange(1, sqrt_period + 1)
        res = np.zeros(self.n)
        for i in range(self.n):
            if i < sqrt_period - 1:
                w = np.arange(1, i + 2)
                res[i] = np.dot(diff[:i + 1], w) / w.sum()
            else:
                res[i] = np.dot(diff[i - sqrt_period + 1:i + 1], weights) / weights.sum()
        return res

    def dema(self, period: int = 20) -> np.ndarray:
        """Double Exponential Moving Average: 2*EMA - EMA(EMA)."""
        ema1 = self.ema(period)
        s_ema1 = pd.Series(ema1)
        ema2 = s_ema1.ewm(span=period, adjust=False).mean().to_numpy(copy=True)
        return 2 * ema1 - ema2

    def tema(self, period: int = 20) -> np.ndarray:
        """Triple Exponential Moving Average: 3*EMA - 3*EMA(EMA) + EMA(EMA(EMA))."""
        ema1 = self.ema(period)
        ema2 = pd.Series(ema1).ewm(span=period, adjust=False).mean().to_numpy(copy=True)
        ema3 = pd.Series(ema2).ewm(span=period, adjust=False).mean().to_numpy(copy=True)
        return 3 * ema1 - 3 * ema2 + ema3

    def vwma(self, period: int = 20) -> np.ndarray:
        """Volume Weighted Moving Average."""
        pv = self.close * self.volume
        sum_pv = pd.Series(pv).rolling(window=period, min_periods=1).sum().to_numpy(copy=True)
        sum_vol = pd.Series(self.volume).rolling(window=period, min_periods=1).sum().to_numpy(copy=True)
        sum_vol[sum_vol == 0] = 1.0
        return sum_pv / sum_vol

    def macd(self, fast: int = 12, slow: int = 26, signal_span: int = 9):
        """Moving Average Convergence Divergence."""
        ema_fast = self.ema(fast)
        ema_slow = self.ema(slow)
        macd_line = ema_fast - ema_slow
        signal_line = pd.Series(macd_line).ewm(span=signal_span, adjust=False).mean().to_numpy(copy=True)
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram

    def supertrend(self, period: int = 10, multiplier: float = 3.0):
        """SuperTrend Indicator (widely used in Indian Intraday Trading)."""
        atr_vals = self.atr(period)
        hl2 = (self.high + self.low) / 2.0
        basic_upper = hl2 + (multiplier * atr_vals)
        basic_lower = hl2 - (multiplier * atr_vals)

        final_upper = np.zeros(self.n)
        final_lower = np.zeros(self.n)
        st = np.zeros(self.n)
        direction = np.zeros(self.n)  # 1 = Bullish, -1 = Bearish

        for i in range(self.n):
            if i == 0:
                final_upper[i] = basic_upper[i]
                final_lower[i] = basic_lower[i]
                direction[i] = 1 if self.close[i] >= hl2[i] else -1
                st[i] = final_lower[i] if direction[i] == 1 else final_upper[i]
                continue

            # Final Upper Band
            if basic_upper[i] < final_upper[i - 1] or self.close[i - 1] > final_upper[i - 1]:
                final_upper[i] = basic_upper[i]
            else:
                final_upper[i] = final_upper[i - 1]

            # Final Lower Band
            if basic_lower[i] > final_lower[i - 1] or self.close[i - 1] < final_lower[i - 1]:
                final_lower[i] = basic_lower[i]
            else:
                final_lower[i] = final_lower[i - 1]

            # SuperTrend Direction
            if direction[i - 1] == 1:
                if self.close[i] < final_lower[i]:
                    direction[i] = -1
                    st[i] = final_upper[i]
                else:
                    direction[i] = 1
                    st[i] = final_lower[i]
            else:
                if self.close[i] > final_upper[i]:
                    direction[i] = 1
                    st[i] = final_lower[i]
                else:
                    direction[i] = -1
                    st[i] = final_upper[i]

        return st, direction, final_upper, final_lower

    def adx(self, period: int = 14):
        """Average Directional Index with +DI and -DI."""
        plus_dm = np.zeros(self.n)
        minus_dm = np.zeros(self.n)
        tr = np.zeros(self.n)

        for i in range(1, self.n):
            h_diff = self.high[i] - self.high[i - 1]
            l_diff = self.low[i - 1] - self.low[i]
            plus_dm[i] = h_diff if (h_diff > l_diff and h_diff > 0) else 0.0
            minus_dm[i] = l_diff if (l_diff > h_diff and l_diff > 0) else 0.0
            tr[i] = max(
                self.high[i] - self.low[i],
                abs(self.high[i] - self.close[i - 1]),
                abs(self.low[i] - self.close[i - 1]),
            )

        # Wilder's smoothing
        atr_s = pd.Series(tr).ewm(alpha=1/period, adjust=False).mean().to_numpy(copy=True)
        plus_di = 100 * (pd.Series(plus_dm).ewm(alpha=1/period, adjust=False).mean().to_numpy(copy=True) / np.where(atr_s == 0, 1, atr_s))
        minus_di = 100 * (pd.Series(minus_dm).ewm(alpha=1/period, adjust=False).mean().to_numpy(copy=True) / np.where(atr_s == 0, 1, atr_s))
        
        sum_di = plus_di + minus_di
        sum_di[sum_di == 0] = 1.0
        dx = 100 * (np.abs(plus_di - minus_di) / sum_di)
        adx_val = pd.Series(dx).ewm(alpha=1/period, adjust=False).mean().to_numpy(copy=True)
        return adx_val, plus_di, minus_di

    def aroon(self, period: int = 14):
        """Aroon Indicator: Aroon Up, Aroon Down, Aroon Oscillator."""
        aroon_up = np.zeros(self.n)
        aroon_down = np.zeros(self.n)
        for i in range(self.n):
            if i < period:
                sub_h = self.high[:i + 1]
                sub_l = self.low[:i + 1]
                p = max(1, i)
            else:
                sub_h = self.high[i - period:i + 1]
                sub_l = self.low[i - period:i + 1]
                p = period
            high_idx = np.argmax(sub_h)
            low_idx = np.argmin(sub_l)
            aroon_up[i] = ((p - (len(sub_h) - 1 - high_idx)) / p) * 100
            aroon_down[i] = ((p - (len(sub_l) - 1 - low_idx)) / p) * 100
        aroon_osc = aroon_up - aroon_down
        return aroon_up, aroon_down, aroon_osc

    def parabolic_sar(self, step: float = 0.02, max_step: float = 0.20):
        """Parabolic SAR (Stop and Reverse)."""
        sar = np.zeros(self.n)
        direction = np.zeros(self.n)  # 1 = Bullish (uptrend), -1 = Bearish (downtrend)
        if self.n < 2:
            return sar, direction

        # Initial conditions
        direction[0] = 1 if self.close[1] >= self.close[0] else -1
        af = step
        ep = self.high[0] if direction[0] == 1 else self.low[0]
        sar[0] = self.low[0] if direction[0] == 1 else self.high[0]

        for i in range(1, self.n):
            prev_sar = sar[i - 1]
            prev_dir = direction[i - 1]

            if prev_dir == 1:
                current_sar = prev_sar + af * (ep - prev_sar)
                if i >= 2:
                    current_sar = min(current_sar, self.low[i - 1], self.low[i - 2])
                else:
                    current_sar = min(current_sar, self.low[i - 1])

                if self.low[i] < current_sar:
                    direction[i] = -1
                    sar[i] = ep
                    af = step
                    ep = self.low[i]
                else:
                    direction[i] = 1
                    sar[i] = current_sar
                    if self.high[i] > ep:
                        ep = self.high[i]
                        af = min(af + step, max_step)
            else:
                current_sar = prev_sar + af * (ep - prev_sar)
                if i >= 2:
                    current_sar = max(current_sar, self.high[i - 1], self.high[i - 2])
                else:
                    current_sar = max(current_sar, self.high[i - 1])

                if self.high[i] > current_sar:
                    direction[i] = 1
                    sar[i] = ep
                    af = step
                    ep = self.high[i]
                else:
                    direction[i] = -1
                    sar[i] = current_sar
                    if self.low[i] < ep:
                        ep = self.low[i]
                        af = min(af + step, max_step)

        return sar, direction

    def ichimoku(self, tenkan_n: int = 9, kijun_n: int = 26, senkou_b_n: int = 52):
        """Ichimoku Kinko Hyo: Tenkan-sen, Kijun-sen, Senkou Span A, Senkou Span B, Chikou Span."""
        def hl_mean(p):
            roll_h = pd.Series(self.high).rolling(p, min_periods=1).max()
            roll_l = pd.Series(self.low).rolling(p, min_periods=1).min()
            return ((roll_h + roll_l) / 2.0).to_numpy(copy=True)

        tenkan_sen = hl_mean(tenkan_n)
        kijun_sen = hl_mean(kijun_n)
        senkou_span_a = (tenkan_sen + kijun_sen) / 2.0
        senkou_span_b = hl_mean(senkou_b_n)
        chikou_span = np.roll(self.close, -kijun_n).astype(float).copy()
        chikou_span[-kijun_n:] = np.nan
        return tenkan_sen, kijun_sen, senkou_span_a, senkou_span_b, chikou_span

    def vortex(self, period: int = 14):
        """Vortex Indicator: VI+, VI-."""
        tr = np.zeros(self.n)
        vm_plus = np.zeros(self.n)
        vm_minus = np.zeros(self.n)

        for i in range(1, self.n):
            tr[i] = max(
                self.high[i] - self.low[i],
                abs(self.high[i] - self.close[i - 1]),
                abs(self.low[i] - self.close[i - 1]),
            )
            vm_plus[i] = abs(self.high[i] - self.low[i - 1])
            vm_minus[i] = abs(self.low[i] - self.high[i - 1])

        tr_sum = pd.Series(tr).rolling(period, min_periods=1).sum().to_numpy(copy=True)
        tr_sum[tr_sum == 0] = 1.0
        vi_plus = pd.Series(vm_plus).rolling(period, min_periods=1).sum().to_numpy(copy=True) / tr_sum
        vi_minus = pd.Series(vm_minus).rolling(period, min_periods=1).sum().to_numpy(copy=True) / tr_sum
        return vi_plus, vi_minus

    def dpo(self, period: int = 20) -> np.ndarray:
        """Detrended Price Oscillator."""
        shift = int(period / 2 + 1)
        sma = self.sma(period)
        res = np.zeros(self.n)
        for i in range(self.n):
            if i >= shift:
                res[i] = self.close[i] - sma[i - shift]
            else:
                res[i] = 0.0
        return res

    # -------------------------------------------------------------
    # 2. MOMENTUM INDICATORS & OSCILLATORS
    # -------------------------------------------------------------
    def rsi(self, period: int = 14) -> np.ndarray:
        """Relative Strength Index (Wilder's Smoothing)."""
        delta = np.diff(self.close, prepend=self.close[0])
        gain = np.where(delta > 0, delta, 0.0)
        loss = np.where(delta < 0, -delta, 0.0)

        avg_gain = pd.Series(gain).ewm(alpha=1/period, adjust=False).mean().to_numpy(copy=True)
        avg_loss = pd.Series(loss).ewm(alpha=1/period, adjust=False).mean().to_numpy(copy=True)

        rs = np.divide(avg_gain, avg_loss, out=np.zeros_like(avg_gain), where=avg_loss != 0)
        rsi_val = 100.0 - (100.0 / (1.0 + rs))
        rsi_val[avg_loss == 0] = 100.0
        return rsi_val

    def stochastic(self, k_period: int = 14, d_period: int = 3):
        """Stochastic Oscillator (%K, %D)."""
        low_min = pd.Series(self.low).rolling(k_period, min_periods=1).min().to_numpy(copy=True)
        high_max = pd.Series(self.high).rolling(k_period, min_periods=1).max().to_numpy(copy=True)
        denom = high_max - low_min
        denom[denom == 0] = 1.0
        k = 100.0 * ((self.close - low_min) / denom)
        d = pd.Series(k).rolling(d_period, min_periods=1).mean().to_numpy(copy=True)
        return k, d

    def stoch_rsi(self, rsi_period: int = 14, stoch_period: int = 14, k_period: int = 3, d_period: int = 3):
        """Stochastic RSI."""
        r = self.rsi(rsi_period)
        r_min = pd.Series(r).rolling(stoch_period, min_periods=1).min().to_numpy(copy=True)
        r_max = pd.Series(r).rolling(stoch_period, min_periods=1).max().to_numpy(copy=True)
        denom = r_max - r_min
        denom[denom == 0] = 1.0
        stoch = 100.0 * ((r - r_min) / denom)
        fast_k = pd.Series(stoch).rolling(k_period, min_periods=1).mean().to_numpy(copy=True)
        fast_d = pd.Series(fast_k).rolling(d_period, min_periods=1).mean().to_numpy(copy=True)
        return fast_k, fast_d

    def williams_r(self, period: int = 14) -> np.ndarray:
        """Williams %R."""
        high_max = pd.Series(self.high).rolling(period, min_periods=1).max().to_numpy(copy=True)
        low_min = pd.Series(self.low).rolling(period, min_periods=1).min().to_numpy(copy=True)
        denom = high_max - low_min
        denom[denom == 0] = 1.0
        return -100.0 * ((high_max - self.close) / denom)

    def cci(self, period: int = 20) -> np.ndarray:
        """Commodity Channel Index."""
        tp = (self.high + self.low + self.close) / 3.0
        sma_tp = pd.Series(tp).rolling(period, min_periods=1).mean().to_numpy(copy=True)
        mad = pd.Series(tp).rolling(period, min_periods=1).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True).to_numpy(copy=True)
        mad[mad == 0] = 1.0
        return (tp - sma_tp) / (0.015 * mad)

    def roc(self, period: int = 14) -> np.ndarray:
        """Rate of Change (%)."""
        res = np.zeros(self.n)
        for i in range(self.n):
            if i >= period and self.close[i - period] != 0:
                res[i] = ((self.close[i] - self.close[i - period]) / self.close[i - period]) * 100.0
        return res

    def mom(self, period: int = 10) -> np.ndarray:
        """Momentum indicator."""
        res = np.zeros(self.n)
        for i in range(self.n):
            if i >= period:
                res[i] = self.close[i] - self.close[i - period]
        return res

    def mfi(self, period: int = 14) -> np.ndarray:
        """Money Flow Index."""
        tp = (self.high + self.low + self.close) / 3.0
        raw_money_flow = tp * self.volume
        pos_flow = np.zeros(self.n)
        neg_flow = np.zeros(self.n)

        for i in range(1, self.n):
            if tp[i] > tp[i - 1]:
                pos_flow[i] = raw_money_flow[i]
            elif tp[i] < tp[i - 1]:
                neg_flow[i] = raw_money_flow[i]

        pos_sum = pd.Series(pos_flow).rolling(period, min_periods=1).sum().to_numpy(copy=True)
        neg_sum = pd.Series(neg_flow).rolling(period, min_periods=1).sum().to_numpy(copy=True)
        neg_sum[neg_sum == 0] = 1.0
        money_ratio = pos_sum / neg_sum
        return 100.0 - (100.0 / (1.0 + money_ratio))

    def ultimate_oscillator(self, s_period: int = 7, m_period: int = 14, l_period: int = 28) -> np.ndarray:
        """Ultimate Oscillator."""
        bp = np.zeros(self.n)
        tr = np.zeros(self.n)
        for i in range(self.n):
            prev_c = self.close[i - 1] if i > 0 else self.low[i]
            bp[i] = self.close[i] - min(self.low[i], prev_c)
            tr[i] = max(self.high[i], prev_c) - min(self.low[i], prev_c)

        tr_s7 = pd.Series(tr).rolling(s_period, min_periods=1).sum().to_numpy(copy=True)
        tr_s14 = pd.Series(tr).rolling(m_period, min_periods=1).sum().to_numpy(copy=True)
        tr_s28 = pd.Series(tr).rolling(l_period, min_periods=1).sum().to_numpy(copy=True)

        bp_s7 = pd.Series(bp).rolling(s_period, min_periods=1).sum().to_numpy(copy=True)
        bp_s14 = pd.Series(bp).rolling(m_period, min_periods=1).sum().to_numpy(copy=True)
        bp_s28 = pd.Series(bp).rolling(l_period, min_periods=1).sum().to_numpy(copy=True)

        tr_s7[tr_s7 == 0] = 1.0
        tr_s14[tr_s14 == 0] = 1.0
        tr_s28[tr_s28 == 0] = 1.0

        avg7 = bp_s7 / tr_s7
        avg14 = bp_s14 / tr_s14
        avg28 = bp_s28 / tr_s28

        return 100.0 * ((4.0 * avg7 + 2.0 * avg14 + avg28) / 7.0)

    def awesome_oscillator(self) -> np.ndarray:
        """Awesome Oscillator (AO): SMA(HL2, 5) - SMA(HL2, 34)."""
        hl2 = (self.high + self.low) / 2.0
        s5 = pd.Series(hl2).rolling(5, min_periods=1).mean().to_numpy(copy=True)
        s34 = pd.Series(hl2).rolling(34, min_periods=1).mean().to_numpy(copy=True)
        return s5 - s34

    def accelerator_oscillator(self) -> np.ndarray:
        """Accelerator Oscillator (AC): AO - SMA(AO, 5)."""
        ao = self.awesome_oscillator()
        ao_sma = pd.Series(ao).rolling(5, min_periods=1).mean().to_numpy(copy=True)
        return ao - ao_sma

    def tsi(self, long_period: int = 25, short_period: int = 13) -> np.ndarray:
        """True Strength Index."""
        diff = np.diff(self.close, prepend=self.close[0])
        abs_diff = np.abs(diff)

        smooth_diff = pd.Series(diff).ewm(span=long_period, adjust=False).mean()
        double_smooth_diff = smooth_diff.ewm(span=short_period, adjust=False).mean().to_numpy(copy=True)

        smooth_abs = pd.Series(abs_diff).ewm(span=long_period, adjust=False).mean()
        double_smooth_abs = smooth_abs.ewm(span=short_period, adjust=False).mean().to_numpy(copy=True)
        double_smooth_abs[double_smooth_abs == 0] = 1.0

        return 100.0 * (double_smooth_diff / double_smooth_abs)

    def cmo(self, period: int = 14) -> np.ndarray:
        """Chande Momentum Oscillator."""
        diff = np.diff(self.close, prepend=self.close[0])
        pos = np.where(diff > 0, diff, 0.0)
        neg = np.where(diff < 0, -diff, 0.0)

        sum_pos = pd.Series(pos).rolling(period, min_periods=1).sum().to_numpy(copy=True)
        sum_neg = pd.Series(neg).rolling(period, min_periods=1).sum().to_numpy(copy=True)
        denom = sum_pos + sum_neg
        denom[denom == 0] = 1.0
        return 100.0 * ((sum_pos - sum_neg) / denom)

    def fisher_transform(self, period: int = 9):
        """Fisher Transform."""
        hl2 = (self.high + self.low) / 2.0
        min_hl2 = pd.Series(hl2).rolling(period, min_periods=1).min().to_numpy(copy=True)
        max_hl2 = pd.Series(hl2).rolling(period, min_periods=1).max().to_numpy(copy=True)
        denom = max_hl2 - min_hl2
        denom[denom == 0] = 1.0

        val = 0.66 * ((hl2 - min_hl2) / denom - 0.5)
        # bound to (-0.999, 0.999)
        val = np.clip(val, -0.999, 0.999)
        
        fish = np.zeros(self.n)
        for i in range(1, self.n):
            fish[i] = 0.5 * math.log((1 + val[i]) / (1 - val[i])) + 0.5 * fish[i - 1]
        fish_signal = pd.Series(fish).shift(1).fillna(0).to_numpy(copy=True)
        return fish, fish_signal

    # -------------------------------------------------------------
    # 3. VOLATILITY INDICATORS
    # -------------------------------------------------------------
    def atr(self, period: int = 14) -> np.ndarray:
        """Average True Range (Wilder's Smoothing)."""
        tr = np.zeros(self.n)
        for i in range(self.n):
            if i == 0:
                tr[i] = self.high[i] - self.low[i]
            else:
                tr[i] = max(
                    self.high[i] - self.low[i],
                    abs(self.high[i] - self.close[i - 1]),
                    abs(self.low[i] - self.close[i - 1]),
                )
        return pd.Series(tr).ewm(alpha=1/period, adjust=False).mean().to_numpy(copy=True)

    def natr(self, period: int = 14) -> np.ndarray:
        """Normalized Average True Range (% of Close)."""
        atr_vals = self.atr(period)
        return (atr_vals / self.close) * 100.0

    def bollinger_bands(self, period: int = 20, num_std: float = 2.0):
        """Bollinger Bands: Upper, Middle, Lower, Bandwidth, %B."""
        s = pd.Series(self.close)
        mid = s.rolling(period, min_periods=1).mean().to_numpy(copy=True)
        std = s.rolling(period, min_periods=1).std(ddof=0).fillna(0).to_numpy(copy=True)
        upper = mid + (num_std * std)
        lower = mid - (num_std * std)
        bandwidth = np.divide(upper - lower, mid, out=np.zeros_like(mid), where=mid != 0) * 100.0
        denom = upper - lower
        denom[denom == 0] = 1.0
        percent_b = (self.close - lower) / denom
        return upper, mid, lower, bandwidth, percent_b

    def keltner_channels(self, period: int = 20, multiplier: float = 2.0):
        """Keltner Channels: Upper, Middle, Lower."""
        mid = self.ema(period)
        atr_vals = self.atr(period)
        upper = mid + (multiplier * atr_vals)
        lower = mid - (multiplier * atr_vals)
        return upper, mid, lower

    def donchian_channels(self, period: int = 20):
        """Donchian Channels: Upper, Middle, Lower."""
        upper = pd.Series(self.high).rolling(period, min_periods=1).max().to_numpy(copy=True)
        lower = pd.Series(self.low).rolling(period, min_periods=1).min().to_numpy(copy=True)
        mid = (upper + lower) / 2.0
        return upper, mid, lower

    def historical_volatility(self, period: int = 20) -> np.ndarray:
        """Annualized Historical Volatility from log returns."""
        log_ret = np.log(self.close[1:] / self.close[:-1])
        log_ret = np.insert(log_ret, 0, 0.0)
        vol = pd.Series(log_ret).rolling(period, min_periods=1).std(ddof=1).fillna(0).to_numpy(copy=True)
        # Assuming 252 trading sessions per year in India
        return vol * math.sqrt(252) * 100.0

    def chaikin_volatility(self, period: int = 10, roc_period: int = 10) -> np.ndarray:
        """Chaikin Volatility."""
        hl_diff = self.high - self.low
        ema_hl = pd.Series(hl_diff).ewm(span=period, adjust=False).mean().to_numpy(copy=True)
        res = np.zeros(self.n)
        for i in range(self.n):
            if i >= roc_period and ema_hl[i - roc_period] != 0:
                res[i] = ((ema_hl[i] - ema_hl[i - roc_period]) / ema_hl[i - roc_period]) * 100.0
        return res

    # -------------------------------------------------------------
    # 4. VOLUME INDICATORS
    # -------------------------------------------------------------
    def vwap(self):
        """Intraday Anchored Volume Weighted Average Price with Standard Deviation Bands."""
        pv = self.close * self.volume
        
        # Check if index has date information to anchor per day
        if isinstance(self.df.index, pd.DatetimeIndex):
            dates = self.df.index.date
        else:
            dates = np.zeros(self.n)

        vwap_arr = np.zeros(self.n)
        upper_1 = np.zeros(self.n)
        lower_1 = np.zeros(self.n)
        upper_2 = np.zeros(self.n)
        lower_2 = np.zeros(self.n)

        curr_date = None
        cum_pv = 0.0
        cum_vol = 0.0
        day_prices = []
        day_vols = []

        for i in range(self.n):
            d = dates[i]
            if d != curr_date:
                curr_date = d
                cum_pv = 0.0
                cum_vol = 0.0
                day_prices = []
                day_vols = []

            cum_pv += pv[i]
            cum_vol += self.volume[i]
            day_prices.append(self.close[i])
            day_vols.append(self.volume[i])

            v = cum_pv / cum_vol if cum_vol > 0 else self.close[i]
            vwap_arr[i] = v

            # Calculate weighted standard deviation
            if cum_vol > 0 and len(day_prices) > 1:
                weights = np.array(day_vols) / cum_vol
                variance = np.sum(weights * (np.array(day_prices) - v) ** 2)
                std_dev = math.sqrt(max(0, variance))
            else:
                std_dev = 0.0

            upper_1[i] = v + std_dev
            lower_1[i] = v - std_dev
            upper_2[i] = v + 2 * std_dev
            lower_2[i] = v - 2 * std_dev

        return vwap_arr, upper_1, lower_1, upper_2, lower_2

    def obv(self) -> np.ndarray:
        """On-Balance Volume."""
        res = np.zeros(self.n)
        for i in range(1, self.n):
            if self.close[i] > self.close[i - 1]:
                res[i] = res[i - 1] + self.volume[i]
            elif self.close[i] < self.close[i - 1]:
                res[i] = res[i - 1] - self.volume[i]
            else:
                res[i] = res[i - 1]
        return res

    def cmf(self, period: int = 20) -> np.ndarray:
        """Chaikin Money Flow."""
        hl = self.high - self.low
        hl[hl == 0] = 1.0
        mfv = (((self.close - self.low) - (self.high - self.close)) / hl) * self.volume
        sum_mfv = pd.Series(mfv).rolling(period, min_periods=1).sum().to_numpy(copy=True)
        sum_vol = pd.Series(self.volume).rolling(period, min_periods=1).sum().to_numpy(copy=True)
        sum_vol[sum_vol == 0] = 1.0
        return sum_mfv / sum_vol

    def adl(self) -> np.ndarray:
        """Accumulation/Distribution Line."""
        hl = self.high - self.low
        hl[hl == 0] = 1.0
        clv = ((self.close - self.low) - (self.high - self.close)) / hl
        return np.cumsum(clv * self.volume)

    def force_index(self, period: int = 13) -> np.ndarray:
        """Force Index."""
        fi_raw = np.diff(self.close, prepend=self.close[0]) * self.volume
        return pd.Series(fi_raw).ewm(span=period, adjust=False).mean().to_numpy(copy=True)

    def eom(self, period: int = 14) -> np.ndarray:
        """Ease of Movement."""
        hl2 = (self.high + self.low) / 2.0
        distance = np.diff(hl2, prepend=hl2[0])
        hl_diff = self.high - self.low
        box_ratio = np.divide(self.volume / 100_000_000.0, hl_diff, out=np.zeros_like(hl_diff), where=hl_diff != 0)
        eom_raw = np.divide(distance, box_ratio, out=np.zeros_like(distance), where=box_ratio != 0)
        return pd.Series(eom_raw).rolling(period, min_periods=1).mean().to_numpy(copy=True)

    def rvol(self, period: int = 20) -> np.ndarray:
        """Relative Volume (Current Volume / 20-period average)."""
        avg_v = pd.Series(self.volume).rolling(period, min_periods=1).mean().to_numpy(copy=True)
        avg_v[avg_v == 0] = 1.0
        return self.volume / avg_v

    # -------------------------------------------------------------
    # 5. PIVOTS & KEY LEVELS (INDIAN INTRADAY ESSENTIALS)
    # -------------------------------------------------------------
    def cpr(self):
        """Central Pivot Range (CPR): Pivot, Top Central (TC), Bottom Central (BC), Width %.
        Crucial for Indian day traders (Narrow CPR = High probability breakout day).
        """
        # CPR calculated from previous session's H, L, C
        prev_h = self.high[-2] if self.n >= 2 else self.high[-1]
        prev_l = self.low[-2] if self.n >= 2 else self.low[-1]
        prev_c = self.close[-2] if self.n >= 2 else self.close[-1]

        pivot = (prev_h + prev_l + prev_c) / 3.0
        bc = (prev_h + prev_l) / 2.0
        tc = (pivot - bc) + pivot

        # Ensure TC is top, BC is bottom
        actual_tc = max(tc, bc)
        actual_bc = min(tc, bc)
        width_pct = (abs(actual_tc - actual_bc) / pivot) * 100.0

        r1 = 2 * pivot - prev_l
        s1 = 2 * pivot - prev_h
        r2 = pivot + (prev_h - prev_l)
        s2 = pivot - (prev_h - prev_l)
        r3 = r1 + (prev_h - prev_l)
        s3 = s1 - (prev_h - prev_l)

        return {
            "pivot": pivot,
            "tc": actual_tc,
            "bc": actual_bc,
            "width_pct": width_pct,
            "is_narrow": width_pct < 0.25,  # Narrow CPR indicates trending potential
            "r1": r1, "r2": r2, "r3": r3,
            "s1": s1, "s2": s2, "s3": s3,
        }

    def camarilla_pivots(self):
        """Camarilla Pivots (H1-H5, L1-L5).
        H3/L3 are reversal zones; H4/L4 are explosive breakout/breakdown levels.
        """
        prev_h = self.high[-2] if self.n >= 2 else self.high[-1]
        prev_l = self.low[-2] if self.n >= 2 else self.low[-1]
        prev_c = self.close[-2] if self.n >= 2 else self.close[-1]
        diff = prev_h - prev_l

        h4 = prev_c + diff * 1.1 / 2.0  # Breakout long level
        h3 = prev_c + diff * 1.1 / 4.0  # Mean reversion sell level
        h2 = prev_c + diff * 1.1 / 6.0
        h1 = prev_c + diff * 1.1 / 12.0

        l1 = prev_c - diff * 1.1 / 12.0
        l2 = prev_c - diff * 1.1 / 6.0
        l3 = prev_c - diff * 1.1 / 4.0  # Mean reversion buy level
        l4 = prev_c - diff * 1.1 / 2.0  # Breakdown short level
        h5 = (prev_h / prev_l) * prev_c if prev_l > 0 else h4 * 1.05
        l5 = prev_c - (h5 - prev_c)

        return {
            "h5": h5, "h4": h4, "h3": h3, "h2": h2, "h1": h1,
            "l1": l1, "l2": l2, "l3": l3, "l4": l4, "l5": l5,
        }

    def fibonacci_pivots(self):
        """Fibonacci Pivot Points."""
        prev_h = self.high[-2] if self.n >= 2 else self.high[-1]
        prev_l = self.low[-2] if self.n >= 2 else self.low[-1]
        prev_c = self.close[-2] if self.n >= 2 else self.close[-1]
        diff = prev_h - prev_l
        p = (prev_h + prev_l + prev_c) / 3.0

        return {
            "pivot": p,
            "r1": p + 0.382 * diff,
            "r2": p + 0.618 * diff,
            "r3": p + 1.000 * diff,
            "s1": p - 0.382 * diff,
            "s2": p - 0.618 * diff,
            "s3": p - 1.000 * diff,
        }

    # -------------------------------------------------------------
    # 6. CANDLESTICK PATTERNS
    # -------------------------------------------------------------
    def candlestick_patterns(self) -> dict[str, bool]:
        """Detect key Japanese Candlestick Patterns on latest candles."""
        if self.n < 3:
            return {}

        c0, c1, c2 = self.close[-1], self.close[-2], self.close[-3]
        o0, o1, o2 = self.open[-1], self.open[-2], self.open[-3]
        h0, h1, h2 = self.high[-1], self.high[-2], self.high[-3]
        l0, l1, l2 = self.low[-1], self.low[-2], self.low[-3]

        body0 = abs(c0 - o0)
        rng0 = h0 - l0 if (h0 - l0) > 0 else 1e-4
        upper_wick0 = h0 - max(c0, o0)
        lower_wick0 = min(c0, o0) - l0

        body1 = abs(c1 - o1)
        rng1 = h1 - l1 if (h1 - l1) > 0 else 1e-4

        # Doji
        is_doji = (body0 / rng0) < 0.1
        is_dragonfly_doji = is_doji and (lower_wick0 / rng0 > 0.6) and (upper_wick0 / rng0 < 0.15)
        is_gravestone_doji = is_doji and (upper_wick0 / rng0 > 0.6) and (lower_wick0 / rng0 < 0.15)

        # Hammer & Shooting Star
        is_hammer = (lower_wick0 >= 2.0 * body0) and (upper_wick0 <= 0.2 * body0) and (body0 / rng0 > 0.15)
        is_inverted_hammer = (upper_wick0 >= 2.0 * body0) and (lower_wick0 <= 0.2 * body0) and (body0 / rng0 > 0.15)
        is_shooting_star = is_inverted_hammer and (c1 > o1)  # after uptrend
        is_hanging_man = is_hammer and (c1 > o1)

        # Engulfing
        bullish_engulfing = (c1 < o1) and (c0 > o0) and (c0 >= o1) and (o0 <= c1)
        bearish_engulfing = (c1 > o1) and (c0 < o0) and (c0 <= o1) and (o0 >= c1)

        # Marubozu (strong conviction candle)
        bullish_marubozu = (c0 > o0) and (body0 / rng0 >= 0.85)
        bearish_marubozu = (c0 < o0) and (body0 / rng0 >= 0.85)

        # Morning Star & Evening Star (3-candle patterns)
        morning_star = (c2 < o2) and (body1 / rng1 < 0.3) and (c0 > o0) and (c0 > (o2 + c2) / 2)
        evening_star = (c2 > o2) and (body1 / rng1 < 0.3) and (c0 < o0) and (c0 < (o2 + c2) / 2)

        # Inside Bar (Harami)
        inside_bar = (h0 <= h1) and (l0 >= l1)

        # Pinbars
        bullish_pinbar = (lower_wick0 / rng0 >= 0.66)
        bearish_pinbar = (upper_wick0 / rng0 >= 0.66)

        return {
            "doji": bool(is_doji),
            "dragonfly_doji": bool(is_dragonfly_doji),
            "gravestone_doji": bool(is_gravestone_doji),
            "hammer": bool(is_hammer),
            "shooting_star": bool(is_shooting_star),
            "bullish_engulfing": bool(bullish_engulfing),
            "bearish_engulfing": bool(bearish_engulfing),
            "bullish_marubozu": bool(bullish_marubozu),
            "bearish_marubozu": bool(bearish_marubozu),
            "morning_star": bool(morning_star),
            "evening_star": bool(evening_star),
            "inside_bar": bool(inside_bar),
            "bullish_pinbar": bool(bullish_pinbar),
            "bearish_pinbar": bool(bearish_pinbar),
        }

    # -------------------------------------------------------------
    # 7. MULTI-INDICATOR CONSENSUS & CONFLUENCE MATRIX
    # -------------------------------------------------------------
    def compute_all(self) -> dict:
        """Compute all indicators, extract current readings and build consensus score."""
        price = float(self.close[-1])
        vol = float(self.volume[-1])

        # Moving Averages
        sma20 = float(self.sma(20)[-1])
        sma50 = float(self.sma(50)[-1])
        sma200 = float(self.sma(200)[-1])
        ema9 = float(self.ema(9)[-1])
        ema20 = float(self.ema(20)[-1])
        ema50 = float(self.ema(50)[-1])
        ema200 = float(self.ema(200)[-1])
        hma20 = float(self.hma(20)[-1])
        dema20 = float(self.dema(20)[-1])
        tema20 = float(self.tema(20)[-1])
        vwma20 = float(self.vwma(20)[-1])

        # MACD
        macd_line, macd_sig, macd_hist = self.macd()
        macd_l, macd_s, macd_h = float(macd_line[-1]), float(macd_sig[-1]), float(macd_hist[-1])

        # SuperTrend
        st_val, st_dir, st_up, st_dn = self.supertrend()
        supertrend_val = float(st_val[-1])
        supertrend_bullish = bool(st_dir[-1] == 1)

        # ADX
        adx_val, p_di, m_di = self.adx()
        adx_cur, plus_di, minus_di = float(adx_val[-1]), float(p_di[-1]), float(m_di[-1])

        # Aroon
        ar_up, ar_dn, ar_osc = self.aroon()
        aroon_up, aroon_dn, aroon_osc = float(ar_up[-1]), float(ar_dn[-1]), float(ar_osc[-1])

        # Parabolic SAR
        psar_vals, psar_dirs = self.parabolic_sar()
        psar_val, psar_bullish = float(psar_vals[-1]), bool(psar_dirs[-1] == 1)

        # Ichimoku
        tenkan, kijun, span_a, span_b, _ = self.ichimoku()
        ich_tenkan, ich_kijun = float(tenkan[-1]), float(kijun[-1])
        ich_span_a, ich_span_b = float(span_a[-1]), float(span_b[-1])

        # Oscillators
        rsi14 = float(self.rsi(14)[-1])
        rsi9 = float(self.rsi(9)[-1])
        stoch_k, stoch_d = self.stochastic()
        k_val, d_val = float(stoch_k[-1]), float(stoch_d[-1])
        stoch_rsi_k, stoch_rsi_d = self.stoch_rsi()
        srsi_k, srsi_d = float(stoch_rsi_k[-1]), float(stoch_rsi_d[-1])
        williams = float(self.williams_r()[-1])
        cci_val = float(self.cci()[-1])
        roc14 = float(self.roc(14)[-1])
        mfi14 = float(self.mfi(14)[-1])
        ao_val = float(self.awesome_oscillator()[-1])
        ac_val = float(self.accelerator_oscillator()[-1])
        tsi_val = float(self.tsi()[-1])
        cmo_val = float(self.cmo()[-1])

        # Volatility
        atr14 = float(self.atr(14)[-1])
        natr14 = float(self.natr(14)[-1])
        bb_upper, bb_mid, bb_lower, bb_width, bb_pct_b = self.bollinger_bands()
        b_up, b_mid, b_low = float(bb_upper[-1]), float(bb_mid[-1]), float(bb_lower[-1])
        b_width, b_pct = float(bb_width[-1]), float(bb_pct_b[-1])
        kc_up, kc_mid, kc_low = self.keltner_channels()
        k_up, k_mid, k_low = float(kc_up[-1]), float(kc_mid[-1]), float(kc_low[-1])
        dc_up, dc_mid, dc_low = self.donchian_channels()
        d_up, d_mid, d_low = float(dc_up[-1]), float(dc_mid[-1]), float(dc_low[-1])
        hv20 = float(self.historical_volatility()[-1])

        # Volume
        vwap_arr, vu1, vl1, vu2, vl2 = self.vwap()
        vwap_val = float(vwap_arr[-1])
        vwap_u1, vwap_l1 = float(vu1[-1]), float(vl1[-1])
        cmf20 = float(self.cmf()[-1])
        obv_val = float(self.obv()[-1])
        force_val = float(self.force_index()[-1])
        rvol_val = float(self.rvol()[-1])

        # Pivots
        cpr_data = self.cpr()
        camarilla = self.camarilla_pivots()
        fib_pivots = self.fibonacci_pivots()

        # Candlestick Patterns
        patterns = self.candlestick_patterns()

        # ----------------- TALLY CONSENSUS SCORE -----------------
        bullish_votes = []
        bearish_votes = []
        neutral_votes = []

        def vote(name, condition_bullish, condition_bearish):
            if condition_bullish:
                bullish_votes.append(name)
            elif condition_bearish:
                bearish_votes.append(name)
            else:
                neutral_votes.append(name)

        # Votes on Trend
        vote("Price vs EMA20", price > ema20, price < ema20)
        vote("Price vs EMA50", price > ema50, price < ema50)
        vote("Price vs EMA200", price > ema200, price < ema200)
        vote("EMA 9/21 Cross", ema9 > ema20, ema9 < ema20)
        vote("MACD Crossover", macd_l > macd_s and macd_h > 0, macd_l < macd_s and macd_h < 0)
        vote("SuperTrend", supertrend_bullish, not supertrend_bullish)
        vote("ADX Trend", (adx_cur > 20 and plus_di > minus_di), (adx_cur > 20 and minus_di > plus_di))
        vote("Parabolic SAR", psar_bullish, not psar_bullish)
        vote("Ichimoku Cloud", price > ich_span_a and price > ich_span_b, price < ich_span_a and price < ich_span_b)
        vote("Aroon", aroon_osc > 20, aroon_osc < -20)
        vote("HMA20", price > hma20, price < hma20)

        # Votes on Momentum
        vote("RSI 14", (50 < rsi14 < 70) or rsi14 < 30, (30 <= rsi14 < 50) or rsi14 > 70)
        vote("Stochastic %K/%D", (k_val > d_val and k_val < 80), (k_val < d_val and k_val > 20))
        vote("StochRSI", (srsi_k > srsi_d and srsi_k < 80), (srsi_k < srsi_d and srsi_k > 20))
        vote("Williams %R", (-80 < williams < -20), (williams < -80 or williams > -20))
        vote("CCI 20", cci_val > 50, cci_val < -50)
        vote("ROC 14", roc14 > 0.5, roc14 < -0.5)
        vote("Awesome Osc", ao_val > 0, ao_val < 0)
        vote("MFI 14", (50 < mfi14 < 80), (20 < mfi14 <= 50))
        vote("TSI", tsi_val > 0, tsi_val < 0)
        vote("CMO", cmo_val > 0, cmo_val < 0)

        # Votes on Volume & Volatility
        vote("VWAP", price > vwap_val, price < vwap_val)
        vote("CMF 20", cmf20 > 0.05, cmf20 < -0.05)
        vote("Bollinger Bands %B", 0.5 <= b_pct <= 1.0, 0.0 <= b_pct < 0.5)
        vote("Force Index", force_val > 0, force_val < 0)
        vote("RVOL Breakout", (rvol_val > 1.3 and price > self.open[-1]), (rvol_val > 1.3 and price < self.open[-1]))

        # Votes on Pivots
        vote("CPR Status", price > cpr_data["tc"], price < cpr_data["bc"])
        vote("Camarilla H3/L3", price > camarilla["h3"], price < camarilla["l3"])

        # Candlestick pattern votes
        if patterns.get("bullish_engulfing") or patterns.get("morning_star") or patterns.get("bullish_marubozu") or patterns.get("hammer"):
            bullish_votes.append("Bullish Candlestick Pattern")
        elif patterns.get("bearish_engulfing") or patterns.get("evening_star") or patterns.get("bearish_marubozu") or patterns.get("shooting_star"):
            bearish_votes.append("Bearish Candlestick Pattern")

        total_voters = len(bullish_votes) + len(bearish_votes) + len(neutral_votes)
        bullish_pct = (len(bullish_votes) / total_voters) * 100.0 if total_voters > 0 else 50.0

        if bullish_pct >= 70:
            consensus_verdict = "STRONG BUY"
        elif bullish_pct >= 55:
            consensus_verdict = "BUY"
        elif bullish_pct <= 30:
            consensus_verdict = "STRONG SELL"
        elif bullish_pct <= 45:
            consensus_verdict = "SELL"
        else:
            consensus_verdict = "NEUTRAL"

        return {
            "current_price": price,
            "volume": vol,
            "consensus": {
                "verdict": consensus_verdict,
                "bullish_pct": round(bullish_pct, 1),
                "bullish_count": len(bullish_votes),
                "bearish_count": len(bearish_votes),
                "neutral_count": len(neutral_votes),
                "total_indicators": total_voters,
                "bullish_signals": bullish_votes,
                "bearish_signals": bearish_votes,
            },
            "trend": {
                "supertrend": {"value": round(supertrend_val, 2), "trend": "BULLISH" if supertrend_bullish else "BEARISH"},
                "macd": {"line": round(macd_l, 2), "signal": round(macd_s, 2), "hist": round(macd_h, 2)},
                "adx": {"adx": round(adx_cur, 2), "+di": round(plus_di, 2), "-di": round(minus_di, 2)},
                "moving_averages": {
                    "ema9": round(ema9, 2), "ema20": round(ema20, 2), "ema50": round(ema50, 2), "ema200": round(ema200, 2),
                    "sma20": round(sma20, 2), "sma50": round(sma50, 2), "sma200": round(sma200, 2),
                    "hma20": round(hma20, 2), "dema20": round(dema20, 2), "tema20": round(tema20, 2), "vwma20": round(vwma20, 2),
                },
                "parabolic_sar": {"value": round(psar_val, 2), "trend": "BULLISH" if psar_bullish else "BEARISH"},
                "ichimoku": {
                    "tenkan": round(ich_tenkan, 2), "kijun": round(ich_kijun, 2),
                    "senkou_a": round(ich_span_a, 2), "senkou_b": round(ich_span_b, 2),
                },
                "aroon": {"up": round(aroon_up, 1), "down": round(aroon_dn, 1), "oscillator": round(aroon_osc, 1)},
            },
            "momentum": {
                "rsi14": round(rsi14, 2),
                "rsi9": round(rsi9, 2),
                "stochastic": {"k": round(k_val, 2), "d": round(d_val, 2)},
                "stoch_rsi": {"k": round(srsi_k, 2), "d": round(srsi_d, 2)},
                "williams_r": round(williams, 2),
                "cci": round(cci_val, 2),
                "roc14": round(roc14, 2),
                "mfi14": round(mfi14, 2),
                "awesome_osc": round(ao_val, 2),
                "accelerator_osc": round(ac_val, 2),
                "tsi": round(tsi_val, 2),
                "cmo": round(cmo_val, 2),
            },
            "volatility": {
                "atr14": round(atr14, 2),
                "natr14": round(natr14, 2),
                "bollinger": {
                    "upper": round(b_up, 2), "mid": round(b_mid, 2), "lower": round(b_low, 2),
                    "bandwidth_pct": round(b_width, 2), "pct_b": round(b_pct, 3),
                },
                "keltner": {"upper": round(k_up, 2), "mid": round(k_mid, 2), "lower": round(k_low, 2)},
                "donchian": {"upper": round(d_up, 2), "mid": round(d_mid, 2), "lower": round(d_low, 2)},
                "historical_volatility_pct": round(hv20, 2),
            },
            "volume": {
                "vwap": round(vwap_val, 2),
                "vwap_upper_1": round(vwap_u1, 2),
                "vwap_lower_1": round(vwap_l1, 2),
                "cmf20": round(cmf20, 3),
                "obv": int(obv_val),
                "rvol": round(rvol_val, 2),
                "force_index": round(force_val, 2),
            },
            "pivots": {
                "cpr": {
                    "pivot": round(cpr_data["pivot"], 2),
                    "tc": round(cpr_data["tc"], 2),
                    "bc": round(cpr_data["bc"], 2),
                    "width_pct": round(cpr_data["width_pct"], 3),
                    "is_narrow": cpr_data["is_narrow"],
                    "r1": round(cpr_data["r1"], 2), "r2": round(cpr_data["r2"], 2), "r3": round(cpr_data["r3"], 2),
                    "s1": round(cpr_data["s1"], 2), "s2": round(cpr_data["s2"], 2), "s3": round(cpr_data["s3"], 2),
                },
                "camarilla": {k: round(v, 2) for k, v in camarilla.items()},
                "fibonacci": {k: round(v, 2) for k, v in fib_pivots.items()},
            },
            "candlestick_patterns": {k: v for k, v in patterns.items() if v},
        }


def format_indicators_terminal(symbol: str, res: dict):
    """Render a clean, structured terminal report of all indicators."""
    c = res["consensus"]
    price_str = format_inr(res["current_price"])
    print("=" * 76)
    print(f" TECHNICAL INDICATOR DASHBOARD: {symbol.upper()} | LTP: {price_str}")
    print("=" * 76)
    
    # Consensus Banner
    v_color = "\033[92m" if "BUY" in c["verdict"] else ("\033[91m" if "SELL" in c["verdict"] else "\033[93m")
    reset = "\033[0m"
    print(f" Overall Technical Verdict: {v_color}{c['verdict']}{reset} ({c['bullish_pct']}% Bullish Confluence)")
    print(f" Indicator Consensus: {c['bullish_count']} Bullish | {c['bearish_count']} Bearish | {c['neutral_count']} Neutral (Total: {c['total_indicators']})")
    print("-" * 76)

    # Key Levels & Trend
    tr = res["trend"]
    m = res["momentum"]
    v = res["volume"]
    p = res["pivots"]["cpr"]
    cam = res["pivots"]["camarilla"]

    print(" 1. TREND & MOVING AVERAGES:")
    print(f"    SuperTrend:     {format_inr(tr['supertrend']['value'])} [{tr['supertrend']['trend']}]")
    print(f"    MACD Line:      {tr['macd']['line']:+.2f} | Signal: {tr['macd']['signal']:+.2f} | Hist: {tr['macd']['hist']:+.2f}")
    print(f"    ADX Trend:      {tr['adx']['adx']:.1f} (+DI: {tr['adx']['+di']:.1f}, -DI: {tr['adx']['-di']:.1f})")
    print(f"    Parabolic SAR:  {format_inr(tr['parabolic_sar']['value'])} [{tr['parabolic_sar']['trend']}]")
    print(f"    EMA 9/20/50:    {format_inr(tr['moving_averages']['ema9'])} / {format_inr(tr['moving_averages']['ema20'])} / {format_inr(tr['moving_averages']['ema50'])}")
    print(f"    EMA 200:        {format_inr(tr['moving_averages']['ema200'])} | SMA 200: {format_inr(tr['moving_averages']['sma200'])}")
    print(f"    Ichimoku Cloud: Tenkan {format_inr(tr['ichimoku']['tenkan'])}, Kijun {format_inr(tr['ichimoku']['kijun'])}, Span A {format_inr(tr['ichimoku']['senkou_a'])}")
    print("-" * 76)

    print(" 2. MOMENTUM & OSCILLATORS:")
    print(f"    RSI 14 / RSI 9: {m['rsi14']:.1f} / {m['rsi9']:.1f}")
    print(f"    Stochastic %K/%D: {m['stochastic']['k']:.1f} / {m['stochastic']['d']:.1f} | StochRSI: {m['stoch_rsi']['k']:.1f}")
    print(f"    Williams %R:    {m['williams_r']:.1f} | CCI 20: {m['cci']:+.1f}")
    print(f"    Money Flow MFI: {m['mfi14']:.1f} | ROC 14: {m['roc14']:+.2f}%")
    print(f"    Awesome Osc:    {m['awesome_osc']:+.2f} | TSI: {m['tsi']:+.2f}")
    print("-" * 76)

    print(" 3. VOLATILITY & VOLUME:")
    vol_section = res["volatility"]
    print(f"    VWAP (Intraday):{format_inr(v['vwap'])} (Upper 1σ: {format_inr(v['vwap_upper_1'])}, Lower: {format_inr(v['vwap_lower_1'])})")
    print(f"    RVOL (vs 20d):  {v['rvol']:.2f}x | CMF 20: {v['cmf20']:+.3f}")
    print(f"    ATR 14:         {format_inr(vol_section['atr14'])} (NATR: {vol_section['natr14']:.2f}%)")
    print(f"    Bollinger Bands:{format_inr(vol_section['bollinger']['mid'])} [L: {format_inr(vol_section['bollinger']['lower'])} - U: {format_inr(vol_section['bollinger']['upper'])}] %B: {vol_section['bollinger']['pct_b']:.2f}")
    print("-" * 76)

    print(" 4. INTRADAY PIVOTS & CPR (INDIAN MARKET SPECIAL):")
    cpr_type = "NARROW (Trending Potential)" if p['is_narrow'] else "WIDE (Sideways / Mean Reversion)"
    print(f"    CPR Range:      Pivot {format_inr(p['pivot'])} | TC: {format_inr(p['tc'])} | BC: {format_inr(p['bc'])}")
    print(f"    CPR Width:      {p['width_pct']:.3f}% -> {cpr_type}")
    print(f"    CPR Levels:     R1 {format_inr(p['r1'])}, R2 {format_inr(p['r2'])}, S1 {format_inr(p['s1'])}, S2 {format_inr(p['s2'])}")
    print(f"    Camarilla H4/L4:Breakout Long: {format_inr(cam['h4'])} | Breakdown Short: {format_inr(cam['l4'])}")
    print(f"    Camarilla H3/L3:Sell Zone: {format_inr(cam['h3'])} | Buy Zone: {format_inr(cam['l3'])}")
    print("-" * 76)

    active_patterns = list(res["candlestick_patterns"].keys())
    pattern_str = ", ".join(k.replace("_", " ").title() for k in active_patterns) if active_patterns else "None detected"
    print(f" 5. CANDLESTICK PATTERNS: {pattern_str}")
    print("=" * 76)


def main():
    parser = argparse.ArgumentParser(description="Technical Indicators Engine for Indian Stocks")
    parser.add_argument("symbol", nargs="?", default="RELIANCE.NS", help="NSE stock symbol (e.g. RELIANCE.NS, TCS, HDFCBANK)")
    parser.add_argument("--interval", default="15m", help="Candle interval (1m, 3m, 5m, 15m, 1d; default: 15m)")
    parser.add_argument("--period", default="5d", help="Data period (1d, 5d, 1mo, 3mo; default: 5d)")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    parser.add_argument("--offline", help="Path to offline price bars JSON")
    args = parser.parse_args()

    symbol = clean_symbol(args.symbol)
    try:
        df = fetch_bars(symbol, period=args.period, interval=args.interval, offline_file=args.offline)
        engine = TechnicalIndicators(df)
        results = engine.compute_all()

        if args.json:
            print(json.dumps(results, indent=2))
        else:
            format_indicators_terminal(symbol, results)
        sys.exit(0)
    except Exception as e:
        print(f"Error computing indicators for {symbol}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
