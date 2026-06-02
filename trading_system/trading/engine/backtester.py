"""Event-driven backtester for a single symbol.

Runs a strategy over historical OHLCV bar-by-bar, applying the same risk rules
(stop-loss / take-profit / position sizing) the live engine uses, then reports
performance metrics. To avoid look-ahead bias, the signal generated from bars
``[0..i]`` is acted on at the *next* bar's price.

Fills include a configurable commission and slippage so results are not
unrealistically optimistic.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from ..risk import RiskConfig, RiskManager
from ..strategies import Signal, Strategy
from ..utils import indicators


@dataclass
class Trade:
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp
    exit_price: float
    qty: float
    reason: str  # "signal" | "stop_loss" | "take_profit"

    @property
    def pnl(self) -> float:
        return (self.exit_price - self.entry_price) * self.qty

    @property
    def return_pct(self) -> float:
        return (self.exit_price / self.entry_price) - 1.0


@dataclass
class BacktestResult:
    equity_curve: pd.Series
    trades: list[Trade] = field(default_factory=list)
    initial_cash: float = 0.0

    @property
    def final_equity(self) -> float:
        return float(self.equity_curve.iloc[-1]) if len(self.equity_curve) else self.initial_cash

    def metrics(self) -> dict[str, float]:
        eq = self.equity_curve
        if len(eq) < 2:
            return {"total_return": 0.0, "sharpe": 0.0, "max_drawdown": 0.0,
                    "num_trades": len(self.trades), "win_rate": 0.0}
        rets = eq.pct_change().dropna()
        total_return = eq.iloc[-1] / eq.iloc[0] - 1.0
        sharpe = 0.0
        if rets.std() > 0:
            sharpe = float(np.sqrt(252) * rets.mean() / rets.std())
        running_max = eq.cummax()
        max_dd = float(((eq - running_max) / running_max).min())
        wins = [t for t in self.trades if t.pnl > 0]
        win_rate = len(wins) / len(self.trades) if self.trades else 0.0
        return {
            "total_return": float(total_return),
            "sharpe": sharpe,
            "max_drawdown": max_dd,
            "num_trades": len(self.trades),
            "win_rate": float(win_rate),
        }


class Backtester:
    def __init__(
        self,
        strategy: Strategy,
        initial_cash: float = 100_000.0,
        risk_config: RiskConfig | None = None,
        commission: float = 0.0,
        slippage_pct: float = 0.0005,
    ):
        self.strategy = strategy
        self.initial_cash = initial_cash
        self.risk = RiskManager(risk_config)
        self.commission = commission
        self.slippage_pct = slippage_pct

    def run(self, data: pd.DataFrame) -> BacktestResult:
        signals = self.strategy.generate_signals(data).shift(1).fillna(Signal.HOLD)
        close = data["close"]
        # Pre-compute ATR (shifted to avoid look-ahead) for volatility sizing.
        if {"high", "low"}.issubset(data.columns):
            atr_series = indicators.atr(data["high"], data["low"], close).shift(1)
        else:
            atr_series = pd.Series(index=data.index, dtype=float)

        cash = self.initial_cash
        qty = 0.0
        entry_price = 0.0
        entry_time = None
        trades: list[Trade] = []
        equity_points: list[float] = []

        self.risk.start_day(cash)

        for ts, price in close.items():
            sig = Signal(int(signals.loc[ts]))

            # --- exits first: stop-loss / take-profit then strategy SELL ---
            if qty > 0:
                reason = self.risk.should_exit(entry_price, price)
                if reason is None and sig is Signal.SELL:
                    reason = "signal"
                if reason is not None:
                    fill = price * (1 - self.slippage_pct)
                    cash += qty * fill - self.commission
                    trades.append(
                        Trade(entry_time, entry_price, ts, fill, qty, reason)
                    )
                    qty = 0.0
                    entry_price = 0.0

            # --- entries ---
            equity = cash + qty * price
            if qty == 0 and sig is Signal.BUY and self.risk.check_daily_loss(equity):
                fill = price * (1 + self.slippage_pct)
                atr_val = atr_series.get(ts)
                if atr_val is not None and pd.isna(atr_val):
                    atr_val = None
                size = self.risk.volatility_position_size(equity, fill, atr_val)
                if size > 0 and size * fill + self.commission <= cash:
                    cash -= size * fill + self.commission
                    qty = size
                    entry_price = fill
                    entry_time = ts

            equity_points.append(cash + qty * price)

        equity_curve = pd.Series(equity_points, index=close.index, name="equity")
        return BacktestResult(equity_curve, trades, self.initial_cash)
