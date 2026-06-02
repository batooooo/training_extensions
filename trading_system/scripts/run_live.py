#!/usr/bin/env python
"""Run the live/paper trading engine from a config file.

    python scripts/run_live.py --config config.yaml

Safety:
  * mode defaults to "paper"; "live" (real money) must be set in config AND
    confirmed interactively at startup.
  * pass --dry-run to compute and log orders without submitting them.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trading import strategies  # noqa: E402
from trading.broker import AlpacaBroker  # noqa: E402
from trading.config import load_config  # noqa: E402
from trading.data import fetch_alpaca_bars  # noqa: E402
from trading.engine import LiveEngine  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True, help="path to YAML config")
    p.add_argument("--dry-run", action="store_true", help="log orders without submitting")
    p.add_argument("--once", action="store_true", help="run a single cycle and exit")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(args.config)

    if not cfg.api_key or not cfg.api_secret:
        raise SystemExit("ALPACA_API_KEY / ALPACA_API_SECRET must be set in the environment")

    if cfg.mode == "live" and not args.dry_run:
        confirm = input(
            "\n*** LIVE TRADING with REAL MONEY is enabled. Type 'I UNDERSTAND' to continue: "
        )
        if confirm.strip() != "I UNDERSTAND":
            raise SystemExit("aborted.")

    broker = AlpacaBroker(cfg.api_key, cfg.api_secret, paper=cfg.paper)
    strategy = strategies.create(cfg.strategy_name, **cfg.strategy_params)

    def data_fn(symbol: str):
        return fetch_alpaca_bars(
            symbol,
            start=None or "2000-01-01",  # broad start; broker caps lookback anyway
            timeframe=cfg.timeframe,
            api_key=cfg.api_key,
            api_secret=cfg.api_secret,
        ).tail(cfg.lookback_bars)

    engine = LiveEngine(
        broker=broker,
        strategy=strategy,
        symbols=cfg.symbols,
        data_fn=data_fn,
        risk_config=cfg.risk,
        dry_run=args.dry_run or cfg.mode == "backtest",
        capital_base=cfg.capital_base,
    )

    logging.info(
        "starting engine: mode=%s strategy=%s symbols=%s dry_run=%s capital_base=%s",
        cfg.mode, strategy.name, cfg.symbols, engine.dry_run, cfg.capital_base,
    )

    if args.once:
        engine.run_once()
        return

    try:
        while True:
            if broker.is_market_open():
                engine.run_once()
            else:
                logging.info("market closed; sleeping")
                engine.reset_day()
            time.sleep(cfg.poll_seconds)
    except KeyboardInterrupt:
        logging.info("interrupted; cancelling open orders")
        broker.cancel_all_orders()


if __name__ == "__main__":
    main()
