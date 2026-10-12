from collections.abc import Callable

import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent, QKeySequence
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from muscle_monitor.core.buffer import SignalBuffer
from muscle_monitor.core.protocol import MAX_SAMPLE
from muscle_monitor.sources.acquisition import Acquisition
from muscle_monitor.sources.base import ByteSource
from muscle_monitor.sources.serial_source import SerialSource, available_ports
from muscle_monitor.sources.simulator import Simulator
from muscle_monitor.ui.style import STYLE


def _label(text: str, buddy: QWidget | None = None) -> QLabel:
    label = QLabel(text)
    if buddy is not None:
        label.setBuddy(buddy)
    return label


def _count(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


class MonitorWindow(QMainWindow):
    def __init__(
        self,
        serial_factory: Callable[[str, int], ByteSource] = SerialSource,
        simulator_factory: Callable[[], Simulator] = Simulator,
        ports_provider: Callable[[], list[tuple[str, str]]] = available_ports,
    ) -> None:
        super().__init__()
        self._serial_factory = serial_factory
        self._simulator_factory = simulator_factory
        self._ports_provider = ports_provider
        self._simulator: Simulator | None = None
        self.acquisition = Acquisition()
        self.buffer = SignalBuffer()
        self._closing = False
        self._following = True
        self._force_render = False
        self._stopping = False
        self.setWindowTitle("Monitor de Sinais Musculares · V1")
        self.resize(1180, 700)
        self.setMinimumSize(850, 560)
        self.setStyleSheet(STYLE)
        body = QWidget()
        self.setCentralWidget(body)
        layout = QVBoxLayout(body)
        layout.setContentsMargins(20, 14, 20, 12)
        layout.setSpacing(10)
        header = QHBoxLayout()
        title = _label("Monitor de sinais")
        title.setObjectName("title")
        header.addWidget(title)
        header.addStretch()
        self.state_label = _label("● Desconectado")
        self.state_label.setObjectName("state")
        header.addWidget(self.state_label)
        layout.addLayout(header)
        self.origin_label = _label("SIMULAÇÃO — DADOS ARTIFICIAIS")
        self.origin_label.setObjectName("origin")
        layout.addWidget(self.origin_label)
        self._build_source_controls(layout)
        self._build_plot_controls(layout)
        pg.setConfigOptions(antialias=False, useOpenGL=False)
        self.plot = pg.PlotWidget(background="#0c141d")
        self.plot.setLabel("left", "Contagens do ADC")
        self.plot.setLabel("bottom", "Tempo da fonte", units="s")
        self.plot.getAxis("bottom").enableAutoSIPrefix(False)
        self.plot.showGrid(x=True, y=True, alpha=0.18)
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(x=True, y=True)
        self.plot.setXRange(0, 10, padding=0)
        self.plot.getPlotItem().hideButtons()
        self.plot.getViewBox().sigRangeChangedManually.connect(self._manual_zoom)
        self.plot.setToolTip("Arraste para mover; use a roda para zoom. Ctrl+L volta ao vivo.")
        self.curve = self.plot.plot(pen=pg.mkPen("#71decd", width=1), connect="finite")
        # Sem downsampling: cada amostra preserva amplitude e lacunas; no máximo 40 mil.
        layout.addWidget(self.plot, 1)
        self.stats_label = _label("")
        self.stats_label.setObjectName("details")
        self.stats_label.setWordWrap(True)
        layout.addWidget(self.stats_label)
        self.message_label = _label("Escolha a fonte e inicie a aquisição.")
        self.message_label.setObjectName("muted")
        self.message_label.setWordWrap(True)
        layout.addWidget(self.message_label)
        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self.tick)
        self.timer.start()
        self.tick()

    def _build_source_controls(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        self.source_combo = QComboBox()
        self.source_combo.addItems(["Simulador", "Serial"])
        row.addWidget(_label("&Fonte", self.source_combo))
        row.addWidget(self.source_combo)
        self.connect_button = QPushButton("&Iniciar")
        self.connect_button.setObjectName("primary")
        self.connect_button.clicked.connect(self.start_acquisition)
        self.disconnect_button = QPushButton("&Desconectar")
        self.disconnect_button.clicked.connect(self.stop_acquisition)
        row.addWidget(self.connect_button)
        row.addWidget(self.disconnect_button)
        row.addStretch()
        channel = _label("CANAL 1  ·  JANELA DE 10 s")
        channel.setObjectName("muted")
        row.addWidget(channel)
        layout.addLayout(row)
        self.source_settings = QStackedWidget()
        simulation = QWidget()
        sim_row = QHBoxLayout(simulation)
        sim_row.setContentsMargins(0, 0, 0, 0)
        self.intensity = QSlider(Qt.Orientation.Horizontal)
        self.intensity.setRange(0, 100)
        self.intensity.setValue(50)
        self.intensity.setMaximumWidth(280)
        self.intensity.setAccessibleName("Intensidade artificial")
        sim_row.addWidget(_label("In&tensidade artificial", self.intensity))
        sim_row.addWidget(self.intensity)
        self.intensity_label = _label("50 / 100")
        sim_row.addWidget(self.intensity_label)
        sim_row.addStretch()
        hint = _label("Sinal sintético, sem interpretação fisiológica")
        hint.setObjectName("muted")
        sim_row.addWidget(hint)
        self.intensity.valueChanged.connect(self._change_intensity)
        serial_settings = QWidget()
        serial_row = QHBoxLayout(serial_settings)
        serial_row.setContentsMargins(0, 0, 0, 0)
        self.port_combo = QComboBox()
        self.port_combo.setEditable(True)
        self.port_combo.setMinimumWidth(150)
        serial_row.addWidget(_label("&Porta", self.port_combo))
        serial_row.addWidget(self.port_combo, 1)
        refresh = QPushButton("&Atualizar portas")
        refresh.clicked.connect(self.refresh_ports)
        serial_row.addWidget(refresh)
        self.baud = QSpinBox()
        self.baud.setRange(300, 4_000_000)
        self.baud.setValue(115200)
        self.baud.setToolTip("Confirme no firmware. Baud rate não é taxa de amostragem.")
        serial_row.addWidget(_label("&Baud rate", self.baud))
        serial_row.addWidget(self.baud)
        self.serial_settings = serial_settings
        self.source_settings.addWidget(simulation)
        self.source_settings.addWidget(serial_settings)
        layout.addWidget(self.source_settings)
        self.source_combo.currentIndexChanged.connect(self._source_changed)

    def _build_plot_controls(self, layout: QVBoxLayout) -> None:
        row = QHBoxLayout()
        self.pause_button = QPushButton("Pausar visualização")
        self.pause_button.setCheckable(True)
        self.pause_button.setShortcut(QKeySequence("Ctrl+P"))
        self.pause_button.setToolTip("Ctrl+P · a aquisição continua durante a pausa")
        self.pause_button.toggled.connect(self._pause_changed)
        row.addWidget(self.pause_button)
        self.live_button = QPushButton("Voltar ao vivo")
        self.live_button.setShortcut(QKeySequence("Ctrl+L"))
        self.live_button.clicked.connect(self.return_to_live)
        row.addWidget(self.live_button)
        row.addStretch()
        self.auto_scale = QCheckBox("Escala &automática")
        self.auto_scale.setChecked(True)
        self.auto_scale.toggled.connect(self._scale_changed)
        row.addWidget(self.auto_scale)
        self.y_min = QDoubleSpinBox()
        self.y_max = QDoubleSpinBox()
        for spin, name, value in (
            (self.y_min, "Mínimo", 0),
            (self.y_max, "Máximo", 4095),
        ):
            spin.setDecimals(0)
            spin.setRange(0, MAX_SAMPLE)
            spin.setValue(value)
            spin.setFixedWidth(105)
            spin.setEnabled(False)
            spin.setAccessibleName(f"{name} do eixo vertical")
            spin.valueChanged.connect(self._scale_changed)
            row.addWidget(_label(name, spin))
            row.addWidget(spin)
        layout.addLayout(row)

    def _source_changed(self, index: int) -> None:
        self.source_settings.setCurrentIndex(index)
        self.acquisition = Acquisition()
        self._reset_plot()
        self.origin_label.setText(
            "SIMULAÇÃO — DADOS ARTIFICIAIS"
            if index == 0
            else "SERIAL — RECEPÇÃO DE BANCADA · Segurança para contato corporal não avaliada"
        )
        self.connect_button.setText("&Iniciar" if index == 0 else "&Conectar")
        self.tick()

    def refresh_ports(self) -> None:
        previous = self._selected_port()
        try:
            ports = self._ports_provider()
        except OSError:
            self.message_label.setText(
                "Não foi possível listar portas. Confira permissões do sistema."
            )
            return
        self.port_combo.clear()
        for device, description in ports:
            self.port_combo.addItem(f"{device} — {description}", device)
        index = self.port_combo.findData(previous)
        if index >= 0:
            self.port_combo.setCurrentIndex(index)
        elif previous:
            self.port_combo.setEditText(str(previous))
        if not ports:
            self.message_label.setText(
                "Nenhuma porta encontrada. Atualize ou informe o caminho da porta."
            )

    def _selected_port(self) -> str:
        index = self.port_combo.currentIndex()
        text = self.port_combo.currentText()
        if index >= 0 and text == self.port_combo.itemText(index):
            return str(self.port_combo.itemData(index))
        return text.strip()

    def _reset_plot(self) -> None:
        self.buffer = SignalBuffer()
        self.curve.clear()
        self.pause_button.setChecked(False)
        self._following = True
        self.plot.setXRange(0, 10, padding=0)

    def start_acquisition(self) -> None:
        if self.acquisition.running:
            return
        try:
            source: ByteSource
            if self.source_combo.currentIndex() == 0:
                self._simulator = self._simulator_factory()
                self._simulator.set_intensity(self.intensity.value() / 100)
                source = self._simulator
            else:
                self._simulator = None
                port = self._selected_port()
                source = self._serial_factory(port, self.baud.value())
            self._reset_plot()
            self.acquisition.start(source)
            self._stopping = False
        except ValueError as error:
            self.message_label.setText(str(error))
            return
        self.tick()

    def stop_acquisition(self) -> None:
        self._stopping = True
        self.acquisition.stop()
        self.tick()

    def _change_intensity(self, value: int) -> None:
        self.intensity_label.setText(f"{value} / 100")
        if self._simulator is not None:
            self._simulator.set_intensity(value / 100)

    def _pause_changed(self, paused: bool) -> None:
        self.pause_button.setText("Retomar visualização" if paused else "Pausar visualização")
        if not paused:
            self._following = True
            self._force_render = True

    def _manual_zoom(self) -> None:
        self._following = False

    def return_to_live(self) -> None:
        self.pause_button.setChecked(False)
        self._following = True
        self._force_render = True
        self.tick()

    def _scale_changed(self) -> None:
        automatic = self.auto_scale.isChecked()
        self.y_min.setEnabled(not automatic)
        self.y_max.setEnabled(not automatic)
        if not automatic and self.y_min.value() >= self.y_max.value():
            self.y_max.setValue(min(MAX_SAMPLE, self.y_min.value() + 1))
            if self.y_min.value() >= self.y_max.value():
                self.y_min.setValue(self.y_max.value() - 1)
        self.plot.enableAutoRange(axis="y", enable=automatic)
        if not automatic:
            self.plot.setYRange(self.y_min.value(), self.y_max.value(), padding=0)

    def tick(self) -> None:
        packets = self.acquisition.drain()
        for packet in packets:
            self.buffer.append(packet.batch, gap_before=packet.gap_before)
        if not self.pause_button.isChecked() and (packets or self._force_render):
            times, values = self.buffer.plot_data()
            self.curve.setData(times, values, connect="finite")
            if self._following:
                last = float(times[-1]) if len(times) else 0
                self.plot.setXRange(max(0, last - 10), max(10, last), padding=0)
            self._force_render = False
        stats = self.acquisition.snapshot()
        running = self.acquisition.running
        self.state_label.setText(f"● {stats.state.capitalize()}")
        self.source_combo.setEnabled(not running)
        self.serial_settings.setEnabled(not running)
        self.connect_button.setEnabled(not running and not self._closing)
        self.disconnect_button.setEnabled(running and not self._stopping)
        self.stats_label.setText(
            f"{_count(stats.samples_per_second)} amostras/s recebidas  ·  "
            f"{_count(stats.total_samples)} recebidas  ·  "
            f"{_count(len(self.buffer))} em memória\n"
            f"Erros: {stats.errors}  ·  "
            f"Lacunas: {stats.gaps} ({stats.missing_samples} amostras)  ·  "
            f"Duplicatas: {stats.duplicates}  ·  Descartes: fila {stats.queue_dropped}, "
            f"capacidade {self.buffer.capacity_dropped}"
        )
        if running or stats.state == "erro" or self._stopping:
            self.message_label.setText(stats.message)
        if self._closing and not running:
            self.close()

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.acquisition.running:
            self._closing = True
            self.acquisition.stop()
            self.message_label.setText("Encerrando aquisição e liberando a fonte…")
            event.ignore()
            return
        self.timer.stop()
        event.accept()
