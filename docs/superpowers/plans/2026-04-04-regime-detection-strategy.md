# Regime Detection & Strategy Advisory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add volatility regime detection (low/normal/high/crisis) using DVOL Z-score, advanced RV estimators (Yang-Zhang, Parkinson), and a strategy advisor that maps regime + IV rank to options strategy recommendations — all surfaced via new TUI panels.

**Architecture:** New data flows in three layers: (1) OHLC candle + DVOL data feed from Deribit REST/WS into SQLite, (2) pure-function analytics (regime detector, strategy advisor) consuming stored data, (3) two new Textual UI panels displaying regime state and strategy recommendations. Existing code is untouched in Phase 1-2; Phase 3 wires everything together.

**Tech Stack:** Python 3.12, numpy, scipy, aiosqlite, httpx (Deribit REST), websockets, Textual

---

## File Structure

| File | Responsibility | Phase |
|------|---------------|-------|
| `src/models.py` | Add `OHLC` dataclass, `Regime` enum | 1 |
| `src/analytics/rv_advanced.py` | Yang-Zhang & Parkinson RV estimators | 1 |
| `src/storage/db.py` | Add `ohlc`, `dvol_history`, `regime_log` tables | 1 |
| `src/exchanges/deribit.py` | DVOL WS subscription + OHLC REST fetch | 1 |
| `src/analytics/regime_detector.py` | DVOL Z-score regime classification | 2 |
| `src/analytics/strategy_advisor.py` | Regime + IV rank → strategy recommendations | 2 |
| `src/analytics/alerts.py` | Regime-change alert rule | 3 |
| `src/ui/regime_panel.py` | Regime status display panel | 3 |
| `src/ui/strategy_panel.py` | Strategy recommendation panel | 3 |
| `src/app.py` | Wire regime loop, new tabs, strategy refresh | 3 |
| `config.yaml` | Add regime/strategy config section | 3 |

**Test files** (one per source file):
- `tests/test_models_regime.py`
- `tests/test_rv_advanced.py`
- `tests/test_db_new_tables.py`
- `tests/test_deribit_dvol.py`
- `tests/test_regime_detector.py`
- `tests/test_strategy_advisor.py`
- `tests/test_regime_alert.py`
- `tests/test_regime_panel.py`
- `tests/test_strategy_panel.py`

---

## Phase 1: Data Foundation

### Task 1: Add OHLC and Regime models

**Files:**
- Modify: `src/models.py`
- Create: `tests/test_models_regime.py`

- [ ] **Step 1: Write failing tests for new models**

```python
# tests/test_models_regime.py
from __future__ import annotations

from datetime import datetime, timezone

from src.models import OHLC, Regime


def test_regime_enum_values():
    assert Regime.LOW.value == "LOW"
    assert Regime.NORMAL.value == "NORMAL"
    assert Regime.HIGH.value == "HIGH"
    assert Regime.CRISIS.value == "CRISIS"


def test_ohlc_frozen():
    candle = OHLC(
        timestamp=datetime(2025, 3, 28, 0, 0, tzinfo=timezone.utc),
        open=87000.0,
        high=88000.0,
        low=86500.0,
        close=87500.0,
        volume=1234.5,
    )
    assert candle.open == 87000.0
    assert candle.close == 87500.0


def test_ohlc_immutable():
    import pytest
    candle = OHLC(
        timestamp=datetime(2025, 3, 28, 0, 0, tzinfo=timezone.utc),
        open=87000.0, high=88000.0, low=86500.0, close=87500.0, volume=1234.5,
    )
    with pytest.raises(AttributeError):
        candle.open = 99999.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models_regime.py -v`
Expected: FAIL — `ImportError: cannot import name 'OHLC' from 'src.models'`

- [ ] **Step 3: Add OHLC and Regime to models.py**

Append to end of `src/models.py`:

```python
class Regime(Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRISIS = "CRISIS"


@dataclass(frozen=True)
class OHLC:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models_regime.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add src/models.py tests/test_models_regime.py
git commit -m "feat: add OHLC dataclass and Regime enum to models"
```

---

### Task 2: Yang-Zhang and Parkinson RV estimators

**Files:**
- Create: `src/analytics/rv_advanced.py`
- Create: `tests/test_rv_advanced.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_rv_advanced.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

from src.models import OHLC
from src.analytics.rv_advanced import parkinson_rv, yang_zhang_rv


def _make_candles(n: int, base_price: float = 87000.0, daily_range_pct: float = 0.02) -> list[OHLC]:
    """Generate n synthetic OHLC candles with controlled volatility."""
    candles = []
    price = base_price
    for i in range(n):
        high = price * (1 + daily_range_pct / 2)
        low = price * (1 - daily_range_pct / 2)
        close = price * (1 + (0.001 if i % 2 == 0 else -0.001))
        candles.append(OHLC(
            timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc) + timedelta(days=i),
            open=price, high=high, low=low, close=close, volume=100.0,
        ))
        price = close
    return candles


def test_parkinson_rv_basic():
    candles = _make_candles(30, daily_range_pct=0.02)
    rv = parkinson_rv(candles)
    assert 0.0 < rv < 2.0  # annualized, should be reasonable
    assert isinstance(rv, float)


def test_parkinson_rv_too_few_candles():
    candle = _make_candles(1)
    assert parkinson_rv(candle) == 0.0


def test_yang_zhang_rv_basic():
    candles = _make_candles(30, daily_range_pct=0.02)
    rv = yang_zhang_rv(candles)
    assert 0.0 < rv < 2.0
    assert isinstance(rv, float)


def test_yang_zhang_rv_too_few_candles():
    candles = _make_candles(1)
    assert yang_zhang_rv(candles) == 0.0


def test_yang_zhang_higher_than_close_to_close():
    """Yang-Zhang captures intraday info, so it can differ from close-to-close RV."""
    # High intraday range but small close-to-close moves
    candles = _make_candles(30, daily_range_pct=0.05)
    yz = yang_zhang_rv(candles)
    pk = parkinson_rv(candles)
    # Both should be positive and in a plausible range
    assert yz > 0
    assert pk > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rv_advanced.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.analytics.rv_advanced'`

- [ ] **Step 3: Implement rv_advanced.py**

```python
# src/analytics/rv_advanced.py
from __future__ import annotations

import math

import numpy as np

from src.models import OHLC


def parkinson_rv(candles: list[OHLC], trading_days_year: int = 365) -> float:
    """Parkinson (1980) high-low range estimator. More efficient than close-to-close."""
    if len(candles) < 2:
        return 0.0

    n = len(candles)
    hl_sq_sum = 0.0
    for c in candles:
        if c.low <= 0 or c.high <= 0:
            continue
        hl_sq_sum += math.log(c.high / c.low) ** 2

    factor = 1.0 / (4.0 * n * math.log(2))
    variance = factor * hl_sq_sum
    return math.sqrt(variance * trading_days_year)


def yang_zhang_rv(candles: list[OHLC], trading_days_year: int = 365) -> float:
    """Yang-Zhang (2000) estimator combining overnight, open-to-close, and Rogers-Satchell."""
    if len(candles) < 2:
        return 0.0

    n = len(candles) - 1  # we need pairs

    # Overnight variance (close-to-open)
    log_oc = []  # log(open_i / close_{i-1})
    for i in range(1, len(candles)):
        if candles[i].open <= 0 or candles[i - 1].close <= 0:
            continue
        log_oc.append(math.log(candles[i].open / candles[i - 1].close))

    if not log_oc:
        return 0.0

    arr_oc = np.array(log_oc)
    sigma_o_sq = float(np.var(arr_oc, ddof=1))

    # Close-to-close variance
    log_cc = []
    for i in range(1, len(candles)):
        if candles[i].close <= 0 or candles[i - 1].close <= 0:
            continue
        log_cc.append(math.log(candles[i].close / candles[i - 1].close))

    if not log_cc:
        return 0.0

    arr_cc = np.array(log_cc)
    sigma_c_sq = float(np.var(arr_cc, ddof=1))

    # Rogers-Satchell variance
    rs_sum = 0.0
    count = 0
    for c in candles:
        if c.high <= 0 or c.low <= 0 or c.open <= 0 or c.close <= 0:
            continue
        ho = math.log(c.high / c.open)
        hc = math.log(c.high / c.close)
        lo = math.log(c.low / c.open)
        lc = math.log(c.low / c.close)
        rs_sum += ho * hc + lo * lc
        count += 1

    if count == 0:
        return 0.0

    sigma_rs_sq = rs_sum / count

    # Yang-Zhang combination
    k = 0.34 / (1.34 + (n + 1) / (n - 1))
    sigma_yz_sq = sigma_o_sq + k * sigma_c_sq + (1 - k) * sigma_rs_sq

    if sigma_yz_sq < 0:
        return 0.0

    return math.sqrt(sigma_yz_sq * trading_days_year)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rv_advanced.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/analytics/rv_advanced.py tests/test_rv_advanced.py
git commit -m "feat: add Parkinson and Yang-Zhang RV estimators"
```

---

### Task 3: Database — new tables (ohlc, dvol_history, regime_log)

**Files:**
- Modify: `src/storage/db.py`
- Create: `tests/test_db_new_tables.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_db_new_tables.py
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_db_new_tables.py -v`
Expected: FAIL — `AttributeError: 'Database' object has no attribute 'save_ohlc'`

- [ ] **Step 3: Add new tables and methods to db.py**

Add to the `executescript` in `initialize()` (append after existing CREATE statements):

```python
CREATE TABLE IF NOT EXISTS ohlc (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exchange TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    open REAL NOT NULL, high REAL NOT NULL,
    low REAL NOT NULL, close REAL NOT NULL,
    volume REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS dvol_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dvol REAL NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS regime_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    regime TEXT NOT NULL,
    dvol REAL NOT NULL,
    zscore REAL NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ohlc_exchange_ts ON ohlc(exchange, timestamp);
CREATE INDEX IF NOT EXISTS idx_dvol_ts ON dvol_history(timestamp);
```

Add these methods to `Database` class:

```python
async def save_ohlc(
    self, exchange: str, timestamp: datetime,
    open_: float, high: float, low: float, close: float, volume: float,
) -> None:
    assert self._conn
    await self._conn.execute(
        "INSERT INTO ohlc (exchange, timestamp, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (exchange, timestamp.isoformat(), open_, high, low, close, volume),
    )
    await self._conn.commit()

async def get_ohlc(self, exchange: str, limit: int = 365) -> list[dict]:
    assert self._conn
    cursor = await self._conn.execute(
        "SELECT * FROM ohlc WHERE exchange = ? ORDER BY timestamp DESC LIMIT ?",
        (exchange, limit),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]

async def save_dvol(self, dvol: float, timestamp: datetime) -> None:
    assert self._conn
    await self._conn.execute(
        "INSERT INTO dvol_history (dvol, timestamp) VALUES (?, ?)",
        (dvol, timestamp.isoformat()),
    )
    await self._conn.commit()

async def get_dvol_history(self, limit: int = 1000) -> list[dict]:
    assert self._conn
    cursor = await self._conn.execute(
        "SELECT * FROM dvol_history ORDER BY timestamp DESC LIMIT ?", (limit,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]

async def get_dvol_since(self, since: datetime) -> list[dict]:
    assert self._conn
    cursor = await self._conn.execute(
        "SELECT * FROM dvol_history WHERE timestamp >= ? ORDER BY timestamp ASC",
        (since.isoformat(),),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]

async def save_regime(self, regime: str, dvol: float, zscore: float, timestamp: datetime) -> None:
    assert self._conn
    await self._conn.execute(
        "INSERT INTO regime_log (regime, dvol, zscore, timestamp) VALUES (?, ?, ?, ?)",
        (regime, dvol, zscore, timestamp.isoformat()),
    )
    await self._conn.commit()

async def get_regime_log(self, limit: int = 100) -> list[dict]:
    assert self._conn
    cursor = await self._conn.execute(
        "SELECT * FROM regime_log ORDER BY timestamp DESC LIMIT ?", (limit,),
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
```

Also add `ohlc`, `dvol_history`, `regime_log` to `prune()`:

```python
await self._conn.execute("DELETE FROM ohlc WHERE timestamp < ?", (cutoff,))
await self._conn.execute("DELETE FROM dvol_history WHERE timestamp < ?", (cutoff,))
await self._conn.execute("DELETE FROM regime_log WHERE timestamp < ?", (cutoff,))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_db_new_tables.py -v`
Expected: 4 passed

- [ ] **Step 5: Run all existing DB tests to verify no regression**

Run: `pytest tests/test_db.py tests/test_db_new_tables.py -v`
Expected: 8 passed (4 old + 4 new)

- [ ] **Step 6: Commit**

```bash
git add src/storage/db.py tests/test_db_new_tables.py
git commit -m "feat: add ohlc, dvol_history, regime_log tables to database"
```

---

### Task 4: Deribit DVOL subscription + OHLC REST fetch

**Files:**
- Modify: `src/exchanges/deribit.py`
- Create: `tests/test_deribit_dvol.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_deribit_dvol.py
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from src.exchanges.deribit import DeribitExchange


def test_parse_dvol_data():
    ex = DeribitExchange(ws_url="wss://test.deribit.com/ws/api/v2")
    data = {"volatility": 65.3, "timestamp": 1743000000123}
    dvol, ts = ex.parse_dvol(data)
    assert dvol == 65.3
    assert ts.year == 2025


def test_parse_dvol_data_missing_key():
    ex = DeribitExchange(ws_url="wss://test.deribit.com/ws/api/v2")
    result = ex.parse_dvol({})
    assert result is None


def test_parse_ohlc_candles():
    ex = DeribitExchange(ws_url="wss://test.deribit.com/ws/api/v2")
    raw_candles = [
        {"tick": 1743000000000, "open": 87000, "high": 88000, "low": 86500, "close": 87500, "volume": 1234.5},
        {"tick": 1743086400000, "open": 87500, "high": 89000, "low": 87000, "close": 88500, "volume": 2000.0},
    ]
    candles = ex.parse_ohlc_candles(raw_candles)
    assert len(candles) == 2
    assert candles[0].open == 87000.0
    assert candles[1].close == 88500.0


def test_parse_ohlc_candles_empty():
    ex = DeribitExchange(ws_url="wss://test.deribit.com/ws/api/v2")
    assert ex.parse_ohlc_candles([]) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_deribit_dvol.py -v`
Expected: FAIL — `AttributeError: 'DeribitExchange' object has no attribute 'parse_dvol'`

- [ ] **Step 3: Add DVOL + OHLC methods to DeribitExchange**

Add imports at top of `src/exchanges/deribit.py`:

```python
from src.models import OptionTicker, OHLC
```

Add a DVOL callback mechanism and new methods to the `DeribitExchange` class:

```python
def __init__(self, ws_url: str = "wss://www.deribit.com/ws/api/v2") -> None:
    super().__init__(name="deribit", ws_url=ws_url)
    self._ws: ClientConnection | None = None
    self._msg_id = 0
    self._running = False
    self._dvol_callbacks: list[Callable[[float, datetime], Any]] = []

def on_dvol(self, callback: Callable[[float, datetime], Any]) -> None:
    self._dvol_callbacks.append(callback)

def _emit_dvol(self, dvol: float, ts: datetime) -> None:
    for cb in self._dvol_callbacks:
        cb(dvol, ts)

def parse_dvol(self, data: dict) -> tuple[float, datetime] | None:
    try:
        dvol = float(data["volatility"])
        ts = datetime.fromtimestamp(data["timestamp"] / 1000, tz=timezone.utc)
        return dvol, ts
    except (KeyError, ValueError, TypeError) as e:
        logger.warning("Failed to parse DVOL data: %s", e)
        return None

@staticmethod
def parse_ohlc_candles(raw_candles: list[dict]) -> list[OHLC]:
    candles = []
    for c in raw_candles:
        try:
            candles.append(OHLC(
                timestamp=datetime.fromtimestamp(c["tick"] / 1000, tz=timezone.utc),
                open=float(c["open"]),
                high=float(c["high"]),
                low=float(c["low"]),
                close=float(c["close"]),
                volume=float(c["volume"]),
            ))
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Failed to parse OHLC candle: %s", e)
    return candles

async def subscribe_dvol(self) -> None:
    if not self._ws:
        return
    await self._send_rpc("public/subscribe", {"channels": ["deribit_volatility_index.btc_usd"]})

async def fetch_ohlc(self, currency: str = "BTC", resolution: str = "1D", count: int = 90) -> list[OHLC]:
    """Fetch historical OHLC candles via REST-over-WS."""
    if not self._ws:
        return []
    import time
    end_ts = int(time.time() * 1000)
    start_ts = end_ts - count * 86400 * 1000
    result = await self._send_rpc("public/get_tradingview_chart_data", {
        "instrument_name": f"{currency}-PERPETUAL",
        "start_timestamp": start_ts,
        "end_timestamp": end_ts,
        "resolution": resolution,
    })
    if not result:
        return []
    # Deribit returns {ticks:[], open:[], high:[], low:[], close:[], volume:[]}
    ticks = result.get("ticks", [])
    opens = result.get("open", [])
    highs = result.get("high", [])
    lows = result.get("low", [])
    closes = result.get("close", [])
    volumes = result.get("volume", [])
    candles = []
    for i in range(len(ticks)):
        try:
            candles.append(OHLC(
                timestamp=datetime.fromtimestamp(ticks[i] / 1000, tz=timezone.utc),
                open=float(opens[i]), high=float(highs[i]),
                low=float(lows[i]), close=float(closes[i]),
                volume=float(volumes[i]),
            ))
        except (IndexError, ValueError, TypeError):
            continue
    return candles
```

Also update `listen()` to handle DVOL subscription messages — add a branch inside the `if msg.get("method") == "subscription":` block:

```python
async def listen(self) -> None:
    if not self._ws: return
    try:
        async for raw in self._ws:
            msg = json.loads(raw)
            if msg.get("method") == "subscription":
                channel = msg["params"].get("channel", "")
                data = msg["params"]["data"]
                if channel.startswith("deribit_volatility_index"):
                    result = self.parse_dvol(data)
                    if result:
                        self._emit_dvol(*result)
                else:
                    ticker = self.parse_ticker(data)
                    if ticker:
                        self._emit(ticker)
            elif msg.get("method") == "heartbeat" and msg.get("params", {}).get("type") == "test_request":
                await self._send_rpc("public/test", {})
    except websockets.ConnectionClosed:
        self._connected = False
```

Add `Callable` and `Any` to imports:

```python
from collections.abc import Callable
from typing import Any
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_deribit_dvol.py -v`
Expected: 4 passed

- [ ] **Step 5: Run all exchange tests for regression**

Run: `pytest tests/test_exchanges.py tests/test_deribit_dvol.py -v`
Expected: 9 passed (5 old + 4 new)

- [ ] **Step 6: Commit**

```bash
git add src/exchanges/deribit.py tests/test_deribit_dvol.py
git commit -m "feat: add DVOL subscription and OHLC fetch to Deribit adapter"
```

---

## Phase 2: Analytics Engine

### Task 5: Regime Detector (DVOL Z-score)

**Files:**
- Create: `src/analytics/regime_detector.py`
- Create: `tests/test_regime_detector.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_regime_detector.py
from __future__ import annotations

from src.models import Regime
from src.analytics.regime_detector import RegimeDetector


def test_classify_low_regime():
    detector = RegimeDetector(lookback_days=90)
    # Feed 90 days of low DVOL around 40, then current at 35
    history = [40.0 + (i % 3 - 1) for i in range(90)]
    regime, zscore = detector.classify(history, current_dvol=35.0)
    assert regime == Regime.LOW
    assert zscore < -1.0


def test_classify_normal_regime():
    detector = RegimeDetector(lookback_days=90)
    history = [55.0 + (i % 5 - 2) * 0.5 for i in range(90)]
    regime, zscore = detector.classify(history, current_dvol=55.0)
    assert regime == Regime.NORMAL
    assert -1.0 <= zscore <= 1.0


def test_classify_high_regime():
    detector = RegimeDetector(lookback_days=90)
    history = [55.0 + (i % 5 - 2) * 0.5 for i in range(90)]
    regime, zscore = detector.classify(history, current_dvol=62.0)
    assert regime == Regime.HIGH
    assert zscore > 1.0


def test_classify_crisis_regime():
    detector = RegimeDetector(lookback_days=90)
    history = [55.0 + (i % 5 - 2) * 0.5 for i in range(90)]
    regime, zscore = detector.classify(history, current_dvol=70.0)
    assert regime == Regime.CRISIS
    assert zscore > 2.0


def test_classify_insufficient_history():
    detector = RegimeDetector(lookback_days=90)
    regime, zscore = detector.classify([50.0], current_dvol=50.0)
    assert regime == Regime.NORMAL
    assert zscore == 0.0


def test_custom_thresholds():
    detector = RegimeDetector(
        lookback_days=90,
        low_z=-0.5, high_z=0.5, crisis_z=1.5,
    )
    history = [55.0] * 90
    # Small deviation above mean triggers HIGH with tighter threshold
    regime, _ = detector.classify(history, current_dvol=56.0)
    # With std ≈ 0 (all same value), zscore would be huge — handle zero std
    assert regime in (Regime.HIGH, Regime.CRISIS)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_regime_detector.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement regime_detector.py**

```python
# src/analytics/regime_detector.py
from __future__ import annotations

import numpy as np

from src.models import Regime


class RegimeDetector:
    def __init__(
        self,
        lookback_days: int = 90,
        low_z: float = -1.0,
        high_z: float = 1.0,
        crisis_z: float = 2.0,
    ) -> None:
        self._lookback = lookback_days
        self._low_z = low_z
        self._high_z = high_z
        self._crisis_z = crisis_z

    def classify(self, dvol_history: list[float], current_dvol: float) -> tuple[Regime, float]:
        """Classify regime based on Z-score of current DVOL vs historical distribution.

        Returns (regime, zscore).
        """
        if len(dvol_history) < 10:
            return Regime.NORMAL, 0.0

        arr = np.array(dvol_history[-self._lookback:])
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1))

        if std < 1e-8:
            # Near-zero std: if current differs from mean at all, it's extreme
            if current_dvol > mean + 0.01:
                return Regime.CRISIS, 999.0
            elif current_dvol < mean - 0.01:
                return Regime.LOW, -999.0
            return Regime.NORMAL, 0.0

        zscore = (current_dvol - mean) / std

        if zscore >= self._crisis_z:
            regime = Regime.CRISIS
        elif zscore >= self._high_z:
            regime = Regime.HIGH
        elif zscore <= self._low_z:
            regime = Regime.LOW
        else:
            regime = Regime.NORMAL

        return regime, round(zscore, 3)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_regime_detector.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/analytics/regime_detector.py tests/test_regime_detector.py
git commit -m "feat: add DVOL Z-score regime detector"
```

---

### Task 6: Strategy Advisor

**Files:**
- Create: `src/analytics/strategy_advisor.py`
- Create: `tests/test_strategy_advisor.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_strategy_advisor.py
from __future__ import annotations

from src.models import Regime
from src.analytics.strategy_advisor import StrategyAdvisor, StrategyAdvice


def test_crisis_regime_suggests_protection():
    advisor = StrategyAdvisor()
    advice = advisor.advise(regime=Regime.CRISIS, iv_rank=0.9)
    assert advice.regime == Regime.CRISIS
    assert len(advice.strategies) > 0
    # In crisis with high IV rank, should recommend selling premium / protective
    assert any("sell" in s.lower() or "iron" in s.lower() or "spread" in s.lower()
               for s in advice.strategies)


def test_low_regime_low_iv_rank():
    advisor = StrategyAdvisor()
    advice = advisor.advise(regime=Regime.LOW, iv_rank=0.1)
    assert advice.regime == Regime.LOW
    assert len(advice.strategies) > 0
    # Low vol + low IV rank = buy cheap options
    assert any("buy" in s.lower() or "straddle" in s.lower() or "calendar" in s.lower()
               for s in advice.strategies)


def test_normal_regime_moderate_iv():
    advisor = StrategyAdvisor()
    advice = advisor.advise(regime=Regime.NORMAL, iv_rank=0.5)
    assert advice.regime == Regime.NORMAL
    assert len(advice.strategies) > 0


def test_high_regime_high_iv_rank():
    advisor = StrategyAdvisor()
    advice = advisor.advise(regime=Regime.HIGH, iv_rank=0.8)
    assert len(advice.strategies) > 0
    assert advice.iv_rank == 0.8


def test_iv_rank_clamped():
    advisor = StrategyAdvisor()
    advice = advisor.advise(regime=Regime.NORMAL, iv_rank=1.5)
    assert advice.iv_rank == 1.0
    advice2 = advisor.advise(regime=Regime.NORMAL, iv_rank=-0.3)
    assert advice2.iv_rank == 0.0


def test_advice_has_description():
    advisor = StrategyAdvisor()
    advice = advisor.advise(regime=Regime.HIGH, iv_rank=0.7)
    assert len(advice.description) > 10  # non-trivial description
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_strategy_advisor.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement strategy_advisor.py**

```python
# src/analytics/strategy_advisor.py
from __future__ import annotations

from dataclasses import dataclass

from src.models import Regime


@dataclass(frozen=True)
class StrategyAdvice:
    regime: Regime
    iv_rank: float
    strategies: list[str]
    description: str


# Strategy matrix: (regime, iv_rank_bucket) -> (strategies, description)
_STRATEGY_MAP: dict[tuple[Regime, str], tuple[list[str], str]] = {
    (Regime.LOW, "low"): (
        ["Buy straddle", "Buy calendar spread", "Long volatility"],
        "Volatility is historically low and cheap — good time to buy options or go long vol.",
    ),
    (Regime.LOW, "mid"): (
        ["Buy calendar spread", "Long call/put"],
        "Vol is low but not at extreme discount — directional plays with limited risk.",
    ),
    (Regime.LOW, "high"): (
        ["Buy calendar spread", "Neutral strategies"],
        "Vol is low overall but IV rank is elevated — calendar spreads benefit from term structure.",
    ),
    (Regime.NORMAL, "low"): (
        ["Buy straddle", "Buy strangle"],
        "Normal vol environment with options priced cheaply — consider buying premium.",
    ),
    (Regime.NORMAL, "mid"): (
        ["Iron condor", "Butterfly spread", "Neutral"],
        "Balanced environment — range-bound strategies or wait for clearer signal.",
    ),
    (Regime.NORMAL, "high"): (
        ["Sell put spread", "Iron condor", "Sell covered call"],
        "Normal vol but IV is relatively elevated — sell premium with defined risk.",
    ),
    (Regime.HIGH, "low"): (
        ["Buy straddle", "Buy strangle"],
        "High vol regime but options are priced low relative to recent history — buy opportunity.",
    ),
    (Regime.HIGH, "mid"): (
        ["Iron condor", "Sell put spread"],
        "Elevated vol with moderate IV rank — sell premium with wider strikes.",
    ),
    (Regime.HIGH, "high"): (
        ["Sell iron condor", "Sell strangle", "Sell put spread"],
        "High vol with rich IV — prime environment to sell premium with defined risk.",
    ),
    (Regime.CRISIS, "low"): (
        ["Buy put protection", "Long volatility"],
        "Crisis regime but options somehow cheap — buy protection immediately.",
    ),
    (Regime.CRISIS, "mid"): (
        ["Buy put spread", "Collar"],
        "Crisis with moderate IV — hedge with spreads to manage cost.",
    ),
    (Regime.CRISIS, "high"): (
        ["Sell iron condor (wide)", "Sell put spread (far OTM)", "Cash / reduce exposure"],
        "Crisis with expensive options — if selling, use very wide wings. Consider reducing exposure.",
    ),
}


class StrategyAdvisor:
    def advise(self, regime: Regime, iv_rank: float) -> StrategyAdvice:
        iv_rank = max(0.0, min(1.0, iv_rank))

        if iv_rank < 0.33:
            bucket = "low"
        elif iv_rank < 0.67:
            bucket = "mid"
        else:
            bucket = "high"

        strategies, description = _STRATEGY_MAP.get(
            (regime, bucket),
            (["No specific recommendation"], "Insufficient data for strategy recommendation."),
        )

        return StrategyAdvice(
            regime=regime,
            iv_rank=iv_rank,
            strategies=list(strategies),
            description=description,
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_strategy_advisor.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add src/analytics/strategy_advisor.py tests/test_strategy_advisor.py
git commit -m "feat: add strategy advisor with regime+IV rank matrix"
```

---

## Phase 3: Integration

### Task 7: Regime-change alert rule

**Files:**
- Modify: `src/analytics/alerts.py`
- Create: `tests/test_regime_alert.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_regime_alert.py
from __future__ import annotations

from src.analytics.alerts import AlertEngine
from src.models import Regime


def test_regime_change_triggers_alert():
    engine = AlertEngine(cooldown_minutes=5)
    alerts = engine.check_regime_change(Regime.HIGH, prev_regime=Regime.NORMAL)
    assert len(alerts) == 1
    assert alerts[0].rule == "regime_change"
    assert "NORMAL" in alerts[0].message
    assert "HIGH" in alerts[0].message
    assert alerts[0].level == "high"


def test_no_alert_when_regime_unchanged():
    engine = AlertEngine(cooldown_minutes=5)
    alerts = engine.check_regime_change(Regime.NORMAL, prev_regime=Regime.NORMAL)
    assert len(alerts) == 0


def test_crisis_regime_change_is_high_level():
    engine = AlertEngine(cooldown_minutes=5)
    alerts = engine.check_regime_change(Regime.CRISIS, prev_regime=Regime.HIGH)
    assert len(alerts) == 1
    assert alerts[0].level == "high"


def test_downgrade_regime_is_medium_level():
    engine = AlertEngine(cooldown_minutes=5)
    alerts = engine.check_regime_change(Regime.LOW, prev_regime=Regime.NORMAL)
    assert len(alerts) == 1
    assert alerts[0].level == "medium"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_regime_alert.py -v`
Expected: FAIL — `AttributeError: 'AlertEngine' object has no attribute 'check_regime_change'`

- [ ] **Step 3: Add check_regime_change to AlertEngine**

Add to `src/analytics/alerts.py` — import `Regime` and add method:

Add import at top:
```python
from src.models import AlertEvent, Regime
```

Add method to AlertEngine class:

```python
_REGIME_SEVERITY = {Regime.CRISIS: 4, Regime.HIGH: 3, Regime.NORMAL: 2, Regime.LOW: 1}

def check_regime_change(self, new_regime: Regime, prev_regime: Regime) -> list[AlertEvent]:
    if new_regime == prev_regime:
        return []

    if not self._is_cooled_down("regime_change", "global"):
        return []

    escalating = self._REGIME_SEVERITY[new_regime] > self._REGIME_SEVERITY[prev_regime]
    level = "high" if escalating or new_regime == Regime.CRISIS else "medium"

    alert = AlertEvent(
        timestamp=datetime.now(timezone.utc),
        level=level,
        rule="regime_change",
        instrument="BTC",
        message=f"Regime changed: {prev_regime.value} → {new_regime.value}",
    )
    self._record_alert("regime_change", "global")
    return [alert]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_regime_alert.py -v`
Expected: 4 passed

- [ ] **Step 5: Run all alert tests for regression**

Run: `pytest tests/test_alerts.py tests/test_regime_alert.py -v`
Expected: 14 passed (10 old + 4 new)

- [ ] **Step 6: Commit**

```bash
git add src/analytics/alerts.py tests/test_regime_alert.py
git commit -m "feat: add regime-change alert rule to AlertEngine"
```

---

### Task 8: Regime Panel (UI)

**Files:**
- Create: `src/ui/regime_panel.py`
- Create: `tests/test_regime_panel.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_regime_panel.py
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from src.models import Regime
from src.ui.regime_panel import RegimePanel


class RegimePanelApp(App):
    def compose(self) -> ComposeResult:
        yield RegimePanel(id="regime_panel")


async def test_regime_panel_mount():
    async with RegimePanelApp().run_test() as pilot:
        panel = pilot.app.query_one(RegimePanel)
        assert panel is not None


async def test_regime_panel_update():
    async with RegimePanelApp().run_test() as pilot:
        panel = pilot.app.query_one(RegimePanel)
        panel.update_regime(
            regime=Regime.HIGH,
            dvol=72.5,
            zscore=1.45,
            iv_rank=0.82,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_regime_panel.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement regime_panel.py**

```python
# src/ui/regime_panel.py
from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Label, Static

from src.models import Regime

REGIME_STYLE = {
    Regime.LOW: ("bold cyan", "LOW VOL"),
    Regime.NORMAL: ("bold white", "NORMAL"),
    Regime.HIGH: ("bold yellow", "HIGH VOL"),
    Regime.CRISIS: ("bold red", "CRISIS"),
}


class RegimePanel(Widget):
    DEFAULT_CSS = """
    RegimePanel { height: 1fr; padding: 1; }
    RegimePanel .regime-label { text-style: bold; width: 100%; content-align: center middle; height: 3; }
    RegimePanel .metric { width: 1fr; height: auto; padding: 0 1; }
    RegimePanel .metric-row { height: auto; width: 100%; }
    """

    def compose(self) -> ComposeResult:
        yield Static("Regime: —", id="regime_label", classes="regime-label")
        with Horizontal(classes="metric-row"):
            yield Static("DVOL: —", id="dvol_value", classes="metric")
            yield Static("Z-Score: —", id="zscore_value", classes="metric")
            yield Static("IV Rank: —", id="ivrank_value", classes="metric")

    def update_regime(
        self, regime: Regime, dvol: float, zscore: float, iv_rank: float,
    ) -> None:
        style, label = REGIME_STYLE.get(regime, ("white", "UNKNOWN"))
        try:
            self.query_one("#regime_label", Static).update(
                f"[{style}]Regime: {label}[/{style}]"
            )
            self.query_one("#dvol_value", Static).update(f"DVOL: {dvol:.1f}")
            self.query_one("#zscore_value", Static).update(f"Z-Score: {zscore:+.2f}")
            self.query_one("#ivrank_value", Static).update(f"IV Rank: {iv_rank:.0%}")
        except Exception:
            pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_regime_panel.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/ui/regime_panel.py tests/test_regime_panel.py
git commit -m "feat: add regime display panel"
```

---

### Task 9: Strategy Panel (UI)

**Files:**
- Create: `src/ui/strategy_panel.py`
- Create: `tests/test_strategy_panel.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_strategy_panel.py
from __future__ import annotations

import pytest
from textual.app import App, ComposeResult

from src.models import Regime
from src.analytics.strategy_advisor import StrategyAdvice
from src.ui.strategy_panel import StrategyPanel


class StrategyPanelApp(App):
    def compose(self) -> ComposeResult:
        yield StrategyPanel(id="strategy_panel")


async def test_strategy_panel_mount():
    async with StrategyPanelApp().run_test() as pilot:
        panel = pilot.app.query_one(StrategyPanel)
        assert panel is not None


async def test_strategy_panel_update():
    async with StrategyPanelApp().run_test() as pilot:
        panel = pilot.app.query_one(StrategyPanel)
        advice = StrategyAdvice(
            regime=Regime.HIGH,
            iv_rank=0.8,
            strategies=["Sell iron condor", "Sell strangle"],
            description="High vol with rich IV — sell premium.",
        )
        panel.update_advice(advice)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_strategy_panel.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement strategy_panel.py**

```python
# src/ui/strategy_panel.py
from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import RichLog, Static

from src.analytics.strategy_advisor import StrategyAdvice


class StrategyPanel(Widget):
    DEFAULT_CSS = """
    StrategyPanel { height: 1fr; padding: 1; }
    StrategyPanel Static { width: 100%; height: auto; }
    StrategyPanel RichLog { height: 1fr; border: solid $accent; }
    """

    def compose(self) -> ComposeResult:
        yield Static("Strategy Recommendations", id="strategy_title")
        yield RichLog(id="strategy_log", wrap=True, markup=True)

    def update_advice(self, advice: StrategyAdvice) -> None:
        try:
            log = self.query_one("#strategy_log", RichLog)
            log.clear()
            log.write(f"[bold]Regime:[/bold] {advice.regime.value}  |  "
                      f"[bold]IV Rank:[/bold] {advice.iv_rank:.0%}\n")
            log.write(f"[dim]{advice.description}[/dim]\n")
            log.write("[bold]Recommended Strategies:[/bold]")
            for i, strategy in enumerate(advice.strategies, 1):
                log.write(f"  {i}. {strategy}")
        except Exception:
            pass
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_strategy_panel.py -v`
Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/ui/strategy_panel.py tests/test_strategy_panel.py
git commit -m "feat: add strategy recommendation panel"
```

---

### Task 10: Wire everything into app.py + config

**Files:**
- Modify: `src/app.py`
- Modify: `config.yaml`

This is the final integration task. It connects regime detection, strategy advising, and the new UI panels into the running app.

- [ ] **Step 1: Update config.yaml**

Add after the `alerts.telegram` section:

```yaml
regime:
  lookback_days: 90
  low_z: -1.0
  high_z: 1.0
  crisis_z: 2.0
  update_interval: 60  # seconds between regime re-evaluation
```

- [ ] **Step 2: Update app.py imports**

Add these imports at the top of `src/app.py`:

```python
from src.analytics.regime_detector import RegimeDetector
from src.analytics.strategy_advisor import StrategyAdvisor
from src.ui.regime_panel import RegimePanel
from src.ui.strategy_panel import StrategyPanel
```

- [ ] **Step 3: Update MonitorApp.__init__**

After the `self._telegram = ...` line, add:

```python
regime_cfg = self._config.get("regime", {})
self._regime_detector = RegimeDetector(
    lookback_days=regime_cfg.get("lookback_days", 90),
    low_z=regime_cfg.get("low_z", -1.0),
    high_z=regime_cfg.get("high_z", 1.0),
    crisis_z=regime_cfg.get("crisis_z", 2.0),
)
self._strategy_advisor = StrategyAdvisor()
self._current_regime = Regime.NORMAL
self._dvol_history: list[float] = []
self._current_dvol: float = 0.0
```

Also add `from src.models import AlertEvent, OptionTicker, Regime` to the imports.

- [ ] **Step 4: Update BINDINGS — add F5 and F6**

```python
BINDINGS = [
    Binding("f1", "switch_tab('dashboard')", "IV/RV"),
    Binding("f2", "switch_tab('smile')", "Smile"),
    Binding("f3", "switch_tab('term')", "Term"),
    Binding("f4", "switch_tab('alerts')", "Alerts"),
    Binding("f5", "switch_tab('regime')", "Regime"),
    Binding("f6", "switch_tab('strategy')", "Strategy"),
    Binding("q", "quit", "Quit"),
]
```

- [ ] **Step 5: Update compose() — add new TabPanes**

After the `"Alerts [F4]"` TabPane, add:

```python
with TabPane("Regime [F5]", id="regime"):
    yield RegimePanel(id="regime_panel")
with TabPane("Strategy [F6]", id="strategy"):
    yield StrategyPanel(id="strategy_panel")
```

- [ ] **Step 6: Add DVOL callback and regime update loop to on_mount**

In `on_mount()`, after setting up exchanges, add:

```python
# Register DVOL callback for Deribit
for ex in self._exchanges:
    if hasattr(ex, 'on_dvol'):
        ex.on_dvol(self._on_dvol)

# Start regime update loop
regime_interval = self._config.get("regime", {}).get("update_interval", 60)
self.set_interval(regime_interval, self._update_regime)
```

- [ ] **Step 7: Add _on_dvol and _update_regime methods**

```python
def _on_dvol(self, dvol: float, ts: datetime) -> None:
    self._current_dvol = dvol
    self._dvol_history.append(dvol)
    max_points = 90 * 24  # 90 days of hourly data
    if len(self._dvol_history) > max_points:
        self._dvol_history = self._dvol_history[-max_points:]

def _update_regime(self) -> None:
    if not self._dvol_history or self._current_dvol <= 0:
        return
    prev_regime = self._current_regime
    new_regime, zscore = self._regime_detector.classify(
        self._dvol_history, self._current_dvol,
    )
    self._current_regime = new_regime

    # Compute IV rank (percentile of current DVOL in history)
    if len(self._dvol_history) >= 10:
        sorted_hist = sorted(self._dvol_history)
        rank_pos = sum(1 for v in sorted_hist if v <= self._current_dvol)
        iv_rank = rank_pos / len(sorted_hist)
    else:
        iv_rank = 0.5

    # Update regime panel
    try:
        panel = self.query_one("#regime_panel", RegimePanel)
        panel.update_regime(new_regime, self._current_dvol, zscore, iv_rank)
    except Exception:
        pass

    # Update strategy panel
    advice = self._strategy_advisor.advise(new_regime, iv_rank)
    try:
        panel = self.query_one("#strategy_panel", StrategyPanel)
        panel.update_advice(advice)
    except Exception:
        pass

    # Check for regime change alerts
    alerts = self._alert_engine.check_regime_change(new_regime, prev_regime)
    for alert in alerts:
        self._show_alert(alert)
```

- [ ] **Step 8: Subscribe to DVOL in _run_exchange for Deribit**

In `_run_exchange()`, after `await exchange.subscribe_options(symbol)`, add:

```python
if hasattr(exchange, 'subscribe_dvol'):
    await exchange.subscribe_dvol()
```

- [ ] **Step 9: Run all tests to verify no regression**

Run: `pytest --tb=short -q`
Expected: All tests pass (existing 55 + all new tests from Phase 1-3)

- [ ] **Step 10: Commit**

```bash
git add src/app.py config.yaml
git commit -m "feat: integrate regime detection and strategy advisory into app"
```

---

## Phase 4: Enhancement (Optional)

### Task 11: HMM Regime Detector upgrade (Level 3)

> **Prerequisite:** Phase 1-3 complete and stable. This is an optional upgrade.

**Files:**
- Modify: `src/analytics/regime_detector.py` — add `HMMRegimeDetector` class
- Create: `tests/test_regime_hmm.py`

This task is intentionally left at a high level since it's optional. Implementation approach:

- [ ] **Step 1: Add hmmlearn dependency**

```bash
pip install hmmlearn
```

Add to `pyproject.toml` optional dependencies:

```toml
[project.optional-dependencies]
hmm = ["hmmlearn>=0.3"]
```

- [ ] **Step 2: Write tests for HMMRegimeDetector**

Tests should verify:
- HMM with 3 states classifies synthetic data into distinct regimes
- Model handles insufficient data gracefully (falls back to Z-score)
- Serialization/deserialization of fitted model

- [ ] **Step 3: Implement HMMRegimeDetector**

Key design:
- Subclass or parallel class to `RegimeDetector`
- `fit(dvol_history)` trains the GaussianHMM with 4 hidden states
- `classify()` uses Viterbi path for most likely current state
- Map HMM states to Regime enum by sorting state means (lowest mean → LOW, highest → CRISIS)
- Fall back to Z-score if `hmmlearn` not installed or insufficient data (<60 days)

- [ ] **Step 4: Config flag to enable HMM**

```yaml
regime:
  method: "zscore"  # or "hmm"
```

- [ ] **Step 5: Commit**

```bash
git commit -m "feat: add optional HMM-based regime detector"
```

---

## Summary

| Task | Phase | Files | Est. Tests |
|------|-------|-------|-----------|
| 1. OHLC + Regime models | 1 | models.py | 3 |
| 2. Yang-Zhang + Parkinson | 1 | rv_advanced.py | 5 |
| 3. DB new tables | 1 | db.py | 4 |
| 4. Deribit DVOL + OHLC | 1 | deribit.py | 4 |
| 5. Regime Detector | 2 | regime_detector.py | 6 |
| 6. Strategy Advisor | 2 | strategy_advisor.py | 6 |
| 7. Regime-change alert | 3 | alerts.py | 4 |
| 8. Regime Panel | 3 | regime_panel.py | 2 |
| 9. Strategy Panel | 3 | strategy_panel.py | 2 |
| 10. App integration | 3 | app.py, config.yaml | 0 (covered by existing app tests) |
| 11. HMM upgrade (optional) | 4 | regime_detector.py | 3+ |

**Total: 10 required tasks, ~36 new tests, ~11 commits**
