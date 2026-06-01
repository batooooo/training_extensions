#!/usr/bin/env python
"""Send a portfolio snapshot (positions, P&L, pending orders) to Telegram.

Run it any time -- before the open it reports pending orders; after fills it
reports holdings and unrealized P&L. Pair with cron for a daily summary.

    python scripts/report.py
"""
from __future__ import annotations

import datetime as dt
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trading.broker import AlpacaBroker  # noqa: E402
from trading.notify import from_env as notifier_from_env  # noqa: E402
from trading.report import format_report  # noqa: E402


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    key, secret = os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_API_SECRET")
    if not key or not secret:
        raise SystemExit("ALPACA_API_KEY / ALPACA_API_SECRET must be set in the environment")

    broker = AlpacaBroker(key, secret, paper=True)
    account = broker.get_account()
    positions = broker.get_positions()

    # Count open orders directly from the underlying client.
    from alpaca.trading.enums import QueryOrderStatus
    from alpaca.trading.requests import GetOrdersRequest

    pending = len(broker._trading.get_orders(GetOrdersRequest(status=QueryOrderStatus.OPEN)))

    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = format_report(account, positions, pending, title=f"Portfolio report {stamp}")
    print(msg)
    notifier_from_env().send(msg)


if __name__ == "__main__":
    main()
