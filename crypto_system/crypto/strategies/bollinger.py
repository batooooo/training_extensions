"""Bollinger Band mean-reversion strategy.

Buy when price closes below the lower band (stretched cheap) and exit when it
returns to / exceeds the middle or upper band.
"""
from __future__ import annotations

import pandas as pd

from ..utils import indicators
from .base import Signal, Strategy


class BollingerReversion(Strategy):
    name = "bollinger"

    def __init__(self, window: int = 20, num_std: float = 2.0):
        super().__init__(window=window, num_std=num_std)
        self.window = window
        self.num_std = num_std

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        bands = indicators.bollinger_bands(close, self.window, self.num_std)
        signals = pd.Series(Signal.HOLD, index=data.index, dtype=int)
        signals[close < bands["lower"]] = Signal.BUY
        signals[close > bands["upper"]] = Signal.SELL
        signals[bands["middle"].isna()] = Signal.HOLD
        return signals
