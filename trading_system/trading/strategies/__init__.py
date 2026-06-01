"""Strategy package + registry.

The registry lets config/CLI refer to strategies by name (e.g. ``"sma_crossover"``)
and pass parameters as a dict, so adding a new strategy is just one entry here.
"""
from __future__ import annotations

from .base import Signal, Strategy
from .bollinger import BollingerReversion
from .macd import MacdStrategy
from .rsi_reversion import RsiReversion
from .sma_crossover import SmaCrossover

_REGISTRY: dict[str, type[Strategy]] = {
    SmaCrossover.name: SmaCrossover,
    RsiReversion.name: RsiReversion,
    BollingerReversion.name: BollingerReversion,
    MacdStrategy.name: MacdStrategy,
}


def available() -> list[str]:
    """Names of all registered strategies."""
    return sorted(_REGISTRY)


def create(name: str, **params) -> Strategy:
    """Instantiate a strategy by registry name."""
    try:
        cls = _REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"unknown strategy {name!r}; available: {', '.join(available())}"
        ) from None
    return cls(**params)


__all__ = [
    "Signal",
    "Strategy",
    "SmaCrossover",
    "RsiReversion",
    "BollingerReversion",
    "MacdStrategy",
    "available",
    "create",
]
