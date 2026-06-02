#!/usr/bin/env python
"""Real-time fill watcher: push a Telegram alert the instant an order fills.

Subscribes to Alpaca's trade-update stream (WebSocket push, not polling) and
sends a notification on every fill / partial fill. Leave it running during
market hours; it reacts immediately when your queued orders execute.

    python scripts/watch.py

This is a long-running process -- run it on a machine that stays on (your PC or
a small server), not an ephemeral session.
"""
from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trading.notify import from_env as notifier_from_env  # noqa: E402
from trading.report import format_fill  # noqa: E402

logger = logging.getLogger("trading.watch")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    key, secret = os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_API_SECRET")
    if not key or not secret:
        raise SystemExit("ALPACA_API_KEY / ALPACA_API_SECRET must be set in the environment")

    from alpaca.trading.stream import TradingStream

    notifier = notifier_from_env()
    stream = TradingStream(key, secret, paper=True)

    async def on_trade_update(data) -> None:
        event = str(getattr(data, "event", ""))
        order = data.order
        if event in ("fill", "partial_fill"):
            qty = float(getattr(data, "qty", None) or order.filled_qty or 0)
            price = float(getattr(data, "price", None) or order.filled_avg_price or 0)
            msg = format_fill(event, order.symbol, str(order.side.value), qty, price)
            logger.info(msg)
            notifier.send(msg)
        else:
            logger.info("trade update: %s %s", event, order.symbol)

    stream.subscribe_trade_updates(on_trade_update)
    logger.info("watching for fills in real time (Ctrl-C to stop)...")
    notifier.send("👀 실시간 체결 감시 시작 — 주문이 체결되면 바로 알려드립니다.")
    stream.run()


if __name__ == "__main__":
    main()
