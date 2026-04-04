from __future__ import annotations
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any
from src.models import OptionTicker

class Exchange(ABC):
    def __init__(self, name: str, ws_url: str) -> None:
        self.name = name
        self.ws_url = ws_url
        self._callbacks: list[Callable[[OptionTicker], Any]] = []
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected

    def on_ticker(self, callback: Callable[[OptionTicker], Any]) -> None:
        self._callbacks.append(callback)

    def _emit(self, ticker: OptionTicker) -> None:
        for cb in self._callbacks:
            cb(ticker)

    @abstractmethod
    async def connect(self) -> None: ...
    @abstractmethod
    async def disconnect(self) -> None: ...
    @abstractmethod
    async def subscribe_options(self, symbol: str) -> None: ...
