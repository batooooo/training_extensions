"""Alpaca broker adapter.

Wraps ``alpaca-py`` behind the :class:`Broker` interface. The SDK is imported
lazily so the rest of the package (backtester, strategies, tests) works without
it installed.

Paper trading is the default. Live trading requires ``paper=False`` to be set
*explicitly* -- there is no way to trade real money by accident.
"""
from __future__ import annotations

from .base import Account, Broker, Order, OrderSide, OrderType, Position


class AlpacaBroker(Broker):
    PAPER_ENDPOINT = "https://paper-api.alpaca.markets"
    LIVE_ENDPOINT = "https://api.alpaca.markets"

    def __init__(self, api_key: str, api_secret: str, paper: bool = True):
        if not api_key or not api_secret:
            raise ValueError("Alpaca API key/secret are required")
        self.paper = paper
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.trading.client import TradingClient
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ImportError(
                "alpaca-py is required for live/paper trading. "
                "Install it with: pip install alpaca-py"
            ) from exc

        self._trading = TradingClient(api_key, api_secret, paper=paper)
        self._data = StockHistoricalDataClient(api_key, api_secret)
        mode = "PAPER" if paper else "!!! LIVE (real money) !!!"
        print(f"[AlpacaBroker] connected in {mode} mode")

    def get_account(self) -> Account:
        a = self._trading.get_account()
        return Account(
            cash=float(a.cash),
            equity=float(a.equity),
            buying_power=float(a.buying_power),
        )

    def get_positions(self) -> list[Position]:
        out = []
        for p in self._trading.get_all_positions():
            out.append(
                Position(
                    symbol=p.symbol,
                    qty=float(p.qty),
                    avg_entry_price=float(p.avg_entry_price),
                    market_value=float(p.market_value),
                    unrealized_pl=float(p.unrealized_pl),
                )
            )
        return out

    def get_last_price(self, symbol: str) -> float:
        from alpaca.data.requests import StockLatestTradeRequest

        req = StockLatestTradeRequest(symbol_or_symbols=symbol)
        trade = self._data.get_stock_latest_trade(req)
        return float(trade[symbol].price)

    def submit_order(self, order: Order) -> Order:
        from alpaca.trading.enums import OrderSide as AlpacaSide
        from alpaca.trading.enums import TimeInForce
        from alpaca.trading.requests import (
            LimitOrderRequest,
            MarketOrderRequest,
        )

        side = AlpacaSide.BUY if order.side is OrderSide.BUY else AlpacaSide.SELL
        if order.notional is not None:
            # Fractional dollar-amount order (market, DAY).
            req = MarketOrderRequest(
                symbol=order.symbol,
                notional=round(order.notional, 2),
                side=side,
                time_in_force=TimeInForce.DAY,
                client_order_id=order.client_order_id,
            )
        elif order.type is OrderType.LIMIT:
            if order.limit_price is None:
                raise ValueError("limit order requires limit_price")
            req = LimitOrderRequest(
                symbol=order.symbol,
                qty=order.qty,
                side=side,
                time_in_force=TimeInForce.DAY,
                limit_price=order.limit_price,
                client_order_id=order.client_order_id,
            )
        else:
            req = MarketOrderRequest(
                symbol=order.symbol,
                qty=order.qty,
                side=side,
                time_in_force=TimeInForce.DAY,
                client_order_id=order.client_order_id,
            )
        result = self._trading.submit_order(req)
        order.id = str(result.id)
        order.status = str(result.status)
        order.filled_qty = float(result.filled_qty or 0.0)
        order.filled_avg_price = (
            float(result.filled_avg_price) if result.filled_avg_price else None
        )
        return order

    def cancel_all_orders(self) -> None:
        self._trading.cancel_orders()

    def is_market_open(self) -> bool:
        return bool(self._trading.get_clock().is_open)
