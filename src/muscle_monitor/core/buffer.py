"""Janela circular limitada em tempo e em capacidade; sem processamento do sinal."""

import numpy as np
from numpy.typing import NDArray

from muscle_monitor.core.models import Batch


class SignalBuffer:
    def __init__(self, capacity: int = 40_000, window_seconds: float = 10) -> None:
        if capacity < 1 or window_seconds <= 0:
            raise ValueError("Capacidade e janela devem ser positivas")
        self.capacity = capacity
        self.window_us = int(window_seconds * 1_000_000)
        self._times = np.empty(capacity, dtype=np.int64)
        self._values = np.empty(capacity, dtype=np.float64)
        self._breaks = np.zeros(capacity, dtype=np.bool_)
        self._head = 0
        self._size = 0
        self.capacity_dropped = 0

    def __len__(self) -> int:
        return self._size

    def _remove(self, count: int) -> None:
        self._head = (self._head + count) % self.capacity
        self._size -= count

    def _expire(self, cutoff: int) -> None:
        low, high = 0, self._size
        while low < high:
            middle = (low + high) // 2
            if self._times[(self._head + middle) % self.capacity] < cutoff:
                low = middle + 1
            else:
                high = middle
        self._remove(low)

    def append(self, batch: Batch, gap_before: bool = False) -> None:
        cutoff = batch.last_us - self.window_us
        self._expire(cutoff)
        first = max(0, (cutoff - batch.t0_us + batch.dt_us - 1) // batch.dt_us)
        count = len(batch.samples) - first
        overflow = max(0, self._size + count - self.capacity)
        self.capacity_dropped += overflow
        self._remove(min(overflow, self._size))
        if count > self.capacity:
            first += count - self.capacity
            count = self.capacity
        positions = (self._head + self._size + np.arange(count)) % self.capacity
        self._times[positions] = batch.t0_us + np.arange(first, first + count) * batch.dt_us
        self._values[positions] = batch.samples[first:]
        self._breaks[positions] = False
        self._breaks[positions[0]] = gap_before
        self._size += count

    def plot_data(self) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        positions = (self._head + np.arange(self._size)) % self.capacity
        times = self._times[positions].astype(np.float64) / 1_000_000
        values = self._values[positions].copy()
        gaps = np.flatnonzero(self._breaks[positions])
        gaps = gaps[gaps > 0]
        if gaps.size:
            times = np.insert(times, gaps, times[gaps])
            values = np.insert(values, gaps, np.nan)
        return times, values
