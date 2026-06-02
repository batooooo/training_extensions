#!/usr/bin/env python
"""Rebalance a crypto basket to target weights, with a trend regime gate.

A coin is funded only while its regime_strategy signal is BUY (in an uptrend);
coins that lose the trend are sold to cash. Fractional (notional) orders let a
small account hit exact weights.

    python scripts/rebalance.py --config portfolio.yaml --dry-run
    python scripts/rebalance.py --config portfolio.yaml            # testnet/paper
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crypto import strategies  # noqa: E402
from crypto.broker import CcxtBroker  # noqa: E402
from crypto.data import fetch_ccxt_ohlcv  # noqa: E402
from crypto.notify import from_env as notifier_from_env  # noqa: E402
from crypto.portfolio import PortfolioManager  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--contribution", type=float, default=0.0, help="extra capital this run (DCA)")
    p.add_argument("--from-holdings", action="store_true",
                   help="base capital on current holdings value + contribution")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    with open(args.config) as fh:
        cfg = yaml.safe_load(fh)

    key = os.getenv("CRYPTO_API_KEY") or os.getenv("BINANCE_API_KEY")
    secret = os.getenv("CRYPTO_API_SECRET") or os.getenv("BINANCE_API_SECRET")
    if not key or not secret:
        raise SystemExit("CRYPTO_API_KEY / CRYPTO_API_SECRET (or BINANCE_*) must be set")

    exchange = cfg.get("exchange", "binance")
    sandbox = cfg.get("mode", "paper") != "live"
    targets = cfg["targets"]
    timeframe = cfg.get("timeframe", "1d")
    symbols = list(targets)

    broker = CcxtBroker(key, secret, exchange=exchange, sandbox=sandbox, symbols=symbols)
    strategy = strategies.create(cfg["regime_strategy"]) if cfg.get("regime_strategy") else None

    if args.from_holdings:
        held = {p.symbol: p.qty for p in broker.get_positions()}
        cap = sum(q * broker.get_last_price(s) for s, q in held.items() if s in targets) + args.contribution
    else:
        cap = float(cfg.get("capital_base", 0.0)) + args.contribution

    def data_fn(symbol: str):
        return fetch_ccxt_ohlcv(symbol, timeframe=timeframe, limit=300, exchange=exchange)

    pm = PortfolioManager(broker, targets, cap, strategy=strategy,
                          dry_run=args.dry_run or cfg.get("mode") == "backtest",
                          notifier=notifier_from_env())
    logging.info("rebalancing %s to %s (capital=%.2f)", exchange, targets, cap)
    pm.rebalance(data_fn=data_fn)


if __name__ == "__main__":
    main()
