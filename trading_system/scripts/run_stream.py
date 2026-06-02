#!/usr/bin/env python
"""Run the REAL-TIME streaming engine (WebSocket push).

Unlike run_live.py (which polls every poll_seconds), this reacts the instant a
new bar arrives from Alpaca's live feed.

    python scripts/run_stream.py --config config.yaml --dry-run   # safe: no orders
    python scripts/run_stream.py --config config.yaml             # paper orders

Notes:
  * Free Alpaca accounts use the IEX feed (real-time, partial volume).
  * The stream only emits bars while the US market is open.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trading import strategies  # noqa: E402
from trading.broker import AlpacaBroker  # noqa: E402
from trading.config import load_config  # noqa: E402
from trading.data import fetch_alpaca_bars  # noqa: E402
from trading.engine import StreamEngine  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--dry-run", action="store_true", help="log orders without submitting")
    p.add_argument("--feed", default="iex", choices=["iex", "sip"], help="data feed (sip needs a paid plan)")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(args.config)
    if not cfg.api_key or not cfg.api_secret:
        raise SystemExit("ALPACA_API_KEY / ALPACA_API_SECRET must be set in the environment")

    if cfg.mode == "live" and not args.dry_run:
        confirm = input("\n*** LIVE streaming with REAL MONEY. Type 'I UNDERSTAND' to continue: ")
        if confirm.strip() != "I UNDERSTAND":
            raise SystemExit("aborted.")

    broker = AlpacaBroker(cfg.api_key, cfg.api_secret, paper=cfg.paper)
    strategy = strategies.create(cfg.strategy_name, **cfg.strategy_params)

    def history_fn(symbol: str):
        return fetch_alpaca_bars(
            symbol, start="2024-01-01", timeframe=cfg.timeframe,
            api_key=cfg.api_key, api_secret=cfg.api_secret,
        ).tail(cfg.lookback_bars)

    engine = StreamEngine(
        broker=broker,
        strategy=strategy,
        symbols=cfg.symbols,
        history_fn=history_fn,
        api_key=cfg.api_key,
        api_secret=cfg.api_secret,
        risk_config=cfg.risk,
        dry_run=args.dry_run or cfg.mode == "backtest",
        capital_base=cfg.capital_base,
        feed=args.feed,
    )
    try:
        engine.run()
    except KeyboardInterrupt:
        logging.info("interrupted; cancelling open orders")
        broker.cancel_all_orders()


if __name__ == "__main__":
    main()
