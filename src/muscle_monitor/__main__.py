import argparse
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from muscle_monitor.ui.window import MonitorWindow


def configure_logging() -> None:
    if sys.platform == "win32":
        directory = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "MuscleMonitor" / "logs"
    else:
        directory = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
        directory = directory / "muscle-monitor"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            directory / "technical.log", maxBytes=128 * 1024, backupCount=2, encoding="utf-8"
        )
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logging.basicConfig(level=logging.WARNING, handlers=[handler])


def main() -> int:
    parser = argparse.ArgumentParser(description="Monitor desktop de sinais — V1")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Abre, exercita o simulador e fecha a interface; não acessa dispositivos.",
    )
    options = parser.parse_args()
    configure_logging()
    app = QApplication(sys.argv[:1])
    app.setApplicationName("MuscleMonitor")
    window = MonitorWindow()
    window.show()
    if options.smoke_test:
        QTimer.singleShot(100, window.start_acquisition)
        QTimer.singleShot(1200, window.close)
    result = app.exec()
    if options.smoke_test:
        stats = window.acquisition.snapshot()
        if stats.total_samples < 100 or stats.state == "erro" or window.acquisition.running:
            return 1
    return result


if __name__ == "__main__":
    raise SystemExit(main())
