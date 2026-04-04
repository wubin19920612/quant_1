import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from src.storage.db import Database


@pytest.fixture
async def db():
    # Use project data/ dir to avoid Windows tmp_path permission issues
    db_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "test_tmp.db")
    database = Database(db_path)
    await database.initialize()
    yield database
    await database.close()
    # Cleanup
    try:
        os.remove(db_path)
    except OSError:
        pass


async def test_save_and_get_spot_prices(db):
    now = datetime.now(timezone.utc)
    await db.save_spot_price("deribit", 87500.0, now)
    await db.save_spot_price("deribit", 87600.0, now)
    prices = await db.get_spot_prices("deribit", limit=10)
    assert len(prices) == 2
    assert prices[0][1] == 87500.0


async def test_save_and_get_iv_snapshots(db):
    now = datetime.now(timezone.utc)
    await db.save_iv_snapshot(
        exchange="deribit",
        instrument="BTC-28MAR25-80000-C",
        strike=80000.0,
        expiry=datetime(2025, 3, 28, tzinfo=timezone.utc),
        iv=68.35,
        timestamp=now,
    )
    snapshots = await db.get_iv_snapshots("BTC-28MAR25-80000-C", limit=10)
    assert len(snapshots) == 1
    assert snapshots[0]["iv"] == 68.35


async def test_save_alert(db):
    now = datetime.now(timezone.utc)
    await db.save_alert(
        rule="iv_rv_ratio",
        instrument="BTC-28MAR25-80000-C",
        details="IV/RV=1.54",
        timestamp=now,
    )
    alerts = await db.get_alerts(limit=10)
    assert len(alerts) == 1
    assert alerts[0]["rule"] == "iv_rv_ratio"


async def test_prune_old_data(db):
    old = datetime.now(timezone.utc) - timedelta(days=100)
    recent = datetime.now(timezone.utc)
    await db.save_spot_price("deribit", 50000.0, old)
    await db.save_spot_price("deribit", 87500.0, recent)
    await db.prune(days=90)
    prices = await db.get_spot_prices("deribit", limit=100)
    assert len(prices) == 1
    assert prices[0][1] == 87500.0
