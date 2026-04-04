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
        if len(dvol_history) < 10:
            return Regime.NORMAL, 0.0

        arr = np.array(dvol_history[-self._lookback:])
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1))

        if std < 1e-8:
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
