import numpy as np
import pandas as pd

from trading.utils import indicators


def test_sma_matches_manual():
    s = pd.Series([1, 2, 3, 4, 5], dtype=float)
    out = indicators.sma(s, 2)
    assert np.isnan(out.iloc[0])
    assert out.iloc[1] == 1.5
    assert out.iloc[-1] == 4.5


def test_rsi_bounds_and_uptrend():
    s = pd.Series(np.arange(1, 50, dtype=float))  # strictly increasing
    rsi = indicators.rsi(s, 14).dropna()
    assert (rsi >= 0).all() and (rsi <= 100).all()
    # An only-up series should saturate near 100.
    assert rsi.iloc[-1] > 95


def test_bollinger_band_ordering():
    rng = np.random.default_rng(1)
    s = pd.Series(100 + np.cumsum(rng.normal(0, 1, 100)))
    bands = indicators.bollinger_bands(s, 20, 2.0).dropna()
    assert (bands["upper"] >= bands["middle"]).all()
    assert (bands["middle"] >= bands["lower"]).all()


def test_macd_hist_is_diff():
    rng = np.random.default_rng(2)
    s = pd.Series(100 + np.cumsum(rng.normal(0, 1, 100)))
    m = indicators.macd(s)
    np.testing.assert_allclose(m["hist"], m["macd"] - m["signal"], rtol=1e-9)
