#!/usr/bin/env python
"""Backtest a strategy over historical data.

Examples:
    # From a CSV of OHLCV bars:
    python scripts/backtest.py --csv data/AAPL.csv --strategy sma_crossover \
        --params fast=20 slow=50

    # Pulling history from Alpaca (needs ALPACA_API_KEY / ALPACA_API_SECRET):
    python scripts/backtest.py --symbol AAPL --start 2022-01-01 \
        --strategy rsi_reversion
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running the script directly without installing the package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from trading import data as market_data  # noqa: E402
from trading import strategies  # noqa: E402
from trading.engine import Backtester  # noqa: E402
from trading.risk import RiskConfig  # noqa: E402


def _parse_params(items: list[str]) -> dict:
    """Turn ['fast=20', 'slow=50'] into {'fast': 20, 'slow': 50}."""
    out: dict = {}
    for item in items or []:
        if "=" not in item:
            raise SystemExit(f"bad --params entry {item!r}; expected key=value")
        key, val = item.split("=", 1)
        try:
            out[key] = int(val)
        except ValueError:
            try:
                out[key] = float(val)
            except ValueError:
                out[key] = val
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--csv", help="path to OHLCV CSV file")
    src.add_argument("--symbol", help="symbol to fetch from Alpaca")
    p.add_argument("--start", default="2022-01-01", help="start date for Alpaca fetch")
    p.add_argument("--end", default=None, help="end date for Alpaca fetch")
    p.add_argument("--timeframe", default="1Day")
    p.add_argument("--strategy", default="sma_crossover", choices=strategies.available())
    p.add_argument("--params", nargs="*", help="strategy params as key=value")
    p.add_argument("--cash", type=float, default=100_000.0)
    p.add_argument("--commission", type=float, default=0.0)
    p.add_argument("--slippage", type=float, default=0.0005)
    p.add_argument("--max-position-pct", type=float, default=1.0)
    p.add_argument("--stop-loss-pct", type=float, default=None)
    p.add_argument("--take-profit-pct", type=float, default=None)
    p.add_argument("--save-equity", help="write the equity curve to this CSV path")
    args = p.parse_args()

    if args.csv:
        df = market_data.load_csv(args.csv)
        label = args.csv
    else:
        df = market_data.fetch_alpaca_bars(args.symbol, args.start, args.end, args.timeframe)
        label = args.symbol

    strategy = strategies.create(args.strategy, **_parse_params(args.params))
    risk = RiskConfig(
        max_position_pct=args.max_position_pct,
        stop_loss_pct=args.stop_loss_pct,
        take_profit_pct=args.take_profit_pct,
        max_daily_loss_pct=None,  # daily limit is for intraday live trading
    )
    bt = Backtester(strategy, args.cash, risk, args.commission, args.slippage)
    result = bt.run(df)
    m = result.metrics()

    print(f"\n=== Backtest: {strategy.name} on {label} ({len(df)} bars) ===")
    print(f"Initial cash : {result.initial_cash:,.2f}")
    print(f"Final equity : {result.final_equity:,.2f}")
    print(f"Total return : {m['total_return'] * 100:+.2f}%")
    print(f"Sharpe       : {m['sharpe']:.2f}")
    print(f"Max drawdown : {m['max_drawdown'] * 100:.2f}%")
    print(f"Trades       : {m['num_trades']}  (win rate {m['win_rate'] * 100:.1f}%)")

    if args.save_equity:
        result.equity_curve.to_csv(args.save_equity)
        print(f"equity curve saved to {args.save_equity}")


if __name__ == "__main__":
    main()
