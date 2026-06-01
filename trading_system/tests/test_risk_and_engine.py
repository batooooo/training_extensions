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


def test_volatility_position_size_risks_fixed_amount():
    # Risk 1% of 100k = $1,000 per trade; stop = 2*ATR = 2*5 = $10 -> 100 shares.
    rm = RiskManager(RiskConfig(max_position_pct=1.0, risk_per_trade_pct=0.01,
                                atr_stop_multiple=2.0))
    assert rm.volatility_position_size(100_000, price=50, atr=5.0) == 100


def test_volatility_size_caps_at_budget():
    # Tiny stop would imply a huge position, but the cash budget caps it.
    rm = RiskManager(RiskConfig(max_position_pct=0.1, risk_per_trade_pct=0.01,
                                atr_stop_multiple=2.0))
    # risk_capital=1000, stop=0.2 -> 5000 shares uncapped; budget 10k/50=200 shares.
    assert rm.volatility_position_size(100_000, price=50, atr=0.1) == 200


def test_volatility_size_falls_back_without_atr():
    rm = RiskManager(RiskConfig(max_position_pct=0.1, risk_per_trade_pct=0.01))
    # No ATR -> behaves like plain percent sizing: 10k budget / 50 = 200.
    assert rm.volatility_position_size(100_000, price=50, atr=None) == 200


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


def test_stream_engine_acts_on_streamed_bar():
    import asyncio
    from types import SimpleNamespace

    import numpy as np

    from trading.engine import StreamEngine

    close = np.linspace(100, 130, 60)
    idx = pd.bdate_range("2026-01-01", periods=60)
    hist = pd.DataFrame(
        {"open": close, "high": close * 1.01, "low": close * 0.99,
         "close": close, "volume": 1e6}, index=idx)

    broker = SimulatedBroker(cash=100_000)
    broker.set_price("AAPL", 131)
    eng = StreamEngine(
        broker, _AlwaysBuy(), ["AAPL"], history_fn=lambda s: hist,
        api_key="k", api_secret="s",
        risk_config=RiskConfig(max_position_pct=1.0), capital_base=663.65,
        dry_run=False,
    )
    eng._seed_history()
    bar = SimpleNamespace(symbol="AAPL", timestamp=idx[-1] + pd.Timedelta(days=1),
                          open=131, high=132, low=130, close=131, volume=1e6)
    asyncio.run(eng._on_bar(bar))
    pos = broker.get_position("AAPL")
    assert pos is not None and pos.qty == 5  # 663.65 // 131


def test_live_engine_dry_run_submits_nothing():
    broker = SimulatedBroker(cash=10_000)
    broker.set_price("AAPL", 100)
    df = pd.DataFrame({"close": [100, 101, 102]})
    engine = LiveEngine(broker, _AlwaysBuy(), ["AAPL"], lambda s: df, dry_run=True)
    engine.run_once()
    assert broker.get_position("AAPL") is None
