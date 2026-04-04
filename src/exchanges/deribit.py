from __future__ import annotations
import asyncio, json, logging
from datetime import datetime, timezone
import websockets
from websockets.asyncio.client import ClientConnection
from src.exchanges.base import Exchange
from src.models import OptionTicker

logger = logging.getLogger(__name__)
MONTH_MAP = {"JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
             "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12}

class DeribitExchange(Exchange):
    def __init__(self, ws_url: str = "wss://www.deribit.com/ws/api/v2") -> None:
        super().__init__(name="deribit", ws_url=ws_url)
        self._ws: ClientConnection | None = None
        self._msg_id = 0
        self._running = False

    def _next_id(self) -> int:
        self._msg_id += 1
        return self._msg_id

    @staticmethod
    def parse_instrument(name: str) -> tuple[float, datetime, str]:
        parts = name.split("-")
        date_str = parts[1]
        day = int(date_str[:len(date_str) - 5])
        month_str = date_str[len(date_str) - 5 : len(date_str) - 2]
        year = 2000 + int(date_str[-2:])
        month = MONTH_MAP[month_str.upper()]
        strike = float(parts[2])
        option_type = "call" if parts[3] == "C" else "put"
        expiry = datetime(year, month, day, 8, 0, tzinfo=timezone.utc)
        return strike, expiry, option_type

    def parse_ticker(self, data: dict) -> OptionTicker | None:
        try:
            name = data["instrument_name"]
            strike, expiry, option_type = self.parse_instrument(name)
            return OptionTicker(
                exchange="deribit", instrument=name,
                underlying_price=float(data.get("underlying_price", 0)),
                strike=strike, expiry=expiry, option_type=option_type,
                mark_price=float(data.get("mark_price", 0)),
                bid=float(data.get("best_bid_price", 0)),
                ask=float(data.get("best_ask_price", 0)),
                iv=float(data.get("mark_iv", 0)),
                volume_24h=float(data.get("volume", 0)),
                open_interest=float(data.get("open_interest", 0)),
                timestamp=datetime.fromtimestamp(data["timestamp"] / 1000, tz=timezone.utc))
        except (KeyError, ValueError, TypeError) as e:
            logger.warning("Failed to parse Deribit ticker: %s", e)
            return None

    async def connect(self) -> None:
        self._running = True
        backoff = 1
        while self._running:
            try:
                self._ws = await websockets.connect(self.ws_url)
                self._connected = True
                backoff = 1
                logger.info("Connected to Deribit")
                await self._send_rpc("public/set_heartbeat", {"interval": 30})
                break
            except Exception as e:
                logger.warning("Deribit connect failed: %s, retry in %ds", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def disconnect(self) -> None:
        self._running = False
        self._connected = False
        if self._ws:
            await self._ws.close()

    async def subscribe_options(self, symbol: str) -> None:
        if not self._ws: return
        result = await self._send_rpc("public/get_instruments",
            {"currency": symbol, "kind": "option", "expired": False})
        if not result: return
        instruments = [i["instrument_name"] for i in result]
        for i in range(0, len(instruments), 100):
            batch = instruments[i : i + 100]
            channels = [f"ticker.{inst}.raw" for inst in batch]
            await self._send_rpc("public/subscribe", {"channels": channels})

    async def listen(self) -> None:
        if not self._ws: return
        try:
            async for raw in self._ws:
                msg = json.loads(raw)
                if msg.get("method") == "subscription":
                    data = msg["params"]["data"]
                    ticker = self.parse_ticker(data)
                    if ticker:
                        self._emit(ticker)
                elif msg.get("method") == "heartbeat" and msg.get("params", {}).get("type") == "test_request":
                    await self._send_rpc("public/test", {})
        except websockets.ConnectionClosed:
            self._connected = False

    async def _send_rpc(self, method: str, params: dict) -> list | dict | None:
        if not self._ws: return None
        msg_id = self._next_id()
        payload = {"jsonrpc": "2.0", "id": msg_id, "method": method, "params": params}
        await self._ws.send(json.dumps(payload))
        try:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=10)
            resp = json.loads(raw)
            if resp.get("id") == msg_id:
                return resp.get("result")
        except asyncio.TimeoutError:
            logger.warning("Deribit RPC timeout for %s", method)
        return None
