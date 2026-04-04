from __future__ import annotations

import pytest
import yaml
from textual.widgets import TabbedContent

from src.app import MonitorApp
from src.models import Regime


@pytest.fixture
def config_file(tmp_path):
    config = {
        "exchanges": {"deribit": {"enabled": False}, "okx": {"enabled": False}},
        "symbol": "BTC",
        "refresh_interval": 2,
        "rv_windows": [7, 14, 30],
        "regime": {
            "lookback_days": 30,
            "low_z": -0.8,
            "high_z": 0.8,
            "crisis_z": 1.8,
            "history_limit": 120,
        },
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
        await pilot.press("f5")
        assert tabs.active == "regime"
        await pilot.press("f6")
        assert tabs.active == "strategy"
        await pilot.press("f1")
        assert tabs.active == "dashboard"


def test_app_initializes_regime_components_from_config(config_file):
    app = MonitorApp(config_path=config_file)

    assert app._regime_history_limit == 120
    assert app._current_regime is Regime.NORMAL
    assert app._current_zscore == 0.0
    assert app._current_iv_rank == 0.0
    assert app._regime_detector._lookback == 30
    assert app._regime_detector._low_z == -0.8
    assert app._regime_detector._high_z == 0.8
    assert app._regime_detector._crisis_z == 1.8


def test_on_dvol_tracks_bounded_history(config_file):
    app = MonitorApp(config_path=config_file)
    app._regime_history_limit = 3

    app._on_dvol(55.0, None)
    app._on_dvol(60.0, None)
    app._on_dvol(65.0, None)
    app._on_dvol(70.0, None)

    assert app._current_dvol == 70.0
    assert app._dvol_history == [60.0, 65.0, 70.0]
