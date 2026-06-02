#!/usr/bin/env python
"""Backtest a strategy on crypto candles (ccxt or CSV).

    python scripts/backtest.py --symbol BTC/USDT --timeframe 1h --strategy trend_momentum
    python scripts/backtest.py --csv data/BTCUSDT.csv --strategy sma_crossover --params fast=20 slow=50
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from crypto import data as market_data  # noqa: E402
from crypto import strategies  # noqa: E402
from crypto.engine import Backtester  # noqa: E402
from crypto.risk import RiskConfig  # noqa: E402


def _parse_params(items):
    out = {}
    for item in items or []:
        k, v = item.split("=", 1)
        try:
            out[k] = int(v)
        except ValueError:
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = v
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv")
    src.add_argument("--symbol", help="e.g. BTC/USDT")
    p.add_argument("--exchange", default="binance")
    p.add_argument("--timeframe", default="1h")
    p.add_argument("--limit", type=int, default=1000)
    p.add_argument("--strategy", default="trend_momentum", choices=strategies.available())
    p.add_argument("--params", nargs="*")
    p.add_argument("--cash", type=float, default=10_000.0)
    p.add_argument("--commission", type=float, default=0.0)
    p.add_argument("--slippage", type=float, default=0.001)
    p.add_argument("--max-position-pct", type=float, default=1.0)
    p.add_argument("--stop-loss-pct", type=float, default=None)
    p.add_argument("--take-profit-pct", type=float, default=None)
    args = p.parse_args()

    if args.csv:
        df = market_data.load_csv(args.csv); label = args.csv
    else:
        df = market_data.fetch_ccxt_ohlcv(args.symbol, timeframe=args.timeframe,
                                          limit=args.limit, exchange=args.exchange)
        label = f"{args.symbol} {args.timeframe}"

    strat = strategies.create(args.strategy, **_parse_params(args.params))
    risk = RiskConfig(max_position_pct=args.max_position_pct, stop_loss_pct=args.stop_loss_pct,
                      take_profit_pct=args.take_profit_pct, max_daily_loss_pct=None)
    result = Backtester(strat, args.cash, risk, args.commission, args.slippage).run(df)
    m = result.metrics()
    print(f"\n=== Backtest: {strat.name} on {label} ({len(df)} bars) ===")
    print(f"Initial : {result.initial_cash:,.2f}")
    print(f"Final   : {result.final_equity:,.2f}")
    print(f"Return  : {m['total_return']*100:+.2f}%")
    print(f"Sharpe  : {m['sharpe']:.2f}")
    print(f"MaxDD   : {m['max_drawdown']*100:.2f}%")
    print(f"Trades  : {m['num_trades']} (win {m['win_rate']*100:.1f}%)")


if __name__ == "__main__":
    main()
