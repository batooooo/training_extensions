"""ccxt-based crypto broker (Binance by default).

Implements the same :class:`Broker` interface the stock system uses, so all the
strategy / risk / portfolio / engine code runs unchanged -- only the venue
changes. Uses ``ccxt`` (imported lazily) and works against any ccxt exchange;
Binance is the default. Spot trading, quote currency configurable (USDT).

Paper trading: Binance offers a Spot **testnet**. Set ``sandbox=True`` and use
testnet API keys. Crypto markets are open 24/7, so ``is_market_open`` is always
True.

NOTE: spot exchanges don't track per-lot average cost, so ``avg_entry_price`` on
positions is reported as the current price (unrealized P&L ~0). Rebalancing and
sizing only use quantity * price, so they are unaffected.
"""
from __future__ import annotations

from .base import Account, Broker, Order, OrderSide, OrderType, Position


class CcxtBroker(Broker):
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        exchange: str = "binance",
        sandbox: bool = True,
        quote: str = "USDT",
        symbols: list[str] | None = None,
    ):
        if not api_key or not api_secret:
            raise ValueError("API key/secret are required")
        try:
            import ccxt
        except ImportError as exc:  # pragma: no cover - dependency guard
            raise ImportError("ccxt is required: pip install ccxt") from exc

        if not hasattr(ccxt, exchange):
            raise ValueError(f"unknown ccxt exchange: {exchange!r}")
        self._ex = getattr(ccxt, exchange)(
            {"apiKey": api_key, "secret": api_secret, "enableRateLimit": True}
        )
        if sandbox:
            self._ex.set_sandbox_mode(True)
        self.quote = quote
        self.symbols = symbols or []
        mode = "TESTNET (paper)" if sandbox else "!!! LIVE (real money) !!!"
        print(f"[CcxtBroker] {exchange} connected in {mode} mode")

    # -- helpers ---------------------------------------------------------
    def _base(self, symbol: str) -> str:
        return symbol.split("/")[0]

    # -- Broker interface ------------------------------------------------
    def get_account(self) -> Account:
        bal = self._ex.fetch_balance()
        cash = float(bal.get(self.quote, {}).get("free", 0.0) or 0.0)
        equity = cash
        for sym in self.symbols:
            base = self._base(sym)
            qty = float(bal.get(base, {}).get("total", 0.0) or 0.0)
            if qty > 0:
                equity += qty * self.get_last_price(sym)
        return Account(cash=cash, equity=equity, buying_power=cash)

    def get_positions(self) -> list[Position]:
        bal = self._ex.fetch_balance()
        out: list[Position] = []
        for sym in self.symbols:
            base = self._base(sym)
            qty = float(bal.get(base, {}).get("total", 0.0) or 0.0)
            if qty > 0:
                price = self.get_last_price(sym)
                out.append(
                    Position(symbol=sym, qty=qty, avg_entry_price=price,
                             market_value=qty * price, unrealized_pl=0.0)
                )
        return out

    def get_last_price(self, symbol: str) -> float:
        return float(self._ex.fetch_ticker(symbol)["last"])

    def submit_order(self, order: Order) -> Order:
        side = "buy" if order.side is OrderSide.BUY else "sell"
        if order.notional is not None:
            # Market order specified by quote-currency cost (e.g. spend 50 USDT).
            result = self._ex.create_order(
                order.symbol, "market", side, amount=None,
                price=None, params={"cost": order.notional},
            )
        elif order.type is OrderType.LIMIT:
            if order.limit_price is None:
                raise ValueError("limit order requires limit_price")
            result = self._ex.create_order(
                order.symbol, "limit", side, order.qty, order.limit_price
            )
        else:
            result = self._ex.create_order(order.symbol, "market", side, order.qty)
        order.id = str(result.get("id"))
        order.status = str(result.get("status"))
        order.filled_qty = float(result.get("filled") or 0.0)
        order.filled_avg_price = result.get("average")
        return order

    def cancel_all_orders(self) -> None:
        for sym in self.symbols:
            try:
                self._ex.cancel_all_orders(sym)
            except Exception:  # not all exchanges support it per-symbol
                for o in self._ex.fetch_open_orders(sym):
                    self._ex.cancel_order(o["id"], sym)

    def is_market_open(self) -> bool:
        return True  # crypto trades 24/7
