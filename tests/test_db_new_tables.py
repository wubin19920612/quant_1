from __future__ import annotations
from datetime import datetime, timezone
import pytest
from src.storage.db import Database


@pytest.fixture
async def db(tmp_path):
    database = Database(str(tmp_path / "test.db"))
    await database.initialize()
    yield database
    await database.close()


async def test_save_and_get_ohlc(db):
    ts = datetime(2025, 3, 28, 0, 0, tzinfo=timezone.utc)
    await db.save_ohlc("deribit", ts, 87000.0, 88000.0, 86500.0, 87500.0, 1234.5)
    rows = await db.get_ohlc("deribit", limit=10)
    assert len(rows) == 1
    assert rows[0]["open"] == 87000.0
    assert rows[0]["close"] == 87500.0


async def test_save_and_get_dvol(db):
    ts = datetime(2025, 3, 28, 12, 0, tzinfo=timezone.utc)
    await db.save_dvol(65.3, ts)
    rows = await db.get_dvol_history(limit=10)
    assert len(rows) == 1
    assert rows[0]["dvol"] == 65.3


async def test_save_and_get_regime_log(db):
    ts = datetime(2025, 3, 28, 12, 0, tzinfo=timezone.utc)
    await db.save_regime("NORMAL", 65.3, -0.2, ts)
    rows = await db.get_regime_log(limit=10)
    assert len(rows) == 1
    assert rows[0]["regime"] == "NORMAL"
    assert rows[0]["zscore"] == -0.2


async def test_get_dvol_since(db):
    ts1 = datetime(2025, 3, 1, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2025, 3, 28, 0, 0, tzinfo=timezone.utc)
    await db.save_dvol(60.0, ts1)
    await db.save_dvol(70.0, ts2)
    since = datetime(2025, 3, 15, 0, 0, tzinfo=timezone.utc)
    rows = await db.get_dvol_since(since)
    assert len(rows) == 1
    assert rows[0]["dvol"] == 70.0
