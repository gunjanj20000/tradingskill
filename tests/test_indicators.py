"""Unit tests for the Technical Indicator Engine."""

import unittest
import numpy as np
import pandas as pd

from trader_indicators.indicators import TechnicalIndicators


class TestTechnicalIndicators(unittest.TestCase):

    def setUp(self):
        # Create deterministic synthetic price data
        np.random.seed(42)
        n = 60
        base_price = 1000.0
        # Gentle upward trend with volatility
        prices = [base_price]
        for _ in range(n - 1):
            prices.append(prices[-1] + np.random.uniform(-5.0, 7.0))
        
        opens = np.array(prices)
        highs = opens + np.random.uniform(2.0, 10.0, size=n)
        lows = opens - np.random.uniform(2.0, 10.0, size=n)
        closes = lows + (highs - lows) * np.random.uniform(0.1, 0.9, size=n)
        volumes = np.random.uniform(10000, 50000, size=n)

        dt_index = pd.date_range("2026-10-19 09:15", periods=n, freq="15min")
        self.df = pd.DataFrame({
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes,
        }, index=dt_index)
        self.ti = TechnicalIndicators(self.df)

    def test_moving_averages(self):
        sma20 = self.ti.sma(20)
        ema20 = self.ti.ema(20)
        wma20 = self.ti.wma(20)
        hma20 = self.ti.hma(20)
        dema20 = self.ti.dema(20)
        tema20 = self.ti.tema(20)
        vwma20 = self.ti.vwma(20)

        self.assertEqual(len(sma20), len(self.df))
        self.assertEqual(len(ema20), len(self.df))
        self.assertGreater(sma20[-1], 0)
        self.assertGreater(ema20[-1], 0)
        self.assertGreater(wma20[-1], 0)
        self.assertGreater(hma20[-1], 0)
        self.assertGreater(dema20[-1], 0)
        self.assertGreater(tema20[-1], 0)
        self.assertGreater(vwma20[-1], 0)

    def test_macd(self):
        line, signal, hist = self.ti.macd(12, 26, 9)
        self.assertEqual(len(line), len(self.df))
        self.assertEqual(len(signal), len(self.df))
        # Histogram should equal line - signal
        np.testing.assert_almost_equal(hist, line - signal)

    def test_supertrend(self):
        st, direction, upper, lower = self.ti.supertrend(10, 3.0)
        self.assertEqual(len(st), len(self.df))
        self.assertTrue(all(d in [1, -1] for d in direction))

    def test_oscillators(self):
        rsi14 = self.ti.rsi(14)
        self.assertTrue(all(0.0 <= r <= 100.0 for r in rsi14))

        k, d = self.ti.stochastic(14, 3)
        self.assertTrue(all(0.0 <= val <= 100.0 for val in k))
        self.assertTrue(all(0.0 <= val <= 100.0 for val in d))

        williams = self.ti.williams_r(14)
        self.assertTrue(all(-100.0 <= w <= 0.0 for w in williams))

    def test_volatility(self):
        atr14 = self.ti.atr(14)
        self.assertTrue(all(a >= 0.0 for a in atr14))

        upper, mid, lower, bw, pct_b = self.ti.bollinger_bands(20, 2.0)
        self.assertTrue(all(upper[i] >= mid[i] >= lower[i] for i in range(20, len(self.df))))

    def test_cpr_and_camarilla(self):
        cpr = self.ti.cpr()
        self.assertIn("pivot", cpr)
        self.assertIn("tc", cpr)
        self.assertIn("bc", cpr)
        self.assertIn("width_pct", cpr)
        self.assertGreaterEqual(cpr["tc"], cpr["bc"])

        cam = self.ti.camarilla_pivots()
        self.assertIn("h4", cam)
        self.assertIn("l4", cam)
        self.assertGreater(cam["h4"], cam["h3"])
        self.assertLess(cam["l4"], cam["l3"])

    def test_compute_all(self):
        res = self.ti.compute_all()
        self.assertIn("consensus", res)
        self.assertIn("verdict", res["consensus"])
        self.assertIn(res["consensus"]["verdict"], ["STRONG BUY", "BUY", "NEUTRAL", "SELL", "STRONG SELL"])
        self.assertGreater(res["consensus"]["total_indicators"], 20)


if __name__ == "__main__":
    unittest.main()
