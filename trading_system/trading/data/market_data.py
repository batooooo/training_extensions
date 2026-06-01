"""Market data access.

Two sources:
  * CSV files -- offline, deterministic, used by the backtester and tests.
  * Alpaca historical bars -- for fetching real OHLCV to backtest on or to feed
    the live engine.

Both return a tidy OHLCV DataFrame indexed by timestamp with lowercase columns:
``open, high, low, close, volume``.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

OHLCV_COLUMNS = ["open", "high", "low", "close", "volume"]


def _normalize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={c: c.lower() for c in df.columns})
    missing = [c for c in OHLCV_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"data is missing required columns: {missing}")
    df = df.sort_index()
    return df[OHLCV_COLUMNS]


def load_csv(path: str | Path, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """Load OHLCV from a CSV file with a timestamp column."""
    df = pd.read_csv(path)
    df = df.rename(columns={c: c.lower() for c in df.columns})
    ts = timestamp_col.lower()
    if ts not in df.columns:
        # fall back to common alternatives
        for alt in ("date", "time", "datetime"):
            if alt in df.columns:
                ts = alt
                break
    df[ts] = pd.to_datetime(df[ts])
    df = df.set_index(ts)
    df.index.name = "timestamp"
    return _normalize(df)


def fetch_alpaca_bars(
    symbol: str,
    start: str,
    end: str | None = None,
    timeframe: str = "1Day",
    api_key: str | None = None,
    api_secret: str | None = None,
) -> pd.DataFrame:
    """Fetch historical bars from Alpaca.

    ``timeframe`` is one of ``"1Min", "5Min", "15Min", "1Hour", "1Day"``.
    Credentials fall back to ALPACA_API_KEY / ALPACA_API_SECRET env vars.
    """
    import os

    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

    api_key = api_key or os.getenv("ALPACA_API_KEY")
    api_secret = api_secret or os.getenv("ALPACA_API_SECRET")
    if not api_key or not api_secret:
        raise ValueError("Alpaca credentials required (args or env vars)")

    tf_map = {
        "1Min": TimeFrame(1, TimeFrameUnit.Minute),
        "5Min": TimeFrame(5, TimeFrameUnit.Minute),
        "15Min": TimeFrame(15, TimeFrameUnit.Minute),
        "1Hour": TimeFrame(1, TimeFrameUnit.Hour),
        "1Day": TimeFrame(1, TimeFrameUnit.Day),
    }
    if timeframe not in tf_map:
        raise ValueError(f"unsupported timeframe {timeframe!r}; pick from {list(tf_map)}")

    client = StockHistoricalDataClient(api_key, api_secret)
    req = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=tf_map[timeframe],
        start=pd.Timestamp(start),
        end=pd.Timestamp(end) if end else None,
    )
    bars = client.get_stock_bars(req).df
    if bars.empty:
        raise ValueError(f"no bars returned for {symbol}")
    # Alpaca returns a MultiIndex (symbol, timestamp) for multi-symbol requests.
    if isinstance(bars.index, pd.MultiIndex):
        bars = bars.xs(symbol, level="symbol")
    bars.index.name = "timestamp"
    return _normalize(bars)
