from __future__ import annotations
import asyncio, json, logging
from datetime import datetime, timezone
import websockets
from websockets.asyncio.client import ClientConnection
from src.exchanges.base import Exchange
from src.models import OptionTicker

logger = logging.getLogger(__name__)

class OkxExchange(Exchange):
    def __init__(self, ws_url: str = "wss://ws.okx.com:8443/ws/v5/public") -> None:
        super().__init__(name="okx", ws_url=ws_url)
        self._ws: ClientConnection | None = None
        self._running = False

    @staticmethod
    def parse_instrument(inst_id: str) -> tuple[float, datetime, str]:
        parts = inst_id.split("-")
        date_str = parts[2]
        year = 2000 + int(date_str[:2])
        month = int(date_str[2:4])
        day = int(date_str[4:6])
        strike = float(parts[3])
        option_type = "call" if parts[4] == "C" else "put"
        expiry = datetime(year, month, day, 8, 0, tzinfo=timezone.utc)
        return strike, expiry, option_type

    def parse_ticker(self, data: dict) -> OptionTicker | None:
        try:
            inst_id = data["instId"]
            strike, expiry, option_type = self.parse_instrument(inst_id)
            iv_decimal = float(data.get("markVol", 0))
            iv_pct = iv_decimal * 100
            return OptionTicker(
                exchange="okx", instrument=inst_id,
                underlying_price=float(data.get("fwdPx", 0)),
                strike=strike, expiry=expiry, option_type=option_type,
                mark_price=float(data.get("markPx", 0)),
                bid=float(data.get("bidPx", 0) or 0),
                ask=float(data.get("askPx", 0) or 0),
                iv=iv_pct,
                volume_24h=0.0, open_interest=0.0,
                timestamp=datetime.fromtimestamp(int(data["ts"]) / 1000, tz=timezone.utc))
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Failed to parse OKX ticker: %s", e)
            return None

    async def connect(self) -> None:
        self._running = True
        backoff = 1
        while self._running:
            try:
                self._ws = await websockets.connect(self.ws_url)
                self._connected = True
                backoff = 1
                break
            except Exception as e:
                logger.warning("OKX connect failed: %s, retry in %ds", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def disconnect(self) -> None:
        self._running = False
        self._connected = False
        if self._ws:
            await self._ws.close()

    async def subscribe_options(self, symbol: str) -> None:
        if not self._ws: return
        msg = {"op": "subscribe", "args": [{"channel": "opt-summary", "instFamily": f"{symbol}-USD"}]}
        await self._ws.send(json.dumps(msg))

    async def listen(self) -> None:
        if not self._ws: return
        try:
            async for raw in self._ws:
                if raw == "ping":
                    await self._ws.send("pong")
                    continue
                msg = json.loads(raw)
                if msg.get("event") == "subscribe":
                    continue
                for tick_data in msg.get("data", []):
                    ticker = self.parse_ticker(tick_data)
                    if ticker:
                        self._emit(ticker)
        except websockets.ConnectionClosed:
            self._connected = False
