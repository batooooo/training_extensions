"""Market data access for crypto (ccxt) + CSV.

Returns a tidy OHLCV DataFrame indexed by timestamp with lowercase columns:
``open, high, low, close, volume`` -- identical shape to the stock system, so the
same indicators/strategies/backtester work unchanged.
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
    return df.sort_index()[OHLCV_COLUMNS]


def load_csv(path: str | Path, timestamp_col: str = "timestamp") -> pd.DataFrame:
    """Load OHLCV from a CSV file with a timestamp column."""
    df = pd.read_csv(path)
    df = df.rename(columns={c: c.lower() for c in df.columns})
    ts = timestamp_col.lower()
    if ts not in df.columns:
        for alt in ("date", "time", "datetime"):
            if alt in df.columns:
                ts = alt
                break
    df[ts] = pd.to_datetime(df[ts])
    df = df.set_index(ts)
    df.index.name = "timestamp"
    return _normalize(df)


def fetch_ccxt_ohlcv(
    symbol: str,
    timeframe: str = "1h",
    limit: int = 500,
    exchange: str = "binance",
    api_key: str | None = None,
    api_secret: str | None = None,
    sandbox: bool = False,
) -> pd.DataFrame:
    """Fetch recent OHLCV candles via ccxt.

    ``symbol`` like ``"BTC/USDT"``; ``timeframe`` like ``"1m","5m","1h","1d"``.
    Public market data needs no API key. Returns the most recent ``limit`` bars.
    """
    import ccxt

    if not hasattr(ccxt, exchange):
        raise ValueError(f"unknown ccxt exchange: {exchange!r}")
    ex = getattr(ccxt, exchange)(
        {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}
    )
    if sandbox:
        ex.set_sandbox_mode(True)
    raw = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    if not raw:
        raise ValueError(f"no candles returned for {symbol}")
    df = pd.DataFrame(raw, columns=["ts", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["ts"], unit="ms")
    df = df.set_index("timestamp").drop(columns="ts")
    return _normalize(df)
