from __future__ import annotations

import os
import tempfile

import pytest
import yaml
from textual.widgets import TabbedContent

from src.app import MonitorApp


@pytest.fixture
def config_file(tmp_path):
    config = {
        "exchanges": {"deribit": {"enabled": False}, "okx": {"enabled": False}},
        "symbol": "BTC",
        "refresh_interval": 2,
        "rv_windows": [7, 14, 30],
        "alerts": {
            "iv_rv_ratio_high": 1.5,
            "iv_rv_ratio_low": 0.5,
            "cross_exchange_iv_diff": 0.05,
            "cooldown_min": 5,
            "iv_spike_pct": 0.20,
            "iv_spike_window_min": 30,
            "telegram": {"enabled": False, "bot_token": "", "chat_id": ""},
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.dump(config))
    return str(path)


async def test_app_mounts(config_file):
    app = MonitorApp(config_path=config_file)
    async with app.run_test() as pilot:
        assert pilot.app is not None


async def test_app_tab_switch(config_file):
    app = MonitorApp(config_path=config_file)
    async with app.run_test() as pilot:
        tabs = pilot.app.query_one(TabbedContent)
        assert tabs.active == "dashboard"
        await pilot.press("f2")
        assert tabs.active == "smile"
        await pilot.press("f3")
        assert tabs.active == "term"
        await pilot.press("f4")
        assert tabs.active == "alerts"
        await pilot.press("f1")
        assert tabs.active == "dashboard"
