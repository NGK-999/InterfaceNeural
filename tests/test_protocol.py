import json

import pytest

from muscle_monitor.core.protocol import LineDecoder


def line(**changes):
    fields = dict(v=1, seq=0, t0_us=0, dt_us=1000, unit="adc_count", samples=[2048, 2051, 2046])
    fields.update(changes)
    return json.dumps(fields, separators=(",", ":")).encode() + b"\n"


def test_partial_and_grouped_messages_preserve_source_timing():
    decoder = LineDecoder()
    data = line()
    assert decoder.feed(data[:17]) == []
    batches = decoder.feed(data[17:] + line(seq=3, t0_us=3000).replace(b"\n", b"\r\n"))
    assert len(batches) == 2
    assert batches[0].samples == (2048, 2051, 2046)
    assert batches[1].seq == 3
    assert batches[1].t0_us == 3000
    assert batches[1].last_us == 5000
    assert decoder.errors == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"v": 2},
        {"v": True},
        {"seq": -1},
        {"seq": 1.0},
        {"seq": True},
        {"seq": 2**53},
        {"t0_us": -1},
        {"t0_us": 2**53},
        {"t0_us": 2**53 - 2},
        {"dt_us": 0},
        {"dt_us": 1_000_001},
        {"dt_us": False},
        {"unit": "mV"},
        {"samples": []},
        {"samples": [0] * 129},
        {"samples": [True]},
        {"samples": [-1]},
        {"samples": [1.2]},
        {"samples": [2**32]},
        {"samples": [float("nan")]},
        {"samples": [float("inf")]},
        {"samples": "123"},
        {"seq": 2**53 - 2},
    ],
)
def test_rejects_invalid_fields_and_recovers(changes):
    decoder = LineDecoder()
    assert len(decoder.feed(line(**changes) + line())) == 1
    assert decoder.errors == 1


@pytest.mark.parametrize(
    "bad",
    [
        b"boot ESP32\n",
        b"\xff\xfe\n",
        b"[]\n",
        b"null\n",
        b"{}\n",
        b"\n",
        b'{"v":1,"v":1}\n',
        b"[" * 1500 + b"]" * 1500 + b"\n",
    ],
)
def test_noise_and_bad_structure_do_not_escape(bad):
    decoder = LineDecoder()
    assert len(decoder.feed(bad + line())) == 1
    assert decoder.errors == 1


def test_oversize_line_discarded_through_lf_with_bounded_memory():
    decoder = LineDecoder()
    assert decoder.feed(b"x" * 8192) == []
    assert decoder.pending_bytes <= 8192
    for _ in range(100):
        assert decoder.feed(b"x" * 4096) == []
        assert decoder.pending_bytes <= 8192
    assert decoder.errors == 1
    assert decoder.feed(line()) == []  # Still part of the oversized line.
    assert len(decoder.feed(line())) == 1
    assert decoder.errors == 1


def test_exact_line_limit_and_numeric_limits():
    decoder = LineDecoder()
    payload = line(samples=[2**32 - 1], seq=2**53 - 1, t0_us=2**53 - 1, dt_us=1_000_000)[:-1]
    assert len(decoder.feed(payload + b" " * (8192 - len(payload)) + b"\n")) == 1
    assert decoder.errors == 0
