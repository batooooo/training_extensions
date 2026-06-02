"""Strategy interface shared by the backtester and the live engine.

A strategy is a pure function of market data: given a price history DataFrame it
emits a target *signal* per bar. It never talks to the broker directly -- the
engine is responsible for turning signals into orders and applying risk rules.
This keeps strategies trivially unit-testable and backtestable.
"""
from __future__ import annotations

import enum
from abc import ABC, abstractmethod

import pandas as pd


class Signal(enum.IntEnum):
    """Target stance for a symbol on a given bar."""

    SELL = -1   # exit / go flat (no shorting in the default engine)
    HOLD = 0
    BUY = 1     # enter / stay long


class Strategy(ABC):
    """Base class for all trading strategies.

    Subclasses implement :meth:`generate_signals`, which receives a DataFrame
    indexed by timestamp with at least a ``close`` column (``open/high/low/
    volume`` may also be present) and returns a Series of :class:`Signal`
    values aligned to the same index.
    """

    #: Human-readable name; defaults to the class name.
    name: str = "strategy"

    def __init__(self, **params):
        self.params = params
        if not getattr(self, "name", None) or self.name == "strategy":
            self.name = self.__class__.__name__

    @abstractmethod
    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        """Return a Signal Series aligned to ``data.index``."""

    def latest_signal(self, data: pd.DataFrame) -> Signal:
        """Convenience: the signal for the most recent bar.

        Used by the live engine, which only cares about *now*.
        """
        signals = self.generate_signals(data)
        if signals.empty:
            return Signal.HOLD
        return Signal(int(signals.iloc[-1]))

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"{self.__class__.__name__}({self.params})"
