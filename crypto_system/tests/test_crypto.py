import pandas as pd

from crypto import strategies
from crypto.broker import Order, OrderSide, SimulatedBroker
from crypto.engine import Backtester, LiveEngine
from crypto.portfolio import plan_rebalance
from crypto.risk import RiskConfig
from crypto.strategies import Signal, Strategy


def test_strategies_available():
    assert "trend_momentum" in strategies.available()
    for name in strategies.available():
        assert strategies.create(name).name == name


def test_backtest_runs_on_crypto(crypto_uptrend):
    strat = strategies.create("sma_crossover", fast=10, slow=30)
    risk = RiskConfig(max_position_pct=1.0, stop_loss_pct=None,
                      take_profit_pct=None, max_daily_loss_pct=None)
    result = Backtester(strat, 10_000, risk, slippage_pct=0.001).run(crypto_uptrend)
    m = result.metrics()
    assert len(result.equity_curve) == len(crypto_uptrend)
    assert (result.equity_curve > 0).all()
    assert m["num_trades"] >= 1


def test_notional_order_buys_fractional_crypto():
    b = SimulatedBroker(cash=1000)
    b.set_price("BTC/USDT", 40000.0)
    b.submit_order(Order("BTC/USDT", qty=0.0, side=OrderSide.BUY, notional=200.0))
    pos = b.get_position("BTC/USDT")
    assert abs(pos.qty - 0.005) < 1e-9     # $200 / $40,000
    assert abs(b.get_account().cash - 800.0) < 1e-9


class _AlwaysBuy(Strategy):
    name = "always_buy"

    def generate_signals(self, data):
        return pd.Series(Signal.BUY, index=data.index, dtype=int)


def test_live_engine_capital_base_buys_fractional_crypto():
    b = SimulatedBroker(cash=100_000)
    b.set_price("ETH/USDT", 2000.0)
    df = pd.DataFrame({"close": [2000, 2000, 2000]})
    eng = LiveEngine(b, _AlwaysBuy(), ["ETH/USDT"], data_fn=lambda s: df,
                     risk_config=RiskConfig(max_position_pct=1.0),
                     dry_run=False, capital_base=300.0)
    eng.run_once()
    pos = b.get_position("ETH/USDT")
    # notional $300 budget / $2000 -> 0.15 ETH (fractional, not 0)
    assert pos is not None and abs(pos.qty - 0.15) < 1e-9


def test_plan_rebalance_crypto_weights():
    orders = plan_rebalance({"BTC/USDT": 0.5, "ETH/USDT": 0.5}, capital=300.0,
                            prices={"BTC/USDT": 40000.0, "ETH/USDT": 2000.0}, positions={})
    by = {o.symbol: o for o in orders}
    assert by["BTC/USDT"].notional == 150.0 and by["ETH/USDT"].notional == 150.0
