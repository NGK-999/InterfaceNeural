STYLE = """
QWidget { background: #111b26; color: #e2eaf2; font-size: 13px; }
QLabel#title { font-size: 23px; font-weight: 600; }
QLabel#muted { color: #aebdcd; }
QLabel#origin { background: #302b1b; color: #ffe2a3; padding: 9px; border-radius: 5px; }
QLabel#state { color: #7ee0cf; font-weight: 600; padding: 8px; }
QLabel#details { color: #b9c8d8; padding: 4px 0; }
QPushButton, QComboBox, QSpinBox, QDoubleSpinBox {
    background: #223243; border: 1px solid #53697e; border-radius: 4px;
    padding: 6px 9px; min-height: 18px;
}
QPushButton:hover { background: #30475e; }
QPushButton:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border: 2px solid #79bfff;
}
QPushButton:disabled, QComboBox:disabled { color: #8395a8; border-color: #364555; }
QPushButton:checked { background: #6d4a16; border-color: #ebba68; }
QPushButton#primary { background: #21685f; border-color: #65b6a7; font-weight: 600; }
QSlider::groove:horizontal { height: 5px; background: #41576e; border-radius: 2px; }
QSlider::handle:horizontal { width: 16px; margin: -5px 0; background: #74d8c6; border-radius: 7px; }
QCheckBox { spacing: 7px; }
QToolTip { background: #223243; color: #e2eaf2; border: 1px solid #829ab2; }
"""
