import errno
from collections.abc import Callable
from typing import Protocol, cast

import serial
from serial.tools import list_ports

from muscle_monitor.sources.base import SourceError


class SerialTransport(Protocol):
    dtr: bool
    rts: bool
    port: str | None

    def open(self) -> None: ...

    def read(self, size: int) -> bytes: ...

    def close(self) -> None: ...


def available_ports() -> list[tuple[str, str]]:
    """Enumera portas; não abre dispositivos."""
    return [(port.device, port.description) for port in list_ports.comports()]


def _port_error(error: OSError) -> SourceError:
    description = str(error).lower()
    if error.errno in (errno.EACCES, errno.EPERM) or any(
        word in description for word in ("permission", "access is denied", "errno 13")
    ):
        return SourceError(
            "Permissão negada ou porta em uso. Feche outros monitores. "
            "No Linux, confira as permissões da porta com o administrador; "
            "não execute como root."
        )
    if error.errno == errno.EBUSY or "busy" in description:
        return SourceError("Porta ocupada. Feche outro programa que esteja usando o dispositivo.")
    return SourceError(
        "Dispositivo desconectado ou porta indisponível. "
        "Confira a porta e reconecte explicitamente."
    )


class SerialSource:
    def __init__(
        self,
        port: str,
        baudrate: int,
        serial_factory: Callable[..., SerialTransport] | None = None,
    ) -> None:
        if not port.strip() or not 300 <= baudrate <= 4_000_000:
            raise ValueError("Selecione uma porta e um baud rate entre 300 e 4.000.000")
        self._name = port
        self._baudrate = baudrate
        self._factory = serial_factory or cast(Callable[..., SerialTransport], serial.Serial)
        self._port: SerialTransport | None = None

    def open(self) -> None:
        try:
            self._port = self._factory(
                port=None,
                baudrate=self._baudrate,
                timeout=0.1,
                write_timeout=0.1,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False,
            )
            # Drivers podem produzir pulsos mesmo configurando as linhas antes de abrir.
            self._port.dtr = False
            self._port.rts = False
            self._port.port = self._name
            self._port.open()
        except OSError as error:
            raise _port_error(error) from error

    def read(self) -> bytes:
        if self._port is None:
            raise SourceError("Porta não está aberta")
        try:
            return self._port.read(4096)
        except OSError as error:
            raise _port_error(error) from error

    def close(self) -> None:
        if self._port is not None:
            try:
                self._port.close()
            except OSError as error:
                raise _port_error(error) from error
            finally:
                self._port = None
