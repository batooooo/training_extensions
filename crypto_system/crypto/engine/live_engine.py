"""Live (and paper) trading engine.

On each cycle, for every symbol it:
  1. pulls recent bars and the current position from the broker;
  2. checks risk exits (stop-loss / take-profit) and the daily-loss kill switch;
  3. asks the strategy for the latest signal;
  4. routes BUY/SELL through the risk manager for sizing, then submits an order.

The strategy and risk logic are byte-for-byte the same ones the backtester
exercises, so behaviour you validated offline carries over. ``dry_run=True``
logs intended orders without submitting them -- the safe default.
"""
from __future__ import annotations

import logging
from typing import Callable

import pandas as pd

from ..broker import Broker, Order, OrderSide
from ..risk import RiskConfig, RiskManager
from ..strategies import Signal, Strategy
from ..utils import indicators

logger = logging.getLogger("trading.live")

# Returns recent OHLCV bars for a symbol (most recent last).
DataFn = Callable[[str], pd.DataFrame]


def _latest_atr(data: pd.DataFrame) -> float | None:
    """Most recent ATR from an OHLCV frame, or None if not computable."""
    if not {"high", "low", "close"}.issubset(data.columns):
        return None
    series = indicators.atr(data["high"], data["low"], data["close"])
    if series.empty or pd.isna(series.iloc[-1]):
        return None
    return float(series.iloc[-1])


class LiveEngine:
    def __init__(
        self,
        broker: Broker,
        strategy: Strategy,
        symbols: list[str],
        data_fn: DataFn,
        risk_config: RiskConfig | None = None,
        dry_run: bool = True,
        capital_base: float | None = None,
    ):
        self.broker = broker
        self.strategy = strategy
        self.symbols = symbols
        self.data_fn = data_fn
        self.risk = RiskManager(risk_config)
        self.dry_run = dry_run
        # When set, position sizing uses this fixed capital amount instead of
        # the broker's full account equity -- e.g. "trade as if I only have
        # 1,000,000 KRW" even though the paper account holds $100k.
        self.capital_base = capital_base
        self._day_started = False

    def _submit(self, symbol: str, side: OrderSide, qty: float, why: str,
                notional: float | None = None) -> None:
        # Crypto is bought by quote-currency amount (notional) so fractional
        # coins work; sells use the held quantity.
        if notional is not None:
            if notional <= 0:
                return
            order = Order(symbol=symbol, qty=0.0, side=side, notional=notional)
            what = f"${notional:.2f}"
        else:
            if qty <= 0:
                return
            order = Order(symbol=symbol, qty=qty, side=side)
            what = f"x{qty}"
        if self.dry_run:
            logger.info("[DRY-RUN] %s %s %s (%s)", side.value, symbol, what, why)
            return
        result = self.broker.submit_order(order)
        logger.info(
            "ORDER %s %s %s (%s) -> id=%s status=%s",
            side.value, symbol, what, why, result.id, result.status,
        )

    def _sizing_equity(self) -> float:
        """Budget used for position sizing: the simulated capital base if set,
        otherwise the real account equity. Also primes the daily-loss guard."""
        account = self.broker.get_account()
        if not self._day_started:
            self.risk.start_day(account.equity)
            self._day_started = True
        if not self.risk.check_daily_loss(account.equity):
            logger.warning("daily loss limit hit -- new entries halted")
        return self.capital_base if self.capital_base is not None else account.equity

    def run_once(self) -> None:
        """Run one decision cycle across all symbols (polling mode)."""
        sizing_equity = self._sizing_equity()
        for symbol in self.symbols:
            try:
                self._process_symbol(symbol, sizing_equity)
            except Exception:  # one bad symbol shouldn't kill the loop
                logger.exception("error processing %s", symbol)

    def run_symbol(self, symbol: str) -> None:
        """Evaluate and act on a single symbol (used by the streaming engine)."""
        try:
            self._process_symbol(symbol, self._sizing_equity())
        except Exception:
            logger.exception("error processing %s", symbol)

    def _process_symbol(self, symbol: str, equity: float) -> None:
        data = self.data_fn(symbol)
        if data is None or data.empty:
            logger.warning("no data for %s, skipping", symbol)
            return

        price = float(data["close"].iloc[-1])
        position = self.broker.get_position(symbol)
        held = position.qty if position else 0.0

        # 1) risk exit takes priority over any strategy signal
        if held > 0:
            reason = self.risk.should_exit(position.avg_entry_price, price)
            if reason is not None:
                self._submit(symbol, OrderSide.SELL, held, reason)
                return

        signal = self.strategy.latest_signal(data)

        if signal is Signal.SELL and held > 0:
            self._submit(symbol, OrderSide.SELL, held, "signal")
        elif signal is Signal.BUY and held <= 0:
            if self.risk.halted:
                logger.info("entry for %s skipped: trading halted", symbol)
                return
            # Spend a quote-currency budget (notional) -> fractional coins.
            budget = self.risk.order_budget(equity)
            self._submit(symbol, OrderSide.BUY, 0.0, "signal", notional=budget)

    def reset_day(self) -> None:
        """Call at the start of a new trading day."""
        self._day_started = False
