"""Risk management -- the gate every order must pass through.

Responsibilities:
  * position sizing: how many shares to buy given equity and a per-trade cap;
  * per-position stop-loss / take-profit checks;
  * a daily loss limit that halts new entries (kill switch) once breached.

The engine asks the risk manager *how much* to buy and *whether* it is still
allowed to trade. Strategies decide direction; risk decides size and safety.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RiskConfig:
    #: Max fraction of equity to deploy into a single position (0..1).
    max_position_pct: float = 0.10
    #: Absolute cash cap per position (account currency). None disables.
    #: When set, the effective budget is min(equity * max_position_pct, this).
    max_position_notional: float | None = None
    #: Stop-loss as a fraction below entry (e.g. 0.05 = -5%). None disables.
    stop_loss_pct: float | None = 0.05
    #: Take-profit as a fraction above entry. None disables.
    take_profit_pct: float | None = 0.15
    #: Halt new entries once the day's realized+unrealized loss exceeds this
    #: fraction of starting equity (e.g. 0.03 = -3%). None disables.
    max_daily_loss_pct: float | None = 0.03
    #: Volatility sizing: fraction of capital to risk per trade (e.g. 0.01 = 1%).
    #: When set, position size targets a fixed dollar risk = capital * this,
    #: using an ATR-based stop distance. None -> simple percent-of-equity sizing.
    risk_per_trade_pct: float | None = None
    #: Stop distance in ATR units used for volatility sizing (e.g. 2 -> 2*ATR).
    atr_stop_multiple: float = 2.0

    def __post_init__(self):
        if not 0 < self.max_position_pct <= 1:
            raise ValueError("max_position_pct must be in (0, 1]")


class RiskManager:
    def __init__(self, config: RiskConfig | None = None):
        self.config = config or RiskConfig()
        self._day_start_equity: float | None = None
        self.halted = False

    def start_day(self, equity: float) -> None:
        """Reset the daily loss tracker. Call at the start of each session."""
        self._day_start_equity = equity
        self.halted = False

    def position_size(self, equity: float, price: float) -> int:
        """Whole-share quantity for a new entry, respecting the per-position cap."""
        if price <= 0:
            return 0
        return int(self._budget(equity) // price)

    def _budget(self, equity: float) -> float:
        """Cash ceiling for a single position."""
        budget = equity * self.config.max_position_pct
        if self.config.max_position_notional is not None:
            budget = min(budget, self.config.max_position_notional)
        return budget

    def volatility_position_size(
        self, equity: float, price: float, atr: float | None
    ) -> int:
        """Size so that an ATR-based stop risks a fixed fraction of capital.

        shares = (equity * risk_per_trade_pct) / (atr_stop_multiple * ATR),
        then capped by the per-position cash budget. Falls back to plain
        :meth:`position_size` when volatility sizing is not configured or ATR
        is unavailable. This is the professional "risk a fixed % per trade"
        method: volatile names get smaller positions, calm names larger ones.
        """
        if (
            self.config.risk_per_trade_pct is None
            or atr is None
            or atr <= 0
            or price <= 0
        ):
            return self.position_size(equity, price)
        stop_distance = self.config.atr_stop_multiple * atr
        if stop_distance <= 0:
            return 0
        risk_capital = equity * self.config.risk_per_trade_pct
        qty = int(risk_capital // stop_distance)
        qty = min(qty, int(self._budget(equity) // price))  # never exceed budget
        return max(qty, 0)

    def check_daily_loss(self, equity: float) -> bool:
        """Return True if trading may continue; flips the kill switch if not."""
        limit = self.config.max_daily_loss_pct
        if limit is None or self._day_start_equity is None:
            return True
        drawdown = (self._day_start_equity - equity) / self._day_start_equity
        if drawdown >= limit:
            self.halted = True
        return not self.halted

    def should_exit(self, entry_price: float, current_price: float) -> str | None:
        """Return ``"stop_loss"`` / ``"take_profit"`` if an exit is triggered."""
        if entry_price <= 0:
            return None
        change = (current_price - entry_price) / entry_price
        sl = self.config.stop_loss_pct
        tp = self.config.take_profit_pct
        if sl is not None and change <= -sl:
            return "stop_loss"
        if tp is not None and change >= tp:
            return "take_profit"
        return None
