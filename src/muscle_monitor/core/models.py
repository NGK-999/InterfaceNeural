from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Batch:
    seq: int
    t0_us: int
    dt_us: int
    samples: tuple[int, ...]

    @property
    def last_us(self) -> int:
        return self.t0_us + (len(self.samples) - 1) * self.dt_us


@dataclass(frozen=True, slots=True)
class Packet:
    batch: Batch
    gap_before: bool = False
