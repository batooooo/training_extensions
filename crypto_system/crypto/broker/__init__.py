from .base import (
    Account,
    Broker,
    Order,
    OrderSide,
    OrderType,
    Position,
)
from .simulated import SimulatedBroker

__all__ = [
    "Account",
    "Broker",
    "Order",
    "OrderSide",
    "OrderType",
    "Position",
    "SimulatedBroker",
    "CcxtBroker",
]


def __getattr__(name):
    # Lazy import so the optional ccxt dependency is only loaded when needed.
    if name == "CcxtBroker":
        from .ccxt_broker import CcxtBroker

        return CcxtBroker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
