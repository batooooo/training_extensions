"""In-memory simulated broker.

Used by tests and for dry-running the *live* engine without touching a real
account or the network. Fills market orders instantly at the last price you
feed in via :meth:`set_price`.
"""
from __future__ import annotations

import itertools

from .base import Account, Broker, Order, OrderSide, Position


class SimulatedBroker(Broker):
    def __init__(self, cash: float = 100_000.0):
        self._cash = cash
        self._positions: dict[str, Position] = {}
        self._prices: dict[str, float] = {}
        self._ids = itertools.count(1)
        self.order_log: list[Order] = []

    def set_price(self, symbol: str, price: float) -> None:
        self._prices[symbol] = price

    def get_last_price(self, symbol: str) -> float:
        if symbol not in self._prices:
            raise KeyError(f"no simulated price set for {symbol}")
        return self._prices[symbol]

    def get_account(self) -> Account:
        equity = self._cash + sum(
            p.qty * self._prices.get(p.symbol, p.avg_entry_price)
            for p in self._positions.values()
        )
        return Account(cash=self._cash, equity=equity, buying_power=self._cash)

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def submit_order(self, order: Order) -> Order:
        price = self.get_last_price(order.symbol)
        # Notional (dollar-amount) orders translate to a fractional quantity.
        qty = order.notional / price if order.notional is not None else order.qty
        order.qty = qty
        cost = qty * price
        if order.side is OrderSide.BUY:
            if cost > self._cash + 1e-9:
                raise ValueError("insufficient cash in simulated broker")
            self._cash -= cost
            pos = self._positions.get(order.symbol)
            if pos is None:
                self._positions[order.symbol] = Position(
                    symbol=order.symbol, qty=order.qty, avg_entry_price=price
                )
            else:
                total_qty = pos.qty + order.qty
                pos.avg_entry_price = (
                    pos.avg_entry_price * pos.qty + price * order.qty
                ) / total_qty
                pos.qty = total_qty
        else:  # SELL
            pos = self._positions.get(order.symbol)
            held = pos.qty if pos else 0.0
            sell_qty = min(order.qty, held)
            self._cash += sell_qty * price
            if pos is not None:
                pos.qty -= sell_qty
                if pos.qty <= 1e-9:
                    del self._positions[order.symbol]

        order.id = str(next(self._ids))
        order.status = "filled"
        order.filled_qty = order.qty
        order.filled_avg_price = price
        self.order_log.append(order)
        return order

    def cancel_all_orders(self) -> None:
        pass
