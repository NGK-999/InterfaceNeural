from collections import deque
from threading import Event
from time import monotonic, sleep


class MemorySource:
    """Transporte falso: nunca importa ou abre uma porta física."""

    def __init__(self, chunks=(), error=None):
        self.chunks = deque(chunks)
        self.error = error
        self.opened = Event()
        self.closed = Event()

    def open(self):
        self.opened.set()

    def read(self):
        if self.chunks:
            return self.chunks.popleft()
        if self.error:
            raise self.error
        self.closed.wait(0.005)
        return b""

    def close(self):
        self.closed.set()


def until(condition, timeout=2):
    deadline = monotonic() + timeout
    while not condition():
        assert monotonic() < deadline, "Condição não atingida no prazo"
        sleep(0.005)
