from threading import Event
from time import monotonic

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from muscle_monitor.sources.base import SourceError
from muscle_monitor.ui.window import MonitorWindow
from tests.fakes import MemorySource
from tests.test_protocol import line


def wait_ui(app, condition, timeout=3):
    deadline = monotonic() + timeout
    while not condition():
        app.processEvents()
        assert monotonic() < deadline, "Interface não atingiu o estado esperado"
        QTest.qWait(5)


def test_default_is_disconnected_and_simulation_visible(qt_app):
    window = MonitorWindow()
    window.show()
    qt_app.processEvents()
    assert window.source_combo.currentText() == "Simulador"
    assert not window.acquisition.running
    assert "SIMULAÇÃO — DADOS ARTIFICIAIS" in window.origin_label.text()
    assert "desconectado" in window.state_label.text().lower()
    assert window.plot.getPlotItem().getAxis("left").labelText == "Contagens do ADC"
    window.close()
    assert not window.isVisible()


def test_pause_keeps_acquiring_and_resume_shows_latest_window(qt_app):
    window = MonitorWindow()
    window.show()
    QTest.mouseClick(window.connect_button, Qt.MouseButton.LeftButton)
    try:
        wait_ui(qt_app, lambda: len(window.buffer) >= 100)
        QTest.mouseClick(window.pause_button, Qt.MouseButton.LeftButton)
        frozen_x = window.curve.getData()[0].copy()
        old_count = window.acquisition.snapshot().total_samples
        wait_ui(qt_app, lambda: window.acquisition.snapshot().total_samples >= old_count + 200)
        np.testing.assert_array_equal(window.curve.getData()[0], frozen_x)
        QTest.mouseClick(window.pause_button, Qt.MouseButton.LeftButton)
        wait_ui(qt_app, lambda: window.curve.getData()[0][-1] > frozen_x[-1] + 0.1)
        assert len(window.buffer) <= window.buffer.capacity
    finally:
        window.close()
        wait_ui(qt_app, lambda: not window.acquisition.running and not window.isVisible())


def test_serial_failure_keeps_source_and_reconnect_is_explicit(qt_app):
    source = MemorySource([line()], SourceError("Dispositivo desconectado. Reconecte."))
    calls = []

    def factory(port, baud):
        calls.append((port, baud))
        return source

    window = MonitorWindow(serial_factory=factory, ports_provider=lambda: [("FAKE", "Memória")])
    window.show()
    window.source_combo.setCurrentText("Serial")
    window.refresh_ports()
    QTest.mouseClick(window.connect_button, Qt.MouseButton.LeftButton)
    wait_ui(qt_app, lambda: "erro" in window.state_label.text().lower())
    assert window.source_combo.currentText() == "Serial"
    assert "SIMULAÇÃO" not in window.origin_label.text()
    assert window.acquisition.snapshot().total_samples == 3
    assert len(calls) == 1
    assert source.closed.is_set()
    window.close()


def test_switching_source_clears_old_signal_identity(qt_app):
    window = MonitorWindow()
    window.show()
    window.connect_button.click()
    wait_ui(qt_app, lambda: len(window.buffer) >= 100)
    window.disconnect_button.click()
    wait_ui(qt_app, lambda: not window.acquisition.running)
    window.source_combo.setCurrentText("Serial")
    assert len(window.buffer) == 0
    assert window.curve.getData()[0] is None
    assert window.acquisition.snapshot().total_samples == 0
    window.close()


def test_manual_scale_and_live_return(qt_app):
    window = MonitorWindow()
    window.show()
    window.auto_scale.setChecked(False)
    window.y_min.setValue(100)
    window.y_max.setValue(900)
    qt_app.processEvents()
    assert window.plot.viewRange()[1] == [100, 900]
    window.plot.setXRange(1, 2, padding=0)
    window.live_button.click()
    assert window.plot.viewRange()[0] == [0, 10]
    window.close()


def test_long_session_keeps_time_axis_in_seconds(qt_app):
    window = MonitorWindow()
    window.show()
    window.plot.setXRange(10000, 10010, padding=0)
    qt_app.processEvents()
    assert window.plot.getAxis("bottom").label.toPlainText() == "Tempo da fonte (s)"
    window.close()


def test_manually_edited_port_is_the_one_opened(qt_app):
    calls = []
    source = MemorySource()

    def factory(port, baud):
        calls.append(port)
        return source

    window = MonitorWindow(serial_factory=factory, ports_provider=lambda: [("OLD", "Anterior")])
    window.show()
    window.source_combo.setCurrentText("Serial")
    window.refresh_ports()
    window.port_combo.setEditText("NOVA PORTA")
    window.connect_button.click()
    try:
        assert calls == ["NOVA PORTA"]
    finally:
        window.close()
        wait_ui(qt_app, lambda: not window.acquisition.running and not window.isVisible())


def test_close_during_connection_stays_responsive_and_cleans_up(qt_app):
    release = Event()
    entered = Event()

    class SlowOpenSource(MemorySource):
        def open(self):
            entered.set()
            assert release.wait(2)
            super().open()

    source = SlowOpenSource()
    window = MonitorWindow(serial_factory=lambda *_: source)
    window.show()
    window.source_combo.setCurrentText("Serial")
    window.port_combo.setEditText("FAKE")
    window.connect_button.click()
    try:
        assert entered.wait(1)
        window.close()
        assert window.isVisible()
        assert window.acquisition.running
        qt_app.processEvents()
    finally:
        release.set()
        wait_ui(qt_app, lambda: not window.acquisition.running and not window.isVisible())
    assert source.closed.is_set()


def test_pause_beyond_window_does_not_replay_old_samples(qt_app):
    source = MemorySource([line(samples=[1] * 100, dt_us=500)])
    window = MonitorWindow(serial_factory=lambda *_: source)
    window.show()
    window.source_combo.setCurrentText("Serial")
    window.port_combo.setEditText("FAKE")
    window.connect_button.click()
    try:
        wait_ui(qt_app, lambda: len(window.buffer) == 100)
        window.pause_button.click()
        old_times = window.curve.getData()[0].copy()
        # 15 s de tempo da fonte entregues em grupos limitados, sem esperar 15 s reais.
        for group in range(15):
            first = 100 + group * 2000
            source.chunks.extend(
                line(seq=seq, t0_us=seq * 500, dt_us=500, samples=[2] * 100)
                for seq in range(first, first + 2000, 100)
            )
            wait_ui(
                qt_app,
                lambda expected=first + 2000: (
                    window.acquisition.snapshot().total_samples >= expected
                ),
            )
            window.tick()
        np.testing.assert_array_equal(window.curve.getData()[0], old_times)
        assert len(window.buffer) == 20001
        window.return_to_live()
        times = window.curve.getData()[0]
        np.testing.assert_allclose([times[0], times[-1]], [5.0495, 15.0495])
        assert window.acquisition.snapshot().queue_dropped == 0
    finally:
        window.close()
        wait_ui(qt_app, lambda: not window.acquisition.running and not window.isVisible())
