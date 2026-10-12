import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
import serial


@pytest.fixture(autouse=True)
def forbid_physical_ports(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Testes não podem abrir portas físicas")

    monkeypatch.setattr(serial.Serial, "open", forbidden)


@pytest.fixture(scope="session")
def qt_app():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    return app
