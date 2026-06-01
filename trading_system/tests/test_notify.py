import pandas as pd

from trading.broker import SimulatedBroker
from trading.notify import LogNotifier, Notifier, TelegramNotifier, from_env
from trading.portfolio import PortfolioManager


class RecordingNotifier(Notifier):
    def __init__(self):
        self.messages = []

    def send(self, message: str) -> None:
        self.messages.append(message)


def test_from_env_falls_back_to_log(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    assert isinstance(from_env(), LogNotifier)


def test_from_env_uses_telegram_when_configured(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    assert isinstance(from_env(), TelegramNotifier)


def test_telegram_send_never_raises_on_failure():
    # Bogus token/host -> the send must swallow the error, not crash trading.
    TelegramNotifier("bad", "0", timeout=0.01).send("hi")  # no exception


def test_portfolio_rebalance_notifies_summary():
    broker = SimulatedBroker(cash=10_000)
    broker.set_price("VTI", 100.0)
    broker.set_price("GLD", 50.0)
    note = RecordingNotifier()
    pm = PortfolioManager(broker, {"VTI": 0.5, "GLD": 0.5}, capital_base=1000.0,
                          dry_run=False, notifier=note)
    pm.rebalance()
    assert len(note.messages) == 1
    msg = note.messages[0]
    assert "Rebalance" in msg and "VTI" in msg and "GLD" in msg


def test_portfolio_notifies_when_no_trades():
    broker = SimulatedBroker(cash=10_000)
    broker.set_price("VTI", 100.0)
    note = RecordingNotifier()
    pm = PortfolioManager(broker, {"VTI": 0.0}, capital_base=1000.0,
                          dry_run=False, notifier=note)
    pm.rebalance()
    assert "no trades" in note.messages[0]
