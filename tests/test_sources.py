import errno
from threading import enumerate as threads

import pytest

from muscle_monitor.core.protocol import LineDecoder
from muscle_monitor.sources.acquisition import Acquisition
from muscle_monitor.sources.serial_source import SerialSource
from muscle_monitor.sources.simulator import Simulator
from tests.fakes import MemorySource, until
from tests.test_protocol import line


def test_simulator_is_reproducible_and_intensity_changes_amplitude():
    low = Simulator(seed=42, intensity=0)
    high = Simulator(seed=42, intensity=1)
    same = Simulator(seed=42, intensity=1)
    try:
        for source in (low, high, same):
            source.open()
        low_batch = LineDecoder().feed(low.read())[0]
        high_data = high.read()
        assert high_data == same.read()
        high_batch = LineDecoder().feed(high_data)[0]
        assert low_batch.samples == (2048,) * 20
        assert max(high_batch.samples) - min(high_batch.samples) > 100
        assert high_batch.dt_us == 1000
    finally:
        for source in (low, high, same):
            source.close()


def test_worker_parses_fragmentation_and_closes_cleanly():
    data = line()
    source = MemorySource([b"boot\n", data[:10], data[10:] + line(seq=5, t0_us=5000)])
    acquisition = Acquisition()
    acquisition.start(source)
    try:
        until(lambda: acquisition.snapshot().total_samples == 6)
        stats = acquisition.snapshot()
        assert stats.state == "recebendo"
        assert stats.errors == 1
        assert stats.missing_samples == 2
        packets = acquisition.drain()
        assert len(packets) == 2
        assert packets[1].gap_before
    finally:
        acquisition.stop()
        assert acquisition.wait(1)
    assert source.closed.is_set()
    assert acquisition.snapshot().state == "desconectado"


def test_queue_overload_discards_oldest_and_marks_visible_gap():
    source = MemorySource([line(seq=i * 3, t0_us=i * 3000) for i in range(20)])
    acquisition = Acquisition(queue_capacity=2)
    acquisition.start(source)
    try:
        until(lambda: acquisition.snapshot().total_samples == 60)
        packets = acquisition.drain()
        assert len(packets) == 2
        assert packets[0].batch.seq == 54
        assert packets[0].gap_before
        assert acquisition.snapshot().queue_dropped == 54
    finally:
        acquisition.stop()
        assert acquisition.wait(1)


def test_open_port_is_not_receiving_and_invalid_data_cannot_refresh_timeout():
    source = MemorySource()
    acquisition = Acquisition(no_data_seconds=0.03)
    acquisition.start(source)
    try:
        assert source.opened.wait(1)
        assert acquisition.snapshot().state == "aguardando dados"
        until(lambda: acquisition.snapshot().state == "sem dados")
        source.chunks.extend([b"boot\n"] * 50)
        until(lambda: acquisition.snapshot().errors == 50)
        assert acquisition.snapshot().state == "sem dados"
        source.chunks.append(line())
        until(lambda: acquisition.snapshot().state == "recebendo")
    finally:
        acquisition.stop()
        assert acquisition.wait(1)


def test_restart_stops_worker_and_does_not_change_source():
    source = MemorySource([line(), line(seq=3, t0_us=3000), line()])
    acquisition = Acquisition()
    acquisition.start(source)
    assert acquisition.wait(1)
    assert source.closed.is_set()
    assert acquisition.snapshot().state == "erro"
    assert acquisition.snapshot().total_samples == 6
    assert "Reconecte" in acquisition.snapshot().message


@pytest.mark.parametrize("fragmented", [False, True])
def test_reset_keeps_counters_detected_in_same_read(fragmented):
    chunks = [b"boot\n", line(), line(seq=5, t0_us=5000), line()]
    source = MemorySource(chunks if fragmented else [b"".join(chunks)])
    acquisition = Acquisition()
    acquisition.start(source)
    assert acquisition.wait(1)
    stats = acquisition.snapshot()
    assert stats.state == "erro"
    assert stats.errors == 1
    assert stats.gaps == 1
    assert stats.missing_samples == 2


def test_repeated_connection_leaves_no_workers():
    acquisition = Acquisition()
    for _ in range(5):
        source = MemorySource([line()])
        acquisition.start(source)
        until(lambda: acquisition.snapshot().total_samples == 3)
        acquisition.stop()
        assert acquisition.wait(1)
        assert source.closed.is_set()
    assert not any(t.name == "muscle-acquisition" for t in threads())


class FakeSerial:
    def __init__(self, **kwargs):
        assert kwargs["port"] is None
        assert 0 < kwargs["timeout"] <= 0.2
        assert kwargs["xonxoff"] is False
        assert kwargs["rtscts"] is False
        assert kwargs["dsrdtr"] is False
        self.dtr = self.rts = True
        self.port = None
        self.opened = False
        self.closed = False

    def open(self):
        assert self.dtr is False and self.rts is False
        assert self.port == "PORTA FALSA"
        self.opened = True

    def read(self, size):
        assert size <= 4096
        return line()

    def close(self):
        self.closed = True


def test_serial_sets_control_lines_before_open_and_never_writes():
    created = []

    def factory(**kwargs):
        port = FakeSerial(**kwargs)
        created.append(port)
        return port

    source = SerialSource("PORTA FALSA", 115200, serial_factory=factory)
    source.open()
    assert LineDecoder().feed(source.read())[0].samples == (2048, 2051, 2046)
    source.close()
    assert created[0].opened and created[0].closed


@pytest.mark.parametrize(
    "number, message",
    [
        (errno.EACCES, "Permissão"),
        (errno.EBUSY, "ocupada"),
        (errno.ENODEV, "desconectado"),
    ],
)
def test_serial_open_errors_are_useful_and_resources_closed(number, message):
    port = FakeSerial(port=None, timeout=0.1, xonxoff=False, rtscts=False, dsrdtr=False)

    def fail():
        raise OSError(number, "private port info")

    port.open = fail
    source = SerialSource("PORTA FALSA", 115200, serial_factory=lambda **_: port)
    acquisition = Acquisition()
    acquisition.start(source)
    assert acquisition.wait(1)
    assert acquisition.snapshot().state == "erro"
    assert message in acquisition.snapshot().message
    assert "private" not in acquisition.snapshot().message
    assert port.closed
