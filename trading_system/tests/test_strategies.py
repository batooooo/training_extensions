import pandas as pd
import pytest

from trading import strategies
from trading.strategies import Signal


def test_registry_roundtrip():
    for name in strategies.available():
        strat = strategies.create(name)
        assert strat.name == name


def test_unknown_strategy_raises():
    with pytest.raises(KeyError):
        strategies.create("does_not_exist")


def test_sma_validates_windows():
    with pytest.raises(ValueError):
        strategies.create("sma_crossover", fast=50, slow=20)


def test_signals_aligned_and_valid(trending_data):
    for name in strategies.available():
        strat = strategies.create(name)
        sig = strat.generate_signals(trending_data)
        assert len(sig) == len(trending_data)
        assert set(sig.unique()).issubset({-1, 0, 1})


def test_sma_crossover_buys_in_uptrend(trending_data):
    strat = strategies.create("sma_crossover", fast=10, slow=30)
    sig = strat.generate_signals(trending_data)
    # During the first (uptrend) half it should be long at some point.
    first_half = sig.iloc[: len(sig) // 2]
    assert (first_half == Signal.BUY).any()


def test_latest_signal_on_empty():
    strat = strategies.create("macd")
    empty = pd.DataFrame({"close": []})
    assert strat.latest_signal(empty) is Signal.HOLD
