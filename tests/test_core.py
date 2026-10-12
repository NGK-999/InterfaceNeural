import numpy as np
import pytest

from muscle_monitor.core.buffer import SignalBuffer
from muscle_monitor.core.continuity import Continuity, StreamReset
from muscle_monitor.core.models import Batch


def batch(seq=0, t0=0, dt=1000, samples=(10, 20, 30)):
    return Batch(seq=seq, t0_us=t0, dt_us=dt, samples=samples)


def test_continuity_counts_loss_without_inventing_samples():
    tracker = Continuity()
    assert not tracker.accept(batch()).gap_before
    result = tracker.accept(batch(seq=5, t0=5000))
    assert result.gap_before
    assert tracker.missing_samples == 2
    assert tracker.gaps == 1
    assert tracker.accept(batch(seq=5, t0=5000)) is None
    assert tracker.duplicates == 1


@pytest.mark.parametrize("next_batch", [batch(), batch(seq=3, t0=0)])
def test_restart_or_time_regression_requires_reconnect(next_batch):
    tracker = Continuity()
    tracker.accept(batch())
    tracker.accept(batch(seq=3, t0=3000))
    with pytest.raises(StreamReset):
        tracker.accept(next_batch)


def test_inconsistent_interval_is_rejected():
    tracker = Continuity()
    tracker.accept(batch())
    assert tracker.accept(batch(seq=3, t0=3001)) is None
    assert tracker.accept(batch(seq=3, t0=3000, dt=500)) is None
    assert tracker.errors == 2
    assert tracker.accept(batch(seq=3, t0=3000)).gap_before is False


def test_ring_window_uses_source_time_and_breaks_gaps():
    buffer = SignalBuffer(capacity=8, window_seconds=10)
    buffer.append(batch())
    buffer.append(batch(seq=5, t0=5000), gap_before=True)
    times, values = buffer.plot_data()
    np.testing.assert_allclose(times, [0, 0.001, 0.002, 0.005, 0.005, 0.006, 0.007])
    np.testing.assert_allclose(values, [10, 20, 30, np.nan, 10, 20, 30])
    assert len(buffer) == 6


def test_capacity_eviction_counts_only_samples_still_in_time_window():
    buffer = SignalBuffer(capacity=5, window_seconds=10)
    buffer.append(batch())
    buffer.append(batch(seq=3, t0=3000))
    assert len(buffer) == 5
    assert buffer.capacity_dropped == 1
    np.testing.assert_allclose(buffer.plot_data()[1], [20, 30, 10, 20, 30])
    buffer.append(batch(seq=11000, t0=11_000_000))
    assert len(buffer) == 3
    assert buffer.capacity_dropped == 1


def test_ring_wrap_and_ten_second_expiry():
    buffer = SignalBuffer(capacity=100, window_seconds=10)
    for second in range(60):
        buffer.append(batch(seq=second * 3, t0=second * 1_000_000))
    times, _ = buffer.plot_data()
    assert len(buffer) == 31
    assert times[0] == 49.002
    assert times[-1] == 59.002
    assert buffer.capacity_dropped == 0
