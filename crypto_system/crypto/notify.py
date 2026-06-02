"""Notifications (Telegram + fallbacks).

A thin :class:`Notifier` interface so the engine/portfolio can announce orders,
fills and rebalances without caring how they're delivered. The Telegram backend
uses only the standard library (urllib) -- no extra dependencies.

Setup (Telegram):
  1. Talk to @BotFather, create a bot, copy the HTTP API token.
  2. Send your bot any message, then read your chat id from
     https://api.telegram.org/bot<TOKEN>/getUpdates  (the ``chat.id`` field),
     or message @userinfobot.
  3. Export TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID; :func:`from_env` picks them
     up automatically. Without them the system falls back to logging.
"""
from __future__ import annotations

import logging
import os
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod

logger = logging.getLogger("trading.notify")


class Notifier(ABC):
    @abstractmethod
    def send(self, message: str) -> None: ...


class NullNotifier(Notifier):
    """Discards messages (used in tests / when notifications are off)."""

    def send(self, message: str) -> None:  # pragma: no cover - trivial
        pass


class LogNotifier(Notifier):
    """Writes notifications to the log -- the no-credentials fallback."""

    def send(self, message: str) -> None:
        logger.info("[notify] %s", message)


class TelegramNotifier(Notifier):
    def __init__(self, token: str, chat_id: str, timeout: float = 10.0):
        if not token or not chat_id:
            raise ValueError("Telegram token and chat_id are required")
        self.token = token
        self.chat_id = chat_id
        self.timeout = timeout

    def send(self, message: str) -> None:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        data = urllib.parse.urlencode(
            {"chat_id": self.chat_id, "text": message, "parse_mode": "HTML"}
        ).encode()
        try:
            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp.read()
        except Exception as exc:  # never let a notification failure break trading
            logger.warning("telegram notify failed: %s", exc)


def from_env() -> Notifier:
    """TelegramNotifier when creds are set, else a LogNotifier."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        return TelegramNotifier(token, chat_id)
    return LogNotifier()
