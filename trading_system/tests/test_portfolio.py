import pandas as pd

from trading.broker import Order, OrderSide, SimulatedBroker
from trading.portfolio import PortfolioManager, plan_rebalance
from trading.strategies import Signal, Strategy


def test_plan_rebalance_buys_to_targets_from_cash():
    orders = plan_rebalance(
        targets={"VTI": 0.5, "QQQ": 0.5},
        capital=1000.0,
        prices={"VTI": 200.0, "QQQ": 100.0},
        positions={},
    )
    by_sym = {o.symbol: o for o in orders}
    assert by_sym["VTI"].side is OrderSide.BUY and by_sym["VTI"].notional == 500.0
    assert by_sym["QQQ"].side is OrderSide.BUY and by_sym["QQQ"].notional == 500.0


def test_plan_rebalance_sells_overweight():
    # Hold 10 VTI ($2000) but target is $500 -> sell ~7.5 shares.
    orders = plan_rebalance(
        targets={"VTI": 0.5},
        capital=1000.0,
        prices={"VTI": 200.0},
        positions={"VTI": 10.0},
    )
    assert len(orders) == 1
    o = orders[0]
    assert o.side is OrderSide.SELL and abs(o.qty - 7.5) < 1e-9


def test_notional_order_fills_fractionally_in_sim_broker():
    b = SimulatedBroker(cash=1000)
    b.set_price("VTI", 400.0)
    b.submit_order(Order("VTI", qty=0.0, side=OrderSide.BUY, notional=100.0))
    pos = b.get_position("VTI")
    assert abs(pos.qty - 0.25) < 1e-9  # $100 / $400
    assert abs(b.get_account().cash - 900.0) < 1e-9


class _RegimeStub(Strategy):
    name = "stub"

    def __init__(self, signal):
        super().__init__()
        self._signal = signal

    def generate_signals(self, data):
        return pd.Series(self._signal, index=data.index, dtype=int)


def test_regime_gate_sends_downtrend_sleeve_to_cash():
    b = SimulatedBroker(cash=1000)
    b.set_price("VTI", 100.0)
    # Strategy says SELL -> target weight forced to 0, no buy happens.
    pm = PortfolioManager(b, {"VTI": 1.0}, capital_base=1000.0,
                          strategy=_RegimeStub(Signal.SELL), dry_run=False)
    df = pd.DataFrame({"close": [100, 100, 100]})
    orders = pm.rebalance(data_fn=lambda s: df)
    assert orders == []
    assert b.get_position("VTI") is None


def test_too_large_weights_rejected():
    import pytest
    with pytest.raises(ValueError):
        PortfolioManager(SimulatedBroker(), {"A": 0.7, "B": 0.7}, 1000.0)
