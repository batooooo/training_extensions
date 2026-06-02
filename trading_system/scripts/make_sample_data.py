#!/usr/bin/env python
"""Generate a synthetic OHLCV CSV so you can try the backtester without any API.

    python scripts/make_sample_data.py --out data/SAMPLE.csv --days 500

The series is a geometric random walk with mild trend + noise -- enough to make
the strategies produce trades. It is NOT real market data.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default="data/SAMPLE.csv")
    p.add_argument("--days", type=int, default=500)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--start-price", type=float, default=100.0)
    args = p.parse_args()

    rng = np.random.default_rng(args.seed)
    dates = pd.bdate_range("2021-01-01", periods=args.days)
    # small positive drift + daily noise
    returns = rng.normal(0.0004, 0.015, size=args.days)
    close = args.start_price * np.exp(np.cumsum(returns))

    open_ = close * (1 + rng.normal(0, 0.003, size=args.days))
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.004, size=args.days)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.004, size=args.days)))
    volume = rng.integers(1_000_000, 5_000_000, size=args.days)

    df = pd.DataFrame(
        {"timestamp": dates, "open": open_, "high": high, "low": low,
         "close": close, "volume": volume}
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out, index=False)
    print(f"wrote {len(df)} rows to {out}")


if __name__ == "__main__":
    main()
