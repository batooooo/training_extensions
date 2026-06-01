import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def trending_data() -> pd.DataFrame:
    """A clean uptrend then downtrend -- exercises crossovers."""
    up = np.linspace(100, 200, 120)
    down = np.linspace(200, 120, 120)
    close = np.concatenate([up, down])
    idx = pd.bdate_range("2022-01-01", periods=len(close))
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.01,
            "low": close * 0.99,
            "close": close,
            "volume": 1_000_000,
        },
        index=idx,
    )


@pytest.fixture
def random_walk() -> pd.DataFrame:
    rng = np.random.default_rng(0)
    rets = rng.normal(0.0003, 0.012, size=400)
    close = 100 * np.exp(np.cumsum(rets))
    idx = pd.bdate_range("2021-01-01", periods=len(close))
    return pd.DataFrame(
        {
            "open": close,
            "high": close * 1.005,
            "low": close * 0.995,
            "close": close,
            "volume": 1_000_000,
        },
        index=idx,
    )
