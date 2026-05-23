import re as _re

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QSlider, QDoubleSpinBox, QFrame, QComboBox, QPlainTextEdit
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QRect, QSize
from PyQt6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QPainter,
)

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
        self.lineEdit().installEventFilter(self)

    def wheelEvent(self, event):
        if self.hasFocus():
            super().wheelEvent(event)
        else:
            event.ignore()

    def eventFilter(self, obj, event):
        if obj is self.lineEdit() and event.type() == QEvent.Type.MouseButtonDblClick:
            self.lineEdit().selectAll()
            return True
        return super().eventFilter(obj, event)


class ComboBox(QComboBox):
    """ComboBox that only responds to wheel scroll when it has been clicked."""
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


# ---------------------------------------------------------------------------
# Code editor — syntax highlighting, line numbers, auto-indent
# ---------------------------------------------------------------------------

class _LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self._e = editor

    def sizeHint(self):
        return QSize(self._e._lnum_width(), 0)

    def paintEvent(self, event):
        self._e._paint_lnum(event)


class PythonHighlighter(QSyntaxHighlighter):
    _KEYWORDS = frozenset({
        'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
        'break', 'class', 'continue', 'def', 'del', 'elif', 'else',
        'except', 'finally', 'for', 'from', 'global', 'if', 'import',
        'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise',
        'return', 'try', 'while', 'with', 'yield',
    })
    _BUILTINS = frozenset({
        'abs', 'all', 'any', 'bin', 'bool', 'breakpoint', 'bytearray',
        'bytes', 'callable', 'chr', 'classmethod', 'compile', 'complex',
        'delattr', 'dict', 'dir', 'divmod', 'enumerate', 'eval', 'exec',
        'filter', 'float', 'format', 'frozenset', 'getattr', 'globals',
        'hasattr', 'hash', 'help', 'hex', 'id', 'input', 'int', 'isinstance',
        'issubclass', 'iter', 'len', 'list', 'locals', 'map', 'max',
        'memoryview', 'min', 'next', 'object', 'oct', 'open', 'ord', 'pow',
        'print', 'property', 'range', 'repr', 'reversed', 'round', 'set',
        'setattr', 'slice', 'sorted', 'staticmethod', 'str', 'sum', 'super',
        'tuple', 'type', 'vars', 'zip',
    })
    _MANIM = frozenset({
        'Scene', 'ThreeDScene', 'MovingCameraScene', 'ZoomedScene',
        'VectorScene', 'LinearTransformationScene',
        'Circle', 'Square', 'Rectangle', 'Triangle', 'Polygon', 'RegularPolygon',
        'Line', 'Arrow', 'DoubleArrow', 'Vector', 'Dot', 'Cross',
        'Text', 'Tex', 'MathTex', 'Title', 'Paragraph',
        'Axes', 'NumberPlane', 'ComplexPlane', 'PolarPlane', 'NumberLine',
        'Create', 'Write', 'FadeIn', 'FadeOut', 'Transform',
        'ReplacementTransform', 'MoveToTarget', 'Indicate', 'Flash',
        'GrowFromCenter', 'ShrinkToCenter', 'DrawBorderThenFill',
        'ValueTracker', 'VGroup', 'Group', 'AnimationGroup',
        'Rotate', 'Scale', 'Shift', 'ApplyMatrix', 'ApplyFunction',
        'CurvedArrow', 'ArcBetweenPoints', 'Arc',
        'SurroundingRectangle', 'Underline', 'Brace',
        'ORIGIN', 'UP', 'DOWN', 'LEFT', 'RIGHT', 'IN', 'OUT',
        'UL', 'UR', 'DL', 'DR',
        'RED', 'BLUE', 'GREEN', 'YELLOW', 'WHITE', 'BLACK',
        'ORANGE', 'PINK', 'PURPLE', 'TEAL', 'GOLD', 'MAROON', 'GREY', 'GRAY',
        'PI', 'TAU', 'DEGREES',
        'RED_A', 'RED_B', 'RED_C', 'RED_D', 'RED_E',
        'BLUE_A', 'BLUE_B', 'BLUE_C', 'BLUE_D', 'BLUE_E',
        'GREEN_A', 'GREEN_B', 'GREEN_C', 'GREEN_D', 'GREEN_E',
    })

    def __init__(self, document):
        super().__init__(document)

        def _fmt(color, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:   f.setFontWeight(QFont.Weight.Bold)
            if italic: f.setFontItalic(True)
            return f

        mn_pat  = '|'.join(_re.escape(k) for k in sorted(self._MANIM,    key=len, reverse=True))
        kw_pat  = '|'.join(_re.escape(k) for k in sorted(self._KEYWORDS, key=len, reverse=True))
        bi_pat  = '|'.join(_re.escape(k) for k in sorted(self._BUILTINS, key=len, reverse=True))

        self._rules = [
            (_re.compile(rf'\b(?:{mn_pat})\b'),  _fmt('#e3b341', bold=True)),
            (_re.compile(rf'\b(?:{bi_pat})\b'),  _fmt('#56d364')),
            (_re.compile(rf'\b(?:{kw_pat})\b'),  _fmt('#58a6ff', bold=True)),
            (_re.compile(r'\bself\b|\bcls\b'),   _fmt('#79c0ff')),
            (_re.compile(r'@\w+'),               _fmt('#d2a8ff')),
            (_re.compile(r'\b\d+\.?\d*\b'),      _fmt('#f78166')),
        ]
        self._str_re  = _re.compile(r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')')
        self._cmt_re  = _re.compile(r'#[^\n]*')
        self._str_fmt = _fmt('#a5d6ff')
        self._cmt_fmt = _fmt('#8b949e', italic=True)
        self._tq      = [
            (_re.compile(r'"""'), 1, self._str_fmt),
            (_re.compile(r"'''"), 2, self._str_fmt),
        ]

    def highlightBlock(self, text):
        for pat, fmt in self._rules:
            for m in pat.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)
        for m in self._str_re.finditer(text):
            self.setFormat(m.start(), m.end() - m.start(), self._str_fmt)
        cm = self._cmt_re.search(text)
        if cm:
            self.setFormat(cm.start(), len(text) - cm.start(), self._cmt_fmt)

        # Multiline triple-quoted string state machine
        self.setCurrentBlockState(0)
        prev  = self.previousBlockState()
        if prev in (1, 2):
            delim = self._tq[prev - 1][0]
            m = delim.search(text)
            if m:
                self.setFormat(0, m.end(), self._str_fmt)
                start = m.end()
                self.setCurrentBlockState(0)
            else:
                self.setFormat(0, len(text), self._str_fmt)
                self.setCurrentBlockState(prev)
                return
        else:
            start = 0

        while start < len(text):
            best = None
            for pat, state, fmt in self._tq:
                m = pat.search(text, start)
                if m and (best is None or m.start() < best[0].start()):
                    best = (m, state, fmt)
            if best is None:
                break
            m, state, fmt = best
            close = self._tq[state - 1][0].search(text, m.end())
            if close:
                self.setFormat(m.start(), close.end() - m.start(), fmt)
                start = close.end()
            else:
                self.setFormat(m.start(), len(text) - m.start(), fmt)
                self.setCurrentBlockState(state)
                break


class CodeEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._lnum_area = _LineNumberArea(self)
        self.blockCountChanged.connect(self._update_lnum_width)
        self.updateRequest.connect(self._update_lnum_area)
        self._update_lnum_width(0)

    def _lnum_width(self):
        digits = max(2, len(str(self.blockCount())))
        return 8 + self.fontMetrics().horizontalAdvance('9') * digits

    def _update_lnum_width(self, _=0):
        self.setViewportMargins(self._lnum_width(), 0, 0, 0)

    def _update_lnum_area(self, rect, dy):
        if dy:
            self._lnum_area.scroll(0, dy)
        else:
            self._lnum_area.update(0, rect.y(), self._lnum_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_lnum_width()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._lnum_area.setGeometry(
            QRect(cr.left(), cr.top(), self._lnum_width(), cr.height())
        )

    def _paint_lnum(self, event):
        painter = QPainter(self._lnum_area)
        painter.fillRect(event.rect(), QColor(C['bg0']))
        block  = self.firstVisibleBlock()
        num    = block.blockNumber()
        top    = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        h      = self.fontMetrics().height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(QColor(C['dim']))
                painter.drawText(
                    0, top, self._lnum_area.width() - 4, h,
                    Qt.AlignmentFlag.AlignRight, str(num + 1),
                )
            block  = block.next()
            top    = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            num   += 1

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Tab:
            self.insertPlainText('    ')
            return
        if key == Qt.Key.Key_Backtab:
            cur    = self.textCursor()
            line   = cur.block().text()
            remove = min(4, len(line) - len(line.lstrip(' ')))
            if remove:
                cur.movePosition(cur.MoveOperation.StartOfBlock)
                for _ in range(remove):
                    cur.deleteChar()
                self.setTextCursor(cur)
            return
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cur    = self.textCursor()
            line   = cur.block().text()
            indent = len(line) - len(line.lstrip())
            if line.rstrip().endswith(':'):
                indent += 4
            super().keyPressEvent(event)
            self.insertPlainText(' ' * indent)
            return
        super().keyPressEvent(event)
