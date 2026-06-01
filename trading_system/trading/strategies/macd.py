"""MACD momentum strategy.

Long while the MACD line is above its signal line, flat otherwise.
"""
from __future__ import annotations

import pandas as pd

from ..utils import indicators
from .base import Signal, Strategy


class MacdStrategy(Strategy):
    name = "macd"

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__(fast=fast, slow=slow, signal=signal)
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        m = indicators.macd(data["close"], self.fast, self.slow, self.signal)
        signals = pd.Series(Signal.HOLD, index=data.index, dtype=int)
        signals[m["macd"] > m["signal"]] = Signal.BUY
        signals[m["macd"] <= m["signal"]] = Signal.SELL
        signals[m["macd"].isna() | m["signal"].isna()] = Signal.HOLD
        return signals
