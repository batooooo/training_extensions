"""A modular stock auto-trading system (Alpaca-backed).

Layers:
  * ``strategies`` -- pluggable signal generators (SMA / RSI / Bollinger / MACD).
  * ``broker``     -- broker abstraction + Alpaca adapter + a simulated broker.
  * ``data``       -- historical/live OHLCV access.
  * ``risk``       -- sizing, stops, daily-loss kill switch.
  * ``engine``     -- backtester and live engine (share strategy + risk logic).

Default mode is paper trading; live trading must be enabled explicitly.
"""
from . import broker, data, engine, risk, strategies, utils
from .config import AppConfig, load_config

__version__ = "0.1.0"

__all__ = [
    "broker",
    "data",
    "engine",
    "risk",
    "strategies",
    "utils",
    "AppConfig",
    "load_config",
]
