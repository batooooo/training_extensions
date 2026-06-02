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
    "AlpacaBroker",
]


def __getattr__(name):
    # Lazy import so the heavy/optional alpaca-py dependency is only loaded
    # when AlpacaBroker is actually used.
    if name == "AlpacaBroker":
        from .alpaca_broker import AlpacaBroker

        return AlpacaBroker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
