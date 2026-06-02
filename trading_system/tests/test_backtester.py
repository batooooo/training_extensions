from trading import strategies
from trading.engine import Backtester
from trading.risk import RiskConfig


def test_backtest_runs_and_reports(random_walk):
    strat = strategies.create("sma_crossover", fast=10, slow=30)
    bt = Backtester(strat, initial_cash=100_000.0,
                    risk_config=RiskConfig(max_position_pct=1.0, stop_loss_pct=None,
                                           take_profit_pct=None, max_daily_loss_pct=None))
    result = bt.run(random_walk)
    m = result.metrics()
    assert len(result.equity_curve) == len(random_walk)
    assert m["num_trades"] >= 0
    assert 0.0 <= m["win_rate"] <= 1.0
    # Equity should never go negative.
    assert (result.equity_curve > 0).all()


def test_stop_loss_caps_losses(trending_data):
    # Buy-and-hold style strategy on a series that trends up then crashes.
    strat = strategies.create("sma_crossover", fast=5, slow=20)
    no_stop = Backtester(strat, risk_config=RiskConfig(
        max_position_pct=1.0, stop_loss_pct=None, take_profit_pct=None,
        max_daily_loss_pct=None)).run(trending_data)
    with_stop = Backtester(strat, risk_config=RiskConfig(
        max_position_pct=1.0, stop_loss_pct=0.03, take_profit_pct=None,
        max_daily_loss_pct=None)).run(trending_data)
    # A tight stop should not produce a worse drawdown than no stop.
    assert with_stop.metrics()["max_drawdown"] >= no_stop.metrics()["max_drawdown"] - 1e-9


def test_no_lookahead_first_bar_flat(random_walk):
    strat = strategies.create("macd")
    bt = Backtester(strat)
    result = bt.run(random_walk)
    # First equity point equals initial cash (signal is shifted, no instant trade).
    assert abs(result.equity_curve.iloc[0] - result.initial_cash) < 1e-6
