import json
from threading import Event, Lock
from time import monotonic

import numpy as np


class Simulator:
    """Gerador genérico artificial. Não é um modelo fisiológico."""

    def __init__(
        self, sample_rate: int = 1000, intensity: float = 0.5, seed: int | None = None
    ) -> None:
        if sample_rate not in (1000, 2000):
            raise ValueError("O simulador suporta 1000 ou 2000 amostras/s")
        self._rng = np.random.default_rng(seed)
        self._dt = 1_000_000 // sample_rate
        self._batch_size = sample_rate // 50
        self._lock = Lock()
        self._intensity = 0.0
        self.set_intensity(intensity)
        self._closed = Event()
        self._deadline = 0.0
        self.generated = 0

    def set_intensity(self, value: float) -> None:
        if not 0 <= value <= 1:
            raise ValueError("Intensidade deve estar entre zero e um")
        with self._lock:
            self._intensity = value

    def open(self) -> None:
        self._closed.clear()
        self._deadline = monotonic()
        self.generated = 0

    def read(self) -> bytes:
        self._deadline += 0.02
        if self._closed.wait(max(0, self._deadline - monotonic())):
            return b""
        with self._lock:
            intensity = self._intensity
        times = (self.generated + np.arange(self._batch_size)) * self._dt / 1_000_000
        envelope = 0.55 + 0.45 * np.sin(2 * np.pi * 0.3 * times) ** 2
        noise = self._rng.uniform(-0.25, 0.25, self._batch_size)
        values = np.rint(
            2048 + intensity * 1500 * envelope * (0.7 * np.sin(2 * np.pi * 43 * times) + noise)
        ).astype(int)
        data = dict(
            v=1,
            seq=self.generated,
            t0_us=self.generated * self._dt,
            dt_us=self._dt,
            unit="adc_count",
            samples=values.tolist(),
        )
        self.generated += self._batch_size
        return json.dumps(data, separators=(",", ":")).encode("ascii") + b"\n"

    def close(self) -> None:
        self._closed.set()
