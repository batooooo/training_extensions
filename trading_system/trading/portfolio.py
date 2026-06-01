"""Target-weight portfolio management with fractional shares.

For small accounts, the right tool isn't one signal -- it's an *allocation*. You
declare target weights (e.g. core 80% / satellite 20%), and the manager issues
fractional (notional) orders to move the portfolio toward those weights. A
strategy can act as a per-symbol regime gate: if it isn't a BUY (e.g. price below
the 200-day trend), that sleeve's target drops to 0 and the manager sells it to
cash -- capital protection in downturns.

Monthly dollar-cost averaging is just calling :meth:`rebalance` again with a
larger ``capital`` after a contribution.
"""
from __future__ import annotations

import logging
from typing import Callable

import pandas as pd

from .broker import Broker, Order, OrderSide
from .strategies import Signal, Strategy

logger = logging.getLogger("trading.portfolio")

DataFn = Callable[[str], pd.DataFrame]


def plan_rebalance(
    targets: dict[str, float],
    capital: float,
    prices: dict[str, float],
    positions: dict[str, float],
    min_trade: float = 1.0,
) -> list[Order]:
    """Pure planner: orders needed to move toward target weights.

    ``targets`` maps symbol -> weight (0..1; weights summing to <1 leave the
    remainder in cash). Buys are notional (dollar) orders; sells are fractional
    quantity orders. Trades smaller than ``min_trade`` dollars are skipped.
    """
    orders: list[Order] = []
    symbols = set(targets) | set(positions)
    for symbol in sorted(symbols):
        price = prices.get(symbol)
        if not price or price <= 0:
            continue
        target_value = capital * targets.get(symbol, 0.0)
        held = positions.get(symbol, 0.0)
        delta = target_value - held * price
        if delta > min_trade:
            orders.append(Order(symbol, qty=0.0, side=OrderSide.BUY, notional=round(delta, 2)))
        elif delta < -min_trade and held > 0:
            sell_qty = min(held, (-delta) / price)
            orders.append(Order(symbol, qty=sell_qty, side=OrderSide.SELL))
    return orders


class PortfolioManager:
    def __init__(
        self,
        broker: Broker,
        targets: dict[str, float],
        capital_base: float,
        strategy: Strategy | None = None,
        dry_run: bool = True,
        min_trade: float = 1.0,
    ):
        if sum(targets.values()) > 1.0 + 1e-9:
            raise ValueError("target weights sum to more than 1.0")
        self.broker = broker
        self.targets = targets
        self.capital_base = capital_base
        self.strategy = strategy
        self.dry_run = dry_run
        self.min_trade = min_trade

    def _regime_adjusted_targets(self, data_fn: DataFn | None) -> dict[str, float]:
        """Zero out any sleeve whose strategy signal is not BUY (-> sell to cash)."""
        if self.strategy is None or data_fn is None:
            return dict(self.targets)
        adjusted = {}
        for symbol, weight in self.targets.items():
            sig = self.strategy.latest_signal(data_fn(symbol))
            if sig is Signal.BUY:
                adjusted[symbol] = weight
            else:
                adjusted[symbol] = 0.0
                logger.info("regime gate: %s not in uptrend (%s) -> cash", symbol, sig.name)
        return adjusted

    def rebalance(self, data_fn: DataFn | None = None) -> list[Order]:
        """Compute and (unless dry_run) submit orders toward target weights."""
        targets = self._regime_adjusted_targets(data_fn)
        prices = {s: self.broker.get_last_price(s) for s in self.targets}
        positions = {p.symbol: p.qty for p in self.broker.get_positions()}
        orders = plan_rebalance(
            targets, self.capital_base, prices, positions, self.min_trade
        )
        for order in orders:
            if order.side is OrderSide.BUY:
                what = f"${order.notional:.2f}"
            else:
                what = f"{order.qty:.4f} sh"
            if self.dry_run:
                logger.info("[DRY-RUN] %s %s %s", order.side.value, order.symbol, what)
            else:
                res = self.broker.submit_order(order)
                logger.info("ORDER %s %s %s -> %s", order.side.value, order.symbol, what, res.status)
        return orders
