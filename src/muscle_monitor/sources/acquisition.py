import logging
from collections import deque
from dataclasses import dataclass, replace
from threading import Event, Lock, Thread
from time import monotonic

from muscle_monitor.core.continuity import Continuity, StreamReset
from muscle_monitor.core.models import Packet
from muscle_monitor.core.protocol import LineDecoder
from muscle_monitor.sources.base import ByteSource, SourceError

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Statistics:
    state: str = "desconectado"
    message: str = "Escolha a fonte e inicie a aquisição."
    total_samples: int = 0
    errors: int = 0
    gaps: int = 0
    missing_samples: int = 0
    duplicates: int = 0
    queue_dropped: int = 0
    samples_per_second: float = 0.0


class Acquisition:
    def __init__(self, queue_capacity: int = 32, no_data_seconds: float = 2.0) -> None:
        if queue_capacity < 1 or no_data_seconds <= 0:
            raise ValueError("Limites devem ser positivos")
        self.queue_capacity = queue_capacity
        self._timeout = no_data_seconds
        self._queue: deque[Packet] = deque()
        self._lock = Lock()
        self._stop = Event()
        self._thread: Thread | None = None
        self._stats = Statistics()
        self._opened_at: float | None = None
        self._last_valid: float | None = None
        self._rate_at = monotonic()
        self._rate_count = 0

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, source: ByteSource) -> None:
        if self.running:
            raise RuntimeError("Aquisição já está em andamento")
        with self._lock:
            self._queue.clear()
            self._stats = Statistics(state="aguardando dados", message="Conectando à fonte…")
            self._opened_at = self._last_valid = None
            self._rate_at = monotonic()
            self._rate_count = 0
        self._stop.clear()
        self._thread = Thread(target=self._run, args=(source,), name="muscle-acquisition")
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def wait(self, timeout: float) -> bool:
        if self._thread is not None:
            self._thread.join(timeout)
        return not self.running

    def drain(self) -> list[Packet]:
        with self._lock:
            packets = list(self._queue)
            self._queue.clear()
            return packets

    def snapshot(self) -> Statistics:
        now = monotonic()
        with self._lock:
            elapsed = now - self._rate_at
            if elapsed >= 1:
                rate = (self._stats.total_samples - self._rate_count) / elapsed
                self._stats = replace(self._stats, samples_per_second=rate)
                self._rate_count = self._stats.total_samples
                self._rate_at = now
            result = self._stats
            if result.state in ("erro", "desconectado"):
                return replace(result, samples_per_second=0)
            reference = self._last_valid if self._last_valid is not None else self._opened_at
            if reference is not None and now - reference >= self._timeout:
                return replace(
                    result,
                    state="sem dados",
                    samples_per_second=0,
                    message="Sem amostras válidas há 2 s. Confira fonte, baud rate e contrato V1."
                    if self._timeout == 2
                    else "Sem amostras válidas no intervalo de timeout.",
                )
            return result

    def _publish(self, packet: Packet) -> None:
        if len(self._queue) >= self.queue_capacity:
            discarded = self._queue.popleft()
            self._stats = replace(
                self._stats, queue_dropped=self._stats.queue_dropped + len(discarded.batch.samples)
            )
            if self._queue:
                self._queue[0] = replace(self._queue[0], gap_before=True)
            else:
                packet = replace(packet, gap_before=True)
        self._queue.append(packet)
        self._last_valid = monotonic()
        self._stats = replace(
            self._stats,
            state="recebendo",
            message="Recebendo amostras válidas.",
            total_samples=self._stats.total_samples + len(packet.batch.samples),
        )

    def _fail(self, message: str) -> None:
        with self._lock:
            self._stats = replace(self._stats, state="erro", message=message)
        logger.error("Aquisição interrompida: %s", message)

    def _run(self, source: ByteSource) -> None:
        decoder = LineDecoder()
        continuity = Continuity()
        next_error_log = 0.0
        try:
            source.open()
            with self._lock:
                self._opened_at = monotonic()
                self._stats = replace(
                    self._stats, message="Fonte aberta. Aguardando dados válidos."
                )
            while not self._stop.is_set():
                data = source.read()
                if not data:
                    continue
                batches = decoder.feed(data)
                with self._lock:
                    previous_errors = self._stats.errors
                    try:
                        for batch in batches:
                            packet = continuity.accept(batch)
                            if packet is not None:
                                self._publish(packet)
                    finally:
                        # Um reset pode ocorrer no mesmo bloco após erros ou lacunas válidas.
                        self._stats = replace(
                            self._stats,
                            errors=decoder.errors + continuity.errors,
                            gaps=continuity.gaps,
                            missing_samples=continuity.missing_samples,
                            duplicates=continuity.duplicates,
                        )
                    errors = decoder.errors + continuity.errors
                    if errors > previous_errors:
                        self._stats = replace(
                            self._stats,
                            message="Formato incompatível: confira baud rate e contrato NDJSON V1.",
                        )
                        if monotonic() >= next_error_log:
                            logger.warning("Mensagens incompatíveis descartadas; total=%d", errors)
                            next_error_log = monotonic() + 5
        except (SourceError, StreamReset) as error:
            self._fail(str(error))
        except Exception as error:
            # Fronteira do worker: preserva fechamento e não vaza bytes/nomes da porta no log.
            self._fail(f"Falha interna de aquisição ({type(error).__name__}). Reconecte a fonte.")
        finally:
            try:
                source.close()
            except Exception as error:
                self._fail(f"Falha ao fechar a fonte ({type(error).__name__}).")
            with self._lock:
                if self._stats.state != "erro":
                    self._stats = replace(
                        self._stats, state="desconectado", message="Aquisição encerrada."
                    )
