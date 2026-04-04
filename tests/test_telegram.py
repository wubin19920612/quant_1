from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from src.notifications.telegram import TelegramConfig, TelegramNotifier


@pytest.fixture
def enabled_config():
    return TelegramConfig(enabled=True, bot_token="123:ABC", chat_id="456")


@pytest.fixture
def disabled_config():
    return TelegramConfig(enabled=False, bot_token="", chat_id="")


async def test_disabled_notifier_noop(disabled_config):
    notifier = TelegramNotifier(disabled_config)
    assert not notifier.enabled
    result = await notifier.send("test")
    assert result is False


async def test_send_success(enabled_config):
    notifier = TelegramNotifier(enabled_config)
    mock_resp = AsyncMock()
    mock_resp.status_code = 200
    with patch.object(notifier._client, "post", return_value=mock_resp) as mock_post:
        result = await notifier.send("Alert: IV spike!")
        assert result is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert "123:ABC" in call_kwargs.args[0]
        assert call_kwargs.kwargs["json"]["chat_id"] == "456"
    await notifier.close()


async def test_send_api_error(enabled_config):
    notifier = TelegramNotifier(enabled_config)
    mock_resp = AsyncMock()
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request"
    with patch.object(notifier._client, "post", return_value=mock_resp):
        result = await notifier.send("Alert: IV spike!")
        assert result is False
    await notifier.close()


async def test_send_network_error(enabled_config):
    notifier = TelegramNotifier(enabled_config)
    with patch.object(
        notifier._client, "post", side_effect=httpx.ConnectError("Connection refused")
    ):
        result = await notifier.send("Alert: IV spike!")
        assert result is False
    await notifier.close()
