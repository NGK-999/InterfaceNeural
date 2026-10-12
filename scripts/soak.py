"""Ensaio sintético de GUI; nunca usa portas, arquivos de amostras ou firmware."""

import argparse
import json
import os
import platform
import sys
from importlib.metadata import version
from pathlib import Path
from time import monotonic

import numpy as np
import psutil
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from muscle_monitor.core.models import Packet
from muscle_monitor.sources.acquisition import Acquisition
from muscle_monitor.sources.simulator import Simulator
from muscle_monitor.ui.window import MonitorWindow


class MeasuredAcquisition(Acquisition):
    def __init__(self) -> None:
        super().__init__()
        self.consumed = 0
        self.max_drained_batches = 0

    def drain(self) -> list[Packet]:
        packets = super().drain()
        self.consumed += sum(len(packet.batch.samples) for packet in packets)
        self.max_drained_batches = max(self.max_drained_batches, len(packets))
        return packets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--rate", type=int, choices=(1000, 2000), default=2000)
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("artifacts/soak.json"))
    options = parser.parse_args()
    if options.seconds < 1:
        parser.error("--seconds deve ser pelo menos 1")
    if options.headless:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication([])
    simulator = Simulator(sample_rate=options.rate, seed=2026)
    window = MonitorWindow(simulator_factory=lambda: simulator)
    acquisition = MeasuredAcquisition()
    window.acquisition = acquisition
    process = psutil.Process()
    started = monotonic()
    last_tick = started
    intervals: list[float] = []
    rss: list[int] = []
    max_buffer = 0
    paused = resumed = False
    frozen = None
    pause_count = 0
    pause_verified = resume_verified = False
    result: dict[str, object] = {}
    stopping = False

    def sample() -> None:
        nonlocal last_tick, max_buffer, paused, resumed, frozen, pause_count
        nonlocal pause_verified, resume_verified, stopping
        now = monotonic()
        elapsed = now - started
        intervals.append(now - last_tick)
        last_tick = now
        max_buffer = max(max_buffer, len(window.buffer))
        if elapsed >= options.seconds / 4:
            rss.append(process.memory_info().rss)
        if not paused and elapsed >= options.seconds / 4:
            window.pause_button.click()
            frozen = window.curve.getData()[0].copy()
            pause_count = acquisition.snapshot().total_samples
            paused = True
        if not resumed and elapsed >= options.seconds * 0.6:
            pause_verified = bool(
                acquisition.snapshot().total_samples > pause_count
                and np.array_equal(frozen, window.curve.getData()[0])
            )
            window.return_to_live()
            resumed = True
            resume_verified = bool(window.curve.getData()[0][-1] > frozen[-1])
        if elapsed < options.seconds:
            return
        if not stopping:
            acquisition.stop()
            stopping = True
        if acquisition.running:
            return
        window.tick()
        stats = acquisition.snapshot()
        timer.stop()
        final_times, _ = window.buffer.plot_data()
        memory_growth = max(rss) - min(rss)
        checks = {
            "duration_at_least_requested": elapsed >= options.seconds,
            "sample_accounting": simulator.generated
            == stats.total_samples
            == acquisition.consumed + stats.queue_dropped,
            "bounded_buffer": max_buffer <= window.buffer.capacity,
            "ten_second_window": float(final_times[-1] - final_times[0]) <= 10.000001,
            "no_losses": stats.queue_dropped
            == stats.missing_samples
            == window.buffer.capacity_dropped
            == 0,
            "no_errors": stats.errors == 0,
            "pause_acquires_without_replay": pause_verified and resume_verified,
            "ui_max_interval_under_one_second": max(intervals) < 1,
            "rss_growth_under_32_mib_after_warmup": memory_growth < 32 * 1024**2,
            "worker_stopped": not acquisition.running,
        }
        result.update(
            {
                "platform": platform.platform(),
                "python": sys.version,
                "qt_platform": app.platformName(),
                "versions": {
                    name: version(name)
                    for name in (
                        "PySide6-Essentials",
                        "pyqtgraph",
                        "numpy",
                        "pyserial",
                    )
                },
                "elapsed_seconds": elapsed,
                "requested_samples_per_second": options.rate,
                "generated": simulator.generated,
                "received": stats.total_samples,
                "consumed": acquisition.consumed,
                "queue_dropped": stats.queue_dropped,
                "missing_samples": stats.missing_samples,
                "errors": stats.errors,
                "buffer_max_samples": max_buffer,
                "buffer_capacity_dropped": window.buffer.capacity_dropped,
                "max_drained_batches": acquisition.max_drained_batches,
                "ui_ticks": len(intervals),
                "ui_max_interval_ms": max(intervals) * 1000,
                "ui_p99_interval_ms": float(np.percentile(intervals, 99)) * 1000,
                "rss_min_after_warmup_mib": min(rss) / 1024**2,
                "rss_max_after_warmup_mib": max(rss) / 1024**2,
                "checks": checks,
                "passed": all(checks.values()),
            }
        )
        window.close()

    window.show()
    window.start_acquisition()
    timer = QTimer()
    timer.setInterval(33)
    timer.timeout.connect(sample)
    timer.start()
    try:
        app.exec()
    finally:
        acquisition.stop()
        acquisition.wait(2)
    if not result:
        print("Ensaio interrompido antes de concluir", file=sys.stderr)
        return 1
    options.output.parent.mkdir(parents=True, exist_ok=True)
    options.output.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
