"""Configuration loading from YAML + environment.

API credentials come from environment variables (never the YAML file, so secrets
don't get committed). Everything else -- strategy, symbols, risk limits -- lives
in a versioned config file. See ``config.example.yaml``.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .risk import RiskConfig


@dataclass
class AppConfig:
    mode: str = "paper"            # "backtest" | "paper" | "live"
    symbols: list[str] = field(default_factory=lambda: ["AAPL"])
    strategy_name: str = "sma_crossover"
    strategy_params: dict = field(default_factory=dict)
    risk: RiskConfig = field(default_factory=RiskConfig)
    timeframe: str = "1Day"
    lookback_bars: int = 200
    poll_seconds: int = 60
    initial_cash: float = 100_000.0

    # Credentials, populated from the environment.
    api_key: str | None = None
    api_secret: str | None = None

    def __post_init__(self):
        if self.mode not in ("backtest", "paper", "live"):
            raise ValueError(f"invalid mode {self.mode!r}")
        self.api_key = self.api_key or os.getenv("ALPACA_API_KEY")
        self.api_secret = self.api_secret or os.getenv("ALPACA_API_SECRET")

    @property
    def paper(self) -> bool:
        """True for paper trading. Live trading must be opted into explicitly."""
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
        symbols=raw.get("symbols", ["AAPL"]),
        strategy_name=strat.get("name", "sma_crossover"),
        strategy_params=strat.get("params", {}) or {},
        risk=RiskConfig(**risk_raw),
        timeframe=data_raw.get("timeframe", "1Day"),
        lookback_bars=int(data_raw.get("lookback_bars", 200)),
        poll_seconds=int(raw.get("poll_seconds", 60)),
        initial_cash=float(raw.get("initial_cash", 100_000.0)),
    )
