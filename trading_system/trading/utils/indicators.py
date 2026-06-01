"""Technical indicators implemented on top of pandas.

All functions take a price Series (or DataFrame) and return Series aligned to the
input index. They are intentionally dependency-light (pandas/numpy only) so the
same code runs in the backtester and in the live engine.
"""
from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    """Simple moving average."""
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=window, adjust=False).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """Relative Strength Index (Wilder's smoothing)."""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, pd.NA)
    out = 100.0 - (100.0 / (1.0 + rs))
    # When avg_loss == 0 the asset only went up -> RSI saturates at 100.
    out = out.where(avg_loss != 0.0, 100.0)
    return out


def bollinger_bands(
    series: pd.Series, window: int = 20, num_std: float = 2.0
) -> pd.DataFrame:
    """Returns DataFrame with columns: middle, upper, lower."""
    middle = sma(series, window)
    std = series.rolling(window=window, min_periods=window).std()
    upper = middle + num_std * std
    lower = middle - num_std * std
    return pd.DataFrame({"middle": middle, "upper": upper, "lower": lower})


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> pd.DataFrame:
    """Returns DataFrame with columns: macd, signal, hist."""
    macd_line = ema(series, fast) - ema(series, slow)
    signal_line = ema(macd_line, signal)
    hist = macd_line - signal_line
    return pd.DataFrame({"macd": macd_line, "signal": signal_line, "hist": hist})


def atr(high: pd.Series, low: pd.Series, close: pd.Series, window: int = 14) -> pd.Series:
    """Average True Range -- useful for volatility-based stops/sizing."""
    prev_close = close.shift(1)
    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
