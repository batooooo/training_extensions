"""A modular stock auto-trading system (Alpaca-backed).

Layers:
  * ``strategies`` -- pluggable signal generators (SMA / RSI / Bollinger / MACD).
  * ``broker``     -- broker abstraction + Alpaca adapter + a simulated broker.
  * ``data``       -- historical/live OHLCV access.
  * ``risk``       -- sizing, stops, daily-loss kill switch.
  * ``engine``     -- backtester and live engine (share strategy + risk logic).

Default mode is paper trading; live trading must be enabled explicitly.
"""
from . import broker, data, engine, notify, risk, strategies, utils
from .config import AppConfig, load_config
from .portfolio import PortfolioManager, plan_rebalance

__version__ = "0.1.0"

__all__ = [
    "broker",
    "data",
    "engine",
    "risk",
    "strategies",
    "notify",
    "utils",
    "AppConfig",
    "load_config",
    "PortfolioManager",
    "plan_rebalance",
]
