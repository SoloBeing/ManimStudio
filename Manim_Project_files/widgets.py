from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider, QDoubleSpinBox, QFrame
from PyQt6.QtCore import Qt, pyqtSignal

from theme import C


def sep():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{C['border']};")
    return f


def hdr(text):
    l = QLabel(text)
    l.setObjectName("hdr")
    return l


class SpinBox(QDoubleSpinBox):
    """SpinBox that only responds to wheel scroll when it has been clicked."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class _ScrollGuardSlider(QSlider):
    """Slider that only responds to wheel scroll when it has been clicked."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()


class Knob(QWidget):
    """Slider + SpinBox in one row for one float parameter."""
    changed = pyqtSignal(float)

    def __init__(self, label, lo, hi, default, decimals=2, step=0.01):
        super().__init__()
        self._decimals = decimals
        self._scale    = 10 ** decimals

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)

        lbl = QLabel(label)
        lbl.setFixedWidth(110)
        lbl.setObjectName("dim")

        self.slider = _ScrollGuardSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(int(lo      * self._scale))
        self.slider.setMaximum(int(hi      * self._scale))
        self.slider.setValue  (int(default * self._scale))

        self.spin = SpinBox()
        self.spin.setRange(lo, hi)
        self.spin.setDecimals(decimals)
        self.spin.setSingleStep(step)
        self.spin.setValue(default)
        self.spin.setFixedWidth(72)

        self.slider.valueChanged.connect(self._from_slider)
        self.spin.valueChanged.connect  (self._from_spin)

        row.addWidget(lbl)
        row.addWidget(self.slider)
        row.addWidget(self.spin)

    def _from_slider(self, v):
        val = v / self._scale
        self.spin.blockSignals(True)
        self.spin.setValue(val)
        self.spin.blockSignals(False)
        self.changed.emit(val)

    def _from_spin(self, val):
        self.slider.blockSignals(True)
        self.slider.setValue(int(val * self._scale))
        self.slider.blockSignals(False)
        self.changed.emit(val)

    def value(self):
        return self.spin.value()
