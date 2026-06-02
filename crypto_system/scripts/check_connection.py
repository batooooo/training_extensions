#!/usr/bin/env python
"""Verify ccxt/exchange connectivity before running the engine. Never trades.

    python scripts/check_connection.py --config config.yaml
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crypto.config import load_config  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--config", required=True)
    args = p.parse_args()
    cfg = load_config(args.config)

    if not cfg.api_key or not cfg.api_secret:
        print("FAIL: CRYPTO_API_KEY / CRYPTO_API_SECRET (or BINANCE_*) not set.")
        return 1
    print(f"[1/3] credentials present, exchange={cfg.exchange}, "
          f"mode={'TESTNET' if cfg.sandbox else 'LIVE'}")

    from crypto.broker import CcxtBroker
    from crypto.data import fetch_ccxt_ohlcv
    try:
        broker = CcxtBroker(cfg.api_key, cfg.api_secret, exchange=cfg.exchange,
                            sandbox=cfg.sandbox, symbols=cfg.symbols)
        acct = broker.get_account()
        print(f"[2/3] account OK: cash={acct.cash:,.2f} equity={acct.equity:,.2f}")
    except Exception as exc:
        print(f"FAIL at account check: {exc}")
        return 1
    try:
        sym = cfg.symbols[0]
        bars = fetch_ccxt_ohlcv(sym, timeframe=cfg.timeframe, limit=10, exchange=cfg.exchange)
        print(f"[3/3] market data OK: {sym} last close={bars['close'].iloc[-1]:,.2f}")
    except Exception as exc:
        print(f"FAIL at market data: {exc}")
        return 1
    print("\nAll checks passed. Try: python scripts/run_24_7.py --config config.yaml --dry-run --once")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
