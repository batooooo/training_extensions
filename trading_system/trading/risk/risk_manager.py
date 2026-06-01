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
    #: Stop-loss as a fraction below entry (e.g. 0.05 = -5%). None disables.
    stop_loss_pct: float | None = 0.05
    #: Take-profit as a fraction above entry. None disables.
    take_profit_pct: float | None = 0.15
    #: Halt new entries once the day's realized+unrealized loss exceeds this
    #: fraction of starting equity (e.g. 0.03 = -3%). None disables.
    max_daily_loss_pct: float | None = 0.03

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
        budget = equity * self.config.max_position_pct
        return int(budget // price)

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
