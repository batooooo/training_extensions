import pandas as pd

from trading.broker import OrderSide, SimulatedBroker
from trading.engine import LiveEngine
from trading.risk import RiskConfig, RiskManager
from trading.strategies import Signal, Strategy


def test_position_size_respects_cap():
    rm = RiskManager(RiskConfig(max_position_pct=0.1))
    # 10% of 100k = 10k budget, price 100 -> 100 shares
    assert rm.position_size(100_000, 100) == 100


def test_position_size_respects_notional_cap():
    # 10% of 100k = 10k budget, but notional cap of 720 binds first.
    rm = RiskManager(RiskConfig(max_position_pct=0.1, max_position_notional=720))
    assert rm.position_size(100_000, 311) == 2   # 720 // 311 = 2 shares


def test_daily_loss_kill_switch():
    rm = RiskManager(RiskConfig(max_daily_loss_pct=0.05))
    rm.start_day(100_000)
    assert rm.check_daily_loss(98_000) is True   # -2%, ok
    assert rm.check_daily_loss(94_000) is False  # -6%, halt
    assert rm.halted is True


def test_stop_and_take_profit():
    rm = RiskManager(RiskConfig(stop_loss_pct=0.05, take_profit_pct=0.10))
    assert rm.should_exit(100, 94) == "stop_loss"
    assert rm.should_exit(100, 111) == "take_profit"
    assert rm.should_exit(100, 102) is None


def test_simulated_broker_buy_sell():
    b = SimulatedBroker(cash=10_000)
    b.set_price("AAPL", 100)
    from trading.broker import Order

    b.submit_order(Order("AAPL", 10, OrderSide.BUY))
    assert b.get_position("AAPL").qty == 10
    assert b.get_account().cash == 9_000
    b.submit_order(Order("AAPL", 10, OrderSide.SELL))
    assert b.get_position("AAPL") is None
    assert b.get_account().cash == 10_000


class _AlwaysBuy(Strategy):
    name = "always_buy"

    def generate_signals(self, data):
        return pd.Series(Signal.BUY, index=data.index, dtype=int)


def test_live_engine_buys_through_broker():
    broker = SimulatedBroker(cash=10_000)
    broker.set_price("AAPL", 100)
    df = pd.DataFrame({"close": [100, 100, 100]})  # last close == broker price

    engine = LiveEngine(
        broker=broker,
        strategy=_AlwaysBuy(),
        symbols=["AAPL"],
        data_fn=lambda s: df,
        risk_config=RiskConfig(max_position_pct=0.5),
        dry_run=False,
    )
    engine.run_once()
    pos = broker.get_position("AAPL")
    assert pos is not None and pos.qty == 50  # 50% of 10k / 100


def test_live_engine_uses_capital_base_for_sizing():
    # Account holds 100k but capital_base says trade as if we have ~$663.
    broker = SimulatedBroker(cash=100_000)
    broker.set_price("AAPL", 100)
    df = pd.DataFrame({"close": [100, 100, 100]})
    engine = LiveEngine(
        broker=broker,
        strategy=_AlwaysBuy(),
        symbols=["AAPL"],
        data_fn=lambda s: df,
        risk_config=RiskConfig(max_position_pct=1.0),
        dry_run=False,
        capital_base=663.65,
    )
    engine.run_once()
    pos = broker.get_position("AAPL")
    assert pos is not None and pos.qty == 6  # 663.65 // 100, not 1000 (full equity)


def test_live_engine_dry_run_submits_nothing():
    broker = SimulatedBroker(cash=10_000)
    broker.set_price("AAPL", 100)
    df = pd.DataFrame({"close": [100, 101, 102]})
    engine = LiveEngine(broker, _AlwaysBuy(), ["AAPL"], lambda s: df, dry_run=True)
    engine.run_once()
    assert broker.get_position("AAPL") is None
