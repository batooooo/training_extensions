#!/usr/bin/env python
"""Rebalance a target-weight portfolio (with fractional shares + monthly DCA).

Reads a portfolio YAML describing target weights and capital, then issues
fractional orders to move the account toward those weights. A regime strategy
(e.g. trend_momentum) gates each sleeve: holdings that lose their uptrend are
sold to cash.

    python scripts/rebalance.py --config portfolio.yaml --dry-run
    python scripts/rebalance.py --config portfolio.yaml            # paper orders

Monthly DCA: pass --contribution 100 to add $100 of fresh capital this run.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trading import strategies  # noqa: E402
from trading.broker import AlpacaBroker  # noqa: E402
from trading.data import fetch_alpaca_bars  # noqa: E402
from trading.portfolio import PortfolioManager  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True, help="portfolio YAML")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--contribution", type=float, default=0.0,
                   help="extra capital added this run (monthly DCA)")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with open(args.config) as fh:
        cfg = yaml.safe_load(fh)

    import os
    key, secret = os.getenv("ALPACA_API_KEY"), os.getenv("ALPACA_API_SECRET")
    if not key or not secret:
        raise SystemExit("ALPACA_API_KEY / ALPACA_API_SECRET must be set in the environment")

    targets = cfg["targets"]
    capital = float(cfg.get("capital_base", 0.0)) + args.contribution
    timeframe = cfg.get("timeframe", "1Day")

    broker = AlpacaBroker(key, secret, paper=cfg.get("mode", "paper") != "live")
    strategy = None
    if cfg.get("regime_strategy"):
        strategy = strategies.create(cfg["regime_strategy"])

    def data_fn(symbol: str):
        return fetch_alpaca_bars(symbol, start="2024-01-01", timeframe=timeframe,
                                 api_key=key, api_secret=secret).tail(260)

    pm = PortfolioManager(broker, targets, capital, strategy=strategy,
                          dry_run=args.dry_run or cfg.get("mode") == "backtest")
    logging.info("rebalancing to %s with capital=$%.2f (contribution=$%.2f)",
                 targets, capital, args.contribution)
    pm.rebalance(data_fn=data_fn)


if __name__ == "__main__":
    main()
