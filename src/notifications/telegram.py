from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


@dataclass(frozen=True)
class TelegramConfig:
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""


class TelegramNotifier:
    def __init__(self, config: TelegramConfig) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None
        if config.enabled and config.bot_token and config.chat_id:
            self._client = httpx.AsyncClient(timeout=10.0)

    @property
    def enabled(self) -> bool:
        return self._client is not None

    async def send(self, text: str) -> bool:
        if not self._client:
            return False
        url = f"{TELEGRAM_API}/bot{self._config.bot_token}/sendMessage"
        payload = {
            "chat_id": self._config.chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
        try:
            resp = await self._client.post(url, json=payload)
            if resp.status_code == 200:
                return True
            logger.warning("Telegram API error %s: %s", resp.status_code, resp.text)
            return False
        except httpx.HTTPError as e:
            logger.error("Telegram send failed: %s", e)
            return False

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None
