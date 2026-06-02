#!/usr/bin/env python
"""Send a crypto portfolio snapshot (holdings, value) to Telegram.

    python scripts/report.py --config config.yaml
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crypto.broker import CcxtBroker  # noqa: E402
from crypto.config import load_config  # noqa: E402
from crypto.notify import from_env as notifier_from_env  # noqa: E402
from crypto.report import format_report  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True)
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    cfg = load_config(args.config)
    if not cfg.api_key or not cfg.api_secret:
        raise SystemExit("CRYPTO_API_KEY / CRYPTO_API_SECRET (or BINANCE_*) must be set")

    broker = CcxtBroker(cfg.api_key, cfg.api_secret, exchange=cfg.exchange,
                        sandbox=cfg.sandbox, symbols=cfg.symbols)
    account = broker.get_account()
    positions = broker.get_positions()
    stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    msg = format_report(account, positions, 0, title=f"Crypto report {stamp}")
    print(msg)
    notifier_from_env().send(msg)


if __name__ == "__main__":
    main()
