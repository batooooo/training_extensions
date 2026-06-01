#!/usr/bin/env python
"""Verify Alpaca connectivity before running the engine.

Run this once you have set ALPACA_API_KEY / ALPACA_API_SECRET in the
environment. It checks, in order:
  1. credentials are present;
  2. the trading account is reachable (and whether the market is open);
  3. historical bars can be fetched;
  4. a latest quote can be pulled.

It NEVER submits an order. Paper trading is assumed unless --live is passed.

    python scripts/check_connection.py --symbol AAPL
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--symbol", default="AAPL", help="symbol to probe")
    p.add_argument("--live", action="store_true", help="check the LIVE endpoint instead of paper")
    args = p.parse_args()

    key = os.getenv("ALPACA_API_KEY")
    secret = os.getenv("ALPACA_API_SECRET")
    if not key or not secret:
        print("FAIL: ALPACA_API_KEY / ALPACA_API_SECRET are not set in the environment.")
        print("      export them (or put them in .env and source it), then re-run.")
        return 1

    paper = not args.live
    print(f"[1/4] credentials present (key ...{key[-4:]}), mode={'PAPER' if paper else 'LIVE'}")

    from trading.broker import AlpacaBroker
    from trading.data import fetch_alpaca_bars

    try:
        broker = AlpacaBroker(key, secret, paper=paper)
        acct = broker.get_account()
        print(f"[2/4] account OK: equity={acct.equity:,.2f} cash={acct.cash:,.2f} "
              f"buying_power={acct.buying_power:,.2f} | market_open={broker.is_market_open()}")
    except Exception as exc:
        print(f"FAIL at account check: {exc}")
        return 1

    try:
        bars = fetch_alpaca_bars(args.symbol, start="2024-01-01", timeframe="1Day",
                                 api_key=key, api_secret=secret)
        last = bars.iloc[-1]
        print(f"[3/4] history OK: {len(bars)} daily bars for {args.symbol}, "
              f"last close={last['close']:.2f} on {bars.index[-1].date()}")
    except Exception as exc:
        print(f"FAIL at history fetch: {exc}")
        return 1

    try:
        price = broker.get_last_price(args.symbol)
        print(f"[4/4] live quote OK: {args.symbol} last trade={price:.2f}")
    except Exception as exc:
        # Real-time quotes can require a data subscription; not fatal for trading.
        print(f"WARN: latest-quote check failed ({exc}). Historical data still works.")

    print("\nAll core checks passed. You can now run:")
    print("  python scripts/run_live.py --config config.yaml --dry-run --once")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
