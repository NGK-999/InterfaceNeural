from typing import Protocol


class SourceError(Exception):
    """Erro técnico seguro para exibir, sem conteúdo bruto do dispositivo."""


class ByteSource(Protocol):
    def open(self) -> None: ...

    def read(self) -> bytes: ...

    def close(self) -> None: ...
