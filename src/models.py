from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class Signal(Enum):
    STRONG_SELL = "STRONG_SELL"
    WEAK_SELL = "WEAK_SELL"
    NEUTRAL = "NEUTRAL"
    WEAK_BUY = "WEAK_BUY"
    STRONG_BUY = "STRONG_BUY"


@dataclass(frozen=True)
class OptionTicker:
    exchange: str
    instrument: str
    underlying_price: float
    strike: float
    expiry: datetime
    option_type: str  # "call" | "put"
    mark_price: float
    bid: float
    ask: float
    iv: float  # percentage, e.g. 68.35 = 68.35%
    volume_24h: float
    open_interest: float
    timestamp: datetime


@dataclass(frozen=True)
class AlertEvent:
    timestamp: datetime
    level: str  # "high" | "medium" | "low"
    rule: str
    instrument: str
    message: str
