from trading.broker import Account, Position
from trading.report import format_fill, format_report


def test_format_fill_message():
    msg = format_fill("fill", "VTI", "buy", 0.5337, 373.10)
    assert "체결" in msg and "VTI" in msg and "BUY" in msg
    assert "0.5337" in msg and "373.10" in msg


def test_format_partial_fill():
    msg = format_fill("partial_fill", "QQQ", "buy", 0.05, 737.0)
    assert "부분체결" in msg and "QQQ" in msg


def test_report_with_no_positions_shows_pending():
    acct = Account(cash=100_000, equity=100_000, buying_power=200_000)
    msg = format_report(acct, [], pending_orders=8)
    assert "보유 포지션 없음" in msg
    assert "미체결 주문 8건" in msg


def test_report_with_positions_shows_pnl():
    acct = Account(cash=500, equity=1_200, buying_power=1_000)
    positions = [
        Position("VTI", qty=2.0, avg_entry_price=100.0, market_value=220.0, unrealized_pl=20.0),
        Position("GLD", qty=1.0, avg_entry_price=400.0, market_value=380.0, unrealized_pl=-20.0),
    ]
    msg = format_report(acct, positions, pending_orders=0)
    assert "VTI" in msg and "GLD" in msg
    assert "🟢" in msg and "🔴" in msg
    # Net P&L = +20 - 20 = 0 on cost 600 -> 0.00%
    assert "총 평가손익 $+0.00" in msg
