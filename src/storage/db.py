from __future__ import annotations

from datetime import datetime, timedelta, timezone

import aiosqlite


class Database:
    def __init__(self, path: str) -> None:
        self._path = path
        self._conn: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        self._conn = await aiosqlite.connect(self._path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS spot_prices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL, price REAL NOT NULL, timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS iv_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                exchange TEXT NOT NULL, instrument TEXT NOT NULL,
                strike REAL NOT NULL, expiry TEXT NOT NULL,
                iv REAL NOT NULL, timestamp TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule TEXT NOT NULL, instrument TEXT NOT NULL,
                details TEXT NOT NULL, timestamp TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_spot_exchange_ts ON spot_prices(exchange, timestamp);
            CREATE INDEX IF NOT EXISTS idx_iv_instrument_ts ON iv_snapshots(instrument, timestamp);
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
        """)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()

    async def save_spot_price(self, exchange: str, price: float, timestamp: datetime) -> None:
        assert self._conn
        await self._conn.execute(
            "INSERT INTO spot_prices (exchange, price, timestamp) VALUES (?, ?, ?)",
            (exchange, price, timestamp.isoformat()),
        )
        await self._conn.commit()

    async def get_spot_prices(self, exchange: str, limit: int = 1000) -> list[tuple[datetime, float]]:
        assert self._conn
        cursor = await self._conn.execute(
            "SELECT timestamp, price FROM spot_prices WHERE exchange = ? ORDER BY timestamp ASC LIMIT ?",
            (exchange, limit),
        )
        rows = await cursor.fetchall()
        return [(datetime.fromisoformat(row["timestamp"]), row["price"]) for row in rows]

    async def get_spot_prices_since(self, exchange: str, since: datetime) -> list[tuple[datetime, float]]:
        assert self._conn
        cursor = await self._conn.execute(
            "SELECT timestamp, price FROM spot_prices WHERE exchange = ? AND timestamp >= ? ORDER BY timestamp ASC",
            (exchange, since.isoformat()),
        )
        rows = await cursor.fetchall()
        return [(datetime.fromisoformat(row["timestamp"]), row["price"]) for row in rows]

    async def save_iv_snapshot(
        self,
        exchange: str,
        instrument: str,
        strike: float,
        expiry: datetime,
        iv: float,
        timestamp: datetime,
    ) -> None:
        assert self._conn
        await self._conn.execute(
            "INSERT INTO iv_snapshots (exchange, instrument, strike, expiry, iv, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (exchange, instrument, strike, expiry.isoformat(), iv, timestamp.isoformat()),
        )
        await self._conn.commit()

    async def get_iv_snapshots(self, instrument: str, limit: int = 100) -> list[dict]:
        assert self._conn
        cursor = await self._conn.execute(
            "SELECT * FROM iv_snapshots WHERE instrument = ? ORDER BY timestamp DESC LIMIT ?",
            (instrument, limit),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def save_alert(self, rule: str, instrument: str, details: str, timestamp: datetime) -> None:
        assert self._conn
        await self._conn.execute(
            "INSERT INTO alerts (rule, instrument, details, timestamp) VALUES (?, ?, ?, ?)",
            (rule, instrument, details, timestamp.isoformat()),
        )
        await self._conn.commit()

    async def get_alerts(self, limit: int = 50) -> list[dict]:
        assert self._conn
        cursor = await self._conn.execute("SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?", (limit,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

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

    async def prune(self, days: int = 90) -> None:
        assert self._conn
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        await self._conn.execute("DELETE FROM spot_prices WHERE timestamp < ?", (cutoff,))
        await self._conn.execute("DELETE FROM iv_snapshots WHERE timestamp < ?", (cutoff,))
        await self._conn.execute("DELETE FROM alerts WHERE timestamp < ?", (cutoff,))
        await self._conn.execute("DELETE FROM ohlc WHERE timestamp < ?", (cutoff,))
        await self._conn.execute("DELETE FROM dvol_history WHERE timestamp < ?", (cutoff,))
        await self._conn.execute("DELETE FROM regime_log WHERE timestamp < ?", (cutoff,))
        await self._conn.commit()
