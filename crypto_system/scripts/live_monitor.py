#!/usr/bin/env python
"""Live crypto monitor -- a refreshing table of prices + strategy signals.

View-only (never trades). Polls the exchange every --interval seconds and shows,
for each symbol: current price, 24h change, and what the strategy says to do
right now (hold / cash). Runs anywhere the exchange is reachable.

    python scripts/live_monitor.py --config config.yaml
    python scripts/live_monitor.py --symbols BTC/USDT ETH/USDT --interval 5
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crypto import strategies  # noqa: E402
from crypto.data import fetch_ccxt_ohlcv  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", help="read exchange/symbols/strategy/timeframe from a config YAML")
    p.add_argument("--exchange", default="binance")
    p.add_argument("--symbols", nargs="*", default=["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    p.add_argument("--timeframe", default="1d")
    p.add_argument("--strategy", default="trend_momentum")
    p.add_argument("--interval", type=float, default=10.0, help="refresh seconds")
    args = p.parse_args()

    exchange, symbols, timeframe, strat_name = args.exchange, args.symbols, args.timeframe, args.strategy
    if args.config:
        import yaml
        cfg = yaml.safe_load(open(args.config))
        exchange = cfg.get("exchange", exchange)
        symbols = list(cfg.get("targets") or cfg.get("symbols") or symbols)
        timeframe = (cfg.get("data") or {}).get("timeframe", timeframe)
        strat_name = (cfg.get("strategy") or {}).get("name") or cfg.get("regime_strategy") or strat_name

    strat = strategies.create(strat_name)
    print(f"live monitor: {exchange} {symbols} [{strat_name}] every {args.interval}s (Ctrl-C to stop)\n")
    try:
        while True:
            print(f"=== {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
            print(f"{'SYMBOL':<12}{'PRICE':>14}{'CHG':>8}{'SIGNAL':>10}")
            for sym in symbols:
                try:
                    df = fetch_ccxt_ohlcv(sym, timeframe=timeframe, limit=300, exchange=exchange)
                    price = df["close"].iloc[-1]
                    chg = (df["close"].iloc[-1] / df["close"].iloc[-2] - 1) * 100
                    sig = strat.latest_signal(df).name
                    tag = "HOLD" if sig == "BUY" else "cash"
                    print(f"{sym:<12}{price:>14,.4f}{chg:>+7.1f}%{tag:>10}")
                except Exception as exc:
                    print(f"{sym:<12}  error: {str(exc)[:40]}")
                time.sleep(0.2)
            print()
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("stopped.")


if __name__ == "__main__":
    main()
