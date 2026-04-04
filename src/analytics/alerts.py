from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone

from src.models import AlertEvent


class AlertEngine:
    def __init__(
        self,
        iv_rv_ratio_high: float = 1.5,
        iv_rv_ratio_low: float = 0.5,
        cross_exchange_iv_diff: float = 0.05,
        cooldown_minutes: int = 5,
        iv_spike_pct: float = 0.20,
        iv_spike_window_min: int = 30,
    ) -> None:
        self._iv_rv_high = iv_rv_ratio_high
        self._iv_rv_low = iv_rv_ratio_low
        self._cross_diff = cross_exchange_iv_diff
        self._cooldown = timedelta(minutes=cooldown_minutes)
        self._last_alert: dict[tuple[str, str], datetime] = {}
        self._iv_spike_pct = iv_spike_pct
        self._iv_spike_window = timedelta(minutes=iv_spike_window_min)
        self._iv_history: dict[str, deque[tuple[datetime, float]]] = {}

    def _is_cooled_down(self, rule: str, key: str) -> bool:
        cache_key = (rule, key)
        last = self._last_alert.get(cache_key)
        if last is None:
            return True
        return datetime.now(timezone.utc) - last >= self._cooldown

    def _record_alert(self, rule: str, key: str) -> None:
        self._last_alert[(rule, key)] = datetime.now(timezone.utc)

    def check_iv_rv_ratio(self, instrument: str, iv: float, rv: float) -> list[AlertEvent]:
        if rv <= 0:
            return []

        ratio = iv / rv
        alerts: list[AlertEvent] = []
        if ratio > self._iv_rv_high or ratio < self._iv_rv_low:
            if not self._is_cooled_down("iv_rv_ratio", instrument):
                return []

            level = "high" if ratio > self._iv_rv_high else "medium"
            direction = "above" if ratio > self._iv_rv_high else "below"
            threshold = self._iv_rv_high if ratio > self._iv_rv_high else self._iv_rv_low
            alert = AlertEvent(
                timestamp=datetime.now(timezone.utc),
                level=level,
                rule="iv_rv_ratio",
                instrument=instrument,
                message=(
                    f"IV/RV ratio {ratio:.2f} {direction} threshold "
                    f"{threshold} for {instrument}"
                ),
            )
            alerts.append(alert)
            self._record_alert("iv_rv_ratio", instrument)

        return alerts

    def check_cross_exchange_iv(
        self,
        instrument_key: str,
        exchange_a: str,
        iv_a: float,
        exchange_b: str,
        iv_b: float,
    ) -> list[AlertEvent]:
        if iv_a <= 0 or iv_b <= 0:
            return []

        diff = abs(iv_a - iv_b) / max(iv_a, iv_b)
        if diff <= self._cross_diff:
            return []
        if not self._is_cooled_down("cross_exchange_iv", instrument_key):
            return []

        higher_ex = exchange_a if iv_a > iv_b else exchange_b
        lower_ex = exchange_b if iv_a > iv_b else exchange_a
        higher_iv = max(iv_a, iv_b)
        lower_iv = min(iv_a, iv_b)
        alert = AlertEvent(
            timestamp=datetime.now(timezone.utc),
            level="medium",
            rule="cross_exchange_iv",
            instrument=instrument_key,
            message=(
                f"IV divergence {diff:.1%}: {higher_ex} {higher_iv:.1f}% vs "
                f"{lower_ex} {lower_iv:.1f}% for {instrument_key}"
            ),
        )
        self._record_alert("cross_exchange_iv", instrument_key)
        return [alert]

    def check_iv_spike(
        self, instrument: str, iv: float, timestamp: datetime | None = None,
    ) -> list[AlertEvent]:
        now = timestamp or datetime.now(timezone.utc)
        history = self._iv_history.setdefault(instrument, deque())

        # Evict expired entries
        cutoff = now - self._iv_spike_window
        while history and history[0][0] < cutoff:
            history.popleft()

        if history:
            oldest_iv = history[0][1]
            if oldest_iv > 0:
                change_pct = (iv - oldest_iv) / oldest_iv
                if abs(change_pct) >= self._iv_spike_pct:
                    if self._is_cooled_down("iv_spike", instrument):
                        direction = "up" if change_pct > 0 else "down"
                        alert = AlertEvent(
                            timestamp=now,
                            level="high",
                            rule="iv_spike",
                            instrument=instrument,
                            message=(
                                f"IV spike {direction} {abs(change_pct):.1%} "
                                f"({oldest_iv:.1f}→{iv:.1f}) for {instrument}"
                            ),
                        )
                        self._record_alert("iv_spike", instrument)
                        history.append((now, iv))
                        return [alert]

        history.append((now, iv))
        return []
