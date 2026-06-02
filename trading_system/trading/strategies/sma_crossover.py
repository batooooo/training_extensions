"""SMA crossover -- a trend-following strategy.

Buy when the fast SMA crosses above the slow SMA (golden cross) and exit when it
crosses back below (dead cross). Works best in trending markets; whipsaws in
sideways markets, which is exactly what the backtester will reveal.
"""
from __future__ import annotations

import pandas as pd

from ..utils import indicators
from .base import Signal, Strategy


class SmaCrossover(Strategy):
    name = "sma_crossover"

    def __init__(self, fast: int = 20, slow: int = 50):
        if fast >= slow:
            raise ValueError("fast window must be shorter than slow window")
        super().__init__(fast=fast, slow=slow)
        self.fast = fast
        self.slow = slow

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        fast_ma = indicators.sma(close, self.fast)
        slow_ma = indicators.sma(close, self.slow)

        signals = pd.Series(Signal.HOLD, index=data.index, dtype=int)
        # Long while fast above slow, flat otherwise. The engine de-dupes
        # repeated signals into a single position change.
        signals[fast_ma > slow_ma] = Signal.BUY
        signals[fast_ma <= slow_ma] = Signal.SELL
        signals[fast_ma.isna() | slow_ma.isna()] = Signal.HOLD
        return signals
