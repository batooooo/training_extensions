"""Portfolio reporting -- a phone-friendly snapshot for Telegram.

Pure formatting lives here (and is unit-tested); the script in
``scripts/report.py`` wires it to the live broker and the notifier.
"""
from __future__ import annotations

from .broker import Account, Position


def format_fill(
    event: str, symbol: str, side: str, qty: float, price: float
) -> str:
    """One-line, phone-friendly fill notification for the trade-update stream."""
    icon = {"fill": "✅", "partial_fill": "📥"}.get(event, "ℹ️")
    label = {"fill": "체결", "partial_fill": "부분체결"}.get(event, event)
    value = qty * price
    return (
        f"{icon} {label}! {side.upper()} {symbol} "
        f"{qty:.4f}주 @ ${price:,.2f}  (${value:,.2f})"
    )


def format_report(
    account: Account,
    positions: list[Position],
    pending_orders: int = 0,
    title: str = "Portfolio report",
) -> str:
    """Build a compact, emoji-tagged report string."""
    lines = [f"📈 {title}"]
    lines.append(f"평가액 ${account.equity:,.2f} | 현금 ${account.cash:,.2f}")

    if positions:
        lines.append("")
        lines.append("보유 종목:")
        total_cost = 0.0
        total_value = 0.0
        for p in sorted(positions, key=lambda x: -x.market_value):
            cost = p.qty * p.avg_entry_price
            total_cost += cost
            total_value += p.market_value
            pct = (p.unrealized_pl / cost * 100) if cost else 0.0
            mark = "🟢" if p.unrealized_pl >= 0 else "🔴"
            lines.append(
                f"  {p.symbol} {p.qty:.4f}주 ${p.market_value:,.2f} "
                f"({pct:+.2f}% {mark})"
            )
        total_pl = total_value - total_cost
        total_pct = (total_pl / total_cost * 100) if total_cost else 0.0
        mark = "🟢" if total_pl >= 0 else "🔴"
        lines.append(f"총 평가손익 ${total_pl:+,.2f} ({total_pct:+.2f}% {mark})")
    else:
        lines.append("")
        lines.append("보유 포지션 없음 (아직 체결 전)")

    if pending_orders:
        lines.append(f"⏳ 미체결 주문 {pending_orders}건 (개장 시 체결 예정)")

    return "\n".join(lines)
