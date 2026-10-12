from muscle_monitor.core.models import Batch, Packet


class StreamReset(Exception):
    """Sequência/tempo regrediu; exige nova conexão explícita."""


class Continuity:
    def __init__(self) -> None:
        self._previous: Batch | None = None
        self.missing_samples = 0
        self.gaps = 0
        self.duplicates = 0
        self.errors = 0

    def accept(self, batch: Batch) -> Packet | None:
        previous = self._previous
        missing = 0
        if previous is not None:
            if batch == previous:
                self.duplicates += 1
                return None
            expected_seq = previous.seq + len(previous.samples)
            if batch.seq < expected_seq or batch.t0_us <= previous.last_us:
                raise StreamReset("Sequência ou tempo regrediu. Reconecte explicitamente.")
            missing = batch.seq - expected_seq
            expected_time = previous.last_us + (missing + 1) * previous.dt_us
            if batch.dt_us != previous.dt_us or batch.t0_us != expected_time:
                self.errors += 1
                return None
        if missing:
            self.gaps += 1
            self.missing_samples += missing
        self._previous = batch
        return Packet(batch, gap_before=missing > 0)
