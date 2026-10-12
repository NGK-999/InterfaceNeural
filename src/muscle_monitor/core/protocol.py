"""NDJSON estrito, incremental e limitado; nunca registra o conteúdo recebido."""

import json

from muscle_monitor.core.models import Batch

MAX_LINE_BYTES = 8192
MAX_INDEX = 2**53 - 1
MAX_SAMPLE = 2**32 - 1
MAX_INTERVAL_US = 1_000_000
FIELDS = {"v", "seq", "t0_us", "dt_us", "unit", "samples"}


def _integer(value: object, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError("Campo inteiro fora dos limites")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Campo repetido")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError("Constante JSON inválida")


def parse_line(data: bytes) -> Batch:
    obj = json.loads(
        data.decode("utf-8"), object_pairs_hook=_unique_object, parse_constant=_reject_constant
    )
    if not isinstance(obj, dict) or set(obj) != FIELDS:
        raise ValueError("Objeto incompatível")
    _integer(obj["v"], 1, 1)
    seq = _integer(obj["seq"], 0, MAX_INDEX)
    t0 = _integer(obj["t0_us"], 0, MAX_INDEX)
    dt = _integer(obj["dt_us"], 1, MAX_INTERVAL_US)
    if obj["unit"] != "adc_count":
        raise ValueError("Unidade incompatível")
    raw = obj["samples"]
    if not isinstance(raw, list) or not 1 <= len(raw) <= 128:
        raise ValueError("Lote incompatível")
    samples = tuple(_integer(value, 0, MAX_SAMPLE) for value in raw)
    if seq + len(samples) - 1 > MAX_INDEX or t0 + (len(samples) - 1) * dt > MAX_INDEX:
        raise ValueError("Última amostra fora dos limites")
    return Batch(seq, t0, dt, samples)


class LineDecoder:
    def __init__(self) -> None:
        self._pending = bytearray()
        self._discarding = False
        self.errors = 0

    @property
    def pending_bytes(self) -> int:
        return len(self._pending)

    def feed(self, data: bytes) -> list[Batch]:
        batches: list[Batch] = []
        start = 0
        while start < len(data):
            newline = data.find(b"\n", start)
            end = newline if newline >= 0 else len(data)
            if not self._discarding:
                if len(self._pending) + end - start > MAX_LINE_BYTES:
                    self.errors += 1
                    self._pending.clear()
                    self._discarding = True
                else:
                    self._pending.extend(data[start:end])
            if newline < 0:
                break
            if not self._discarding:
                try:
                    batches.append(parse_line(bytes(self._pending)))
                except (ValueError, UnicodeError, RecursionError):
                    self.errors += 1
            self._pending.clear()
            self._discarding = False
            start = newline + 1
        return batches
