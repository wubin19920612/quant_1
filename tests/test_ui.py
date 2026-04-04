from __future__ import annotations

from datetime import datetime, timezone

import pytest
from textual.app import App, ComposeResult

from src.models import AlertEvent, Signal
from src.ui.dashboard import DashboardPanel
from src.ui.alert_log import AlertLogPanel

try:
    from src.ui.vol_smile import VolSmilePanel
    from src.ui.term_structure import TermStructurePanel
    HAS_PLOTEXT = True
except ImportError:
    HAS_PLOTEXT = False


class DashboardApp(App):
    def compose(self) -> ComposeResult:
        yield DashboardPanel(id="panel")


class AlertLogApp(App):
    def compose(self) -> ComposeResult:
        yield AlertLogPanel(id="panel")


class VolSmileApp(App):
    def compose(self) -> ComposeResult:
        yield VolSmilePanel(id="panel")


class TermStructureApp(App):
    def compose(self) -> ComposeResult:
        yield TermStructurePanel(id="panel")


async def test_dashboard_panel_mount():
    async with DashboardApp().run_test() as pilot:
        panel = pilot.app.query_one(DashboardPanel)
        assert panel is not None


async def test_dashboard_panel_update_data():
    async with DashboardApp().run_test() as pilot:
        panel = pilot.app.query_one(DashboardPanel)
        rows = [
            {
                "exchange": "deribit", "expiry": "28Mar25", "strike": 80000,
                "option_type": "call", "iv": 65.0, "rv_7d": 50.0,
                "rv_14d": 52.0, "rv_30d": 55.0, "ratio": 1.25,
                "signal": Signal.WEAK_BUY,
            }
        ]
        panel.update_data(rows)


async def test_alert_log_panel_mount():
    async with AlertLogApp().run_test() as pilot:
        panel = pilot.app.query_one(AlertLogPanel)
        assert panel is not None


async def test_alert_log_panel_add_alert():
    async with AlertLogApp().run_test() as pilot:
        panel = pilot.app.query_one(AlertLogPanel)
        alert = AlertEvent(
            timestamp=datetime.now(timezone.utc),
            level="high",
            rule="iv_spike",
            instrument="BTC-28MAR25-80000-C",
            message="IV spike up 25.0%",
        )
        panel.add_alert(alert)


@pytest.mark.skipif(not HAS_PLOTEXT, reason="textual-plotext not installed")
async def test_vol_smile_panel_mount():
    async with VolSmileApp().run_test() as pilot:
        panel = pilot.app.query_one(VolSmilePanel)
        assert panel is not None


@pytest.mark.skipif(not HAS_PLOTEXT, reason="textual-plotext not installed")
async def test_term_structure_panel_mount():
    async with TermStructureApp().run_test() as pilot:
        panel = pilot.app.query_one(TermStructurePanel)
        assert panel is not None
