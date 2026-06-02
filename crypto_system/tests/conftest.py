import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def crypto_uptrend() -> pd.DataFrame:
    up = np.linspace(20000, 40000, 150)
    down = np.linspace(40000, 30000, 100)
    close = np.concatenate([up, down])
    idx = pd.date_range("2026-01-01", periods=len(close), freq="h")
    return pd.DataFrame(
        {"open": close, "high": close * 1.02, "low": close * 0.98,
         "close": close, "volume": 1000.0}, index=idx)
