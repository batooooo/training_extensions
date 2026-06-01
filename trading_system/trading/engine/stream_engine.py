"""Real-time streaming engine (WebSocket push, not polling).

Instead of asking Alpaca for prices every N seconds, this subscribes to Alpaca's
live bar stream: the moment a new (minute) bar closes, Alpaca pushes it to us and
we re-evaluate the strategy for that symbol. Decision logic, risk and sizing are
reused verbatim from :class:`LiveEngine` -- only the *trigger* differs.

A rolling per-symbol OHLCV buffer is seeded with history (so indicators like a
50-bar SMA have enough data immediately) and appended to on every streamed bar.
"""
from __future__ import annotations

import logging
from typing import Callable

import pandas as pd

from ..broker import Broker
from ..risk import RiskConfig
from ..strategies import Strategy
from .live_engine import LiveEngine

logger = logging.getLogger("trading.stream")

HistoryFn = Callable[[str], pd.DataFrame]


class StreamEngine:
    def __init__(
        self,
        broker: Broker,
        strategy: Strategy,
        symbols: list[str],
        history_fn: HistoryFn,
        api_key: str,
        api_secret: str,
        risk_config: RiskConfig | None = None,
        dry_run: bool = True,
        capital_base: float | None = None,
        feed: str = "iex",
        max_buffer: int = 500,
    ):
        self.symbols = symbols
        self.history_fn = history_fn
        self.api_key = api_key
        self.api_secret = api_secret
        self.feed = feed
        self.max_buffer = max_buffer
        self._buffers: dict[str, pd.DataFrame] = {}

        # Reuse all live trading logic; feed it from our in-memory buffers.
        self.engine = LiveEngine(
            broker=broker,
            strategy=strategy,
            symbols=symbols,
            data_fn=lambda s: self._buffers.get(s),
            risk_config=risk_config,
            dry_run=dry_run,
            capital_base=capital_base,
        )

    def _seed_history(self) -> None:
        for symbol in self.symbols:
            df = self.history_fn(symbol)
            self._buffers[symbol] = df.tail(self.max_buffer).copy()
            logger.info("seeded %s with %d historical bars", symbol, len(df))

    async def _on_bar(self, bar) -> None:
        """Async handler invoked by Alpaca on each new streamed bar."""
        symbol = bar.symbol
        ts = pd.Timestamp(bar.timestamp)
        buf = self._buffers.get(symbol)
        if buf is None:
            return
        buf.loc[ts] = [bar.open, bar.high, bar.low, bar.close, bar.volume]
        if len(buf) > self.max_buffer:
            self._buffers[symbol] = buf.iloc[-self.max_buffer :]
        logger.info("bar %s close=%.2f @ %s", symbol, bar.close, ts)
        # Synchronous decision + (optional) order submission.
        self.engine.run_symbol(symbol)

    def run(self) -> None:
        """Seed history then block on the WebSocket stream."""
        from alpaca.data.live import StockDataStream

        self._seed_history()
        stream = StockDataStream(self.api_key, self.api_secret, feed=self.feed)
        stream.subscribe_bars(self._on_bar, *self.symbols)
        logger.info(
            "streaming live bars for %s (feed=%s, dry_run=%s)",
            self.symbols, self.feed, self.engine.dry_run,
        )
        stream.run()  # blocks; manages its own asyncio loop
