"""Broker abstraction.

Everything the engine needs from a broker is captured here so the same engine
runs against Alpaca, a future IBKR adapter, or the in-memory simulated broker
used by tests. Concrete brokers translate these calls to their own SDK.
"""
from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass


class OrderSide(enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(enum.Enum):
    MARKET = "market"
    LIMIT = "limit"


@dataclass
class Order:
    symbol: str
    qty: float
    side: OrderSide
    type: OrderType = OrderType.MARKET
    limit_price: float | None = None
    #: Dollar amount for a fractional/notional order. When set, ``qty`` is
    #: ignored and the broker buys/sells this much value (enables small accounts
    #: to hit precise target weights). Market orders only.
    notional: float | None = None
    client_order_id: str | None = None
    # Filled in by the broker after submission:
    id: str | None = None
    status: str | None = None
    filled_qty: float = 0.0
    filled_avg_price: float | None = None


@dataclass
class Position:
    symbol: str
    qty: float
    avg_entry_price: float
    market_value: float = 0.0
    unrealized_pl: float = 0.0


@dataclass
class Account:
    cash: float
    equity: float
    buying_power: float


class Broker(ABC):
    """Minimal trading interface used by the engine."""

    @abstractmethod
    def get_account(self) -> Account: ...

    @abstractmethod
    def get_positions(self) -> list[Position]: ...

    def get_position(self, symbol: str) -> Position | None:
        for pos in self.get_positions():
            if pos.symbol == symbol:
                return pos
        return None

    @abstractmethod
    def get_last_price(self, symbol: str) -> float: ...

    @abstractmethod
    def submit_order(self, order: Order) -> Order: ...

    @abstractmethod
    def cancel_all_orders(self) -> None: ...

    def is_market_open(self) -> bool:  # pragma: no cover - overridden by real brokers
        return True
