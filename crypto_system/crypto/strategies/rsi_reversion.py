"""RSI mean-reversion strategy.

Buy when RSI drops below ``oversold`` (price likely over-sold) and exit when it
climbs back above ``overbought``. Profits from snap-backs; dangerous in strong
downtrends, where RSI can stay oversold for a long time.
"""
from __future__ import annotations

import pandas as pd

from ..utils import indicators
from .base import Signal, Strategy


class RsiReversion(Strategy):
    name = "rsi_reversion"

    def __init__(self, window: int = 14, oversold: float = 30.0, overbought: float = 70.0):
        if not 0 < oversold < overbought < 100:
            raise ValueError("require 0 < oversold < overbought < 100")
        super().__init__(window=window, oversold=oversold, overbought=overbought)
        self.window = window
        self.oversold = oversold
        self.overbought = overbought

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        rsi = indicators.rsi(data["close"], self.window)
        signals = pd.Series(Signal.HOLD, index=data.index, dtype=int)
        signals[rsi < self.oversold] = Signal.BUY
        signals[rsi > self.overbought] = Signal.SELL
        signals[rsi.isna()] = Signal.HOLD
        return signals
