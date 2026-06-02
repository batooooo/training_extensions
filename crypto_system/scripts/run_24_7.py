#!/usr/bin/env python
"""24/7 crypto trading loop (strategy-driven).

Crypto never closes, so this just polls every ``poll_seconds``, recomputes the
strategy signal for each symbol from fresh candles, and routes BUY/SELL through
the risk manager -- the same engine the stock system uses, minus market hours.

    python scripts/run_24_7.py --config config.yaml --dry-run   # safe: logs only
    python scripts/run_24_7.py --config config.yaml             # paper/testnet
    python scripts/run_24_7.py --config config.yaml --once       # single cycle

Live (real money) requires mode: live in config AND an interactive confirm.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crypto import strategies  # noqa: E402
from crypto.broker import CcxtBroker  # noqa: E402
from crypto.config import load_config  # noqa: E402
from crypto.data import fetch_ccxt_ohlcv  # noqa: E402
from crypto.engine import LiveEngine  # noqa: E402
from crypto.notify import from_env as notifier_from_env  # noqa: E402

logger = logging.getLogger("crypto.run")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", required=True)
    p.add_argument("--dry-run", action="store_true", help="log intended orders, don't submit")
    p.add_argument("--once", action="store_true", help="run a single cycle and exit")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(args.config)
    if not cfg.api_key or not cfg.api_secret:
        raise SystemExit("CRYPTO_API_KEY / CRYPTO_API_SECRET (or BINANCE_*) must be set")

    if cfg.mode == "live" and not args.dry_run:
        if input("\n*** LIVE crypto trading with REAL MONEY. Type 'I UNDERSTAND': ").strip() != "I UNDERSTAND":
            raise SystemExit("aborted.")

    broker = CcxtBroker(cfg.api_key, cfg.api_secret, exchange=cfg.exchange,
                        sandbox=cfg.sandbox, symbols=cfg.symbols)
    strategy = strategies.create(cfg.strategy_name, **cfg.strategy_params)
    notifier = notifier_from_env()

    def data_fn(symbol: str):
        return fetch_ccxt_ohlcv(symbol, timeframe=cfg.timeframe, limit=cfg.lookback_bars,
                                exchange=cfg.exchange)

    engine = LiveEngine(broker=broker, strategy=strategy, symbols=cfg.symbols,
                        data_fn=data_fn, risk_config=cfg.risk,
                        dry_run=args.dry_run or cfg.mode == "backtest",
                        capital_base=cfg.capital_base)

    logger.info("starting 24/7 crypto engine: %s %s on %s (dry_run=%s)",
                cfg.exchange, cfg.symbols, strategy.name, engine.dry_run)
    notifier.send(f"🤖 크립토 자동매매 시작: {cfg.exchange} {cfg.symbols} / {strategy.name}")

    if args.once:
        engine.run_once()
        return
    try:
        while True:
            engine.run_once()
            time.sleep(cfg.poll_seconds)
    except KeyboardInterrupt:
        logger.info("interrupted; cancelling open orders")
        broker.cancel_all_orders()
        notifier.send("🛑 크립토 자동매매 중지됨")


if __name__ == "__main__":
    main()
