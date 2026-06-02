"""Trend-Momentum -- a robust, multi-filter strategy.

This is not a single indicator but a *confluence* of principles that veteran
systematic/trend-following traders rely on. The edge comes less from any one
signal and more from (a) only trading with the primary trend, (b) requiring
momentum confirmation, (c) refusing to chase blow-off tops, and (d) exiting the
moment the trend structure breaks. Pair it with the volatility/stop controls in
the risk module.

Long entry requires ALL of:
  * regime filter : close > SMA(trend_window)        -> primary uptrend ("bull")
  * trend trigger : EMA(fast) > EMA(slow)            -> short-term trend is up
  * momentum      : close > close `mom_window` ago    -> medium-term momentum +ve
  * not overbought: RSI(rsi_window) < rsi_max         -> avoid buying euphoria

Exit (go flat) when EITHER:
  * close < SMA(trend_window)  (primary trend lost), OR
  * EMA(fast) < EMA(slow)      (short-term trend rolled over)

Defaults follow widely-used values (200-day regime, ~6-month momentum) rather
than numbers tuned to one dataset, to reduce overfitting.
"""
from __future__ import annotations

import pandas as pd

from ..utils import indicators
from .base import Signal, Strategy


class TrendMomentum(Strategy):
    name = "trend_momentum"

    def __init__(
        self,
        trend_window: int = 200,
        fast: int = 20,
        slow: int = 50,
        mom_window: int = 126,   # ~6 trading months
        rsi_window: int = 14,
        rsi_max: float = 80.0,
    ):
        if fast >= slow:
            raise ValueError("fast must be shorter than slow")
        super().__init__(
            trend_window=trend_window, fast=fast, slow=slow,
            mom_window=mom_window, rsi_window=rsi_window, rsi_max=rsi_max,
        )
        self.trend_window = trend_window
        self.fast = fast
        self.slow = slow
        self.mom_window = mom_window
        self.rsi_window = rsi_window
        self.rsi_max = rsi_max

    def generate_signals(self, data: pd.DataFrame) -> pd.Series:
        close = data["close"]
        trend_ma = indicators.sma(close, self.trend_window)
        ema_fast = indicators.ema(close, self.fast)
        ema_slow = indicators.ema(close, self.slow)
        momentum = close - close.shift(self.mom_window)
        rsi = indicators.rsi(close, self.rsi_window)

        in_uptrend = close > trend_ma
        trend_up = ema_fast > ema_slow

        long_entry = in_uptrend & trend_up & (momentum > 0) & (rsi < self.rsi_max)
        exit_signal = (~in_uptrend) | (~trend_up)

        signals = pd.Series(Signal.HOLD, index=data.index, dtype=int)
        signals[long_entry] = Signal.BUY
        signals[exit_signal] = Signal.SELL
        # While invariants are not yet computable, stay flat.
        warmup = trend_ma.isna() | ema_slow.isna() | momentum.isna() | rsi.isna()
        signals[warmup] = Signal.HOLD
        return signals
