"""Configuration loading from YAML + environment.

API credentials come from environment variables (never the YAML file, so secrets
don't get committed). Everything else -- exchange, symbols, strategy, risk --
lives in a versioned config file. See ``config.example.yaml``.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .risk import RiskConfig


@dataclass
class AppConfig:
    mode: str = "paper"            # "backtest" | "paper" | "live"
    exchange: str = "binance"      # any ccxt exchange id
    symbols: list[str] = field(default_factory=lambda: ["BTC/USDT", "ETH/USDT"])
    strategy_name: str = "trend_momentum"
    strategy_params: dict = field(default_factory=dict)
    risk: RiskConfig = field(default_factory=RiskConfig)
    timeframe: str = "1h"          # ccxt timeframe: 1m,5m,15m,1h,4h,1d
    lookback_bars: int = 300
    poll_seconds: int = 60         # crypto is 24/7; loop interval
    initial_cash: float = 10_000.0
    #: Optional fixed capital for sizing (quote currency, e.g. USDT). Trade as if
    #: you only have this much regardless of real balance.
    capital_base: float | None = None

    # Credentials, populated from the environment.
    api_key: str | None = None
    api_secret: str | None = None

    def __post_init__(self):
        if self.mode not in ("backtest", "paper", "live"):
            raise ValueError(f"invalid mode {self.mode!r}")
        # Accept exchange-specific or generic env vars.
        self.api_key = self.api_key or os.getenv("CRYPTO_API_KEY") or os.getenv("BINANCE_API_KEY")
        self.api_secret = self.api_secret or os.getenv("CRYPTO_API_SECRET") or os.getenv("BINANCE_API_SECRET")

    @property
    def sandbox(self) -> bool:
        """True (testnet/paper) unless live trading is explicitly selected."""
        return self.mode != "live"


def load_config(path: str | Path) -> AppConfig:
    """Load an :class:`AppConfig` from a YAML file."""
    import yaml

    with open(path) as fh:
        raw = yaml.safe_load(fh) or {}

    strat = raw.get("strategy", {}) or {}
    risk_raw = raw.get("risk", {}) or {}
    data_raw = raw.get("data", {}) or {}

    return AppConfig(
        mode=raw.get("mode", "paper"),
        exchange=raw.get("exchange", "binance"),
        symbols=raw.get("symbols", ["BTC/USDT", "ETH/USDT"]),
        strategy_name=strat.get("name", "trend_momentum"),
        strategy_params=strat.get("params", {}) or {},
        risk=RiskConfig(**risk_raw),
        timeframe=data_raw.get("timeframe", "1h"),
        lookback_bars=int(data_raw.get("lookback_bars", 300)),
        poll_seconds=int(raw.get("poll_seconds", 60)),
        initial_cash=float(raw.get("initial_cash", 10_000.0)),
        capital_base=(
            float(raw["capital_base"]) if raw.get("capital_base") is not None else None
        ),
    )
