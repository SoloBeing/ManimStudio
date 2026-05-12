C = dict(
    bg0="#0d1117", bg1="#161b22", bg2="#1c2230", bg3="#21262d",
    border="#30363d", accent="#58a6ff", accent2="#f78166",
    accent3="#e3b341", text="#e6edf3", dim="#8b949e",
    green="#3fb950", red="#f85149", teal="#39d353",
)

STYLE = f"""
* {{ font-family: 'JetBrains Mono','Fira Code','Consolas',monospace; color:{C['text']}; }}
QWidget {{ background:{C['bg0']}; }}
QScrollArea,QScrollBar {{ background:transparent; border:none; }}
QScrollBar:vertical {{ background:{C['bg1']}; width:5px; border-radius:2px; }}
QScrollBar::handle:vertical {{ background:{C['border']}; border-radius:2px; }}

QGroupBox {{
    border:1px solid {C['border']}; border-radius:7px;
    margin-top:16px; padding:10px 8px 8px 8px;
    background:{C['bg2']}; font-size:11px; font-weight:700;
}}
QGroupBox::title {{
    subcontrol-origin:margin; left:10px; padding:0 6px;
    color:{C['accent']}; font-size:10px; font-weight:700;
    text-transform:uppercase; letter-spacing:1px;
}}
QLabel {{ font-size:11px; }}
QLabel#dim  {{ color:{C['dim']}; font-size:10px; }}
QLabel#hdr  {{ color:{C['accent3']}; font-size:10px; font-weight:700;
               letter-spacing:1px; padding:4px 0 2px 0; }}
QLabel#comboLabel {{ color:{C['accent3']}; font-size:10px; font-weight:700; }}
QLabel#emptyTitle {{ color:{C['text']}; font-size:22px; font-weight:800; }}
QFrame#emptyPreview {{
    background:{C['bg1']}; border:1px dashed {C['border']};
    border-radius:8px;
}}

QDoubleSpinBox,QSpinBox,QComboBox {{
    background:{C['bg3']}; border:1px solid {C['border']};
    border-radius:5px; padding:3px 7px; font-size:11px;
    color:{C['text']}; selection-background-color:{C['accent']};
    selection-color:{C['bg0']};
}}
QDoubleSpinBox:focus,QComboBox:focus {{ border-color:{C['accent']}; background:{C['bg2']}; }}
QComboBox:hover {{ border-color:{C['accent']}; }}
QComboBox::drop-down {{
    subcontrol-origin:padding; subcontrol-position:top right;
    background:{C['bg2']}; border-left:1px solid {C['border']};
    width:22px; border-top-right-radius:5px; border-bottom-right-radius:5px;
}}
QComboBox::down-arrow {{
    image:none; width:0; height:0;
    border-left:4px solid transparent; border-right:4px solid transparent;
    border-top:5px solid {C['accent']}; margin-right:7px;
}}
QComboBox QAbstractItemView {{
    background:{C['bg2']}; color:{C['text']};
    border:1px solid {C['border']}; outline:0;
    selection-background-color:{C['accent']}; selection-color:{C['bg0']};
}}
QComboBox#animationCombo {{
    color:{C['accent3']}; font-weight:700;
}}
QComboBox#animationCombo QAbstractItemView {{
    color:{C['text']}; font-weight:600;
}}
QComboBox#modeSelector {{
    background:{C['bg1']}; color:{C['text']};
    border:1px solid {C['accent']}; border-radius:6px;
    padding:6px 8px; font-size:12px; font-weight:800;
}}
QComboBox#modeSelector::drop-down {{
    background:{C['bg2']}; border-left:1px solid {C['border']};
    width:24px; border-top-right-radius:6px; border-bottom-right-radius:6px;
}}
QComboBox#modeSelector QAbstractItemView {{
    background:{C['bg2']}; color:{C['text']};
    border:1px solid {C['border']};
    selection-background-color:{C['accent']}; selection-color:{C['bg0']};
}}
QComboBox#statusCombo {{
    background:{C['bg1']}; color:{C['accent3']};
    border:1px solid {C['border']}; border-radius:4px;
    padding:2px 6px; font-size:10px; font-weight:700;
}}
QComboBox#statusCombo::drop-down {{
    background:{C['bg2']}; border-left:1px solid {C['border']};
    width:20px; border-top-right-radius:4px; border-bottom-right-radius:4px;
}}
QComboBox#statusCombo QAbstractItemView {{
    background:{C['bg2']}; color:{C['text']};
    border:1px solid {C['border']};
    selection-background-color:{C['accent']}; selection-color:{C['bg0']};
}}

QCheckBox {{ font-size:11px; spacing:6px; }}
QCheckBox::indicator {{ width:13px; height:13px; border-radius:3px;
    border:1.5px solid {C['border']}; background:{C['bg3']}; }}
QCheckBox::indicator:checked {{ background:{C['accent']}; border-color:{C['accent']}; }}

QSlider::groove:horizontal {{ background:{C['bg3']}; height:3px; border-radius:2px; }}
QSlider::handle:horizontal {{ background:{C['accent']}; width:13px; height:13px;
    margin:-5px 0; border-radius:6px; border:2px solid {C['bg2']}; }}
QSlider::sub-page:horizontal {{ background:{C['accent']}; border-radius:2px; }}

QPushButton {{ background:{C['bg3']}; border:1px solid {C['border']};
    border-radius:6px; padding:6px 14px; font-size:11px; font-weight:600; }}
QPushButton:hover {{ border-color:{C['accent']}; color:{C['accent']}; }}
QPushButton#run {{ background:{C['accent']}; color:{C['bg0']}; border:none;
    padding:9px 28px; font-size:12px; font-weight:700; border-radius:6px; }}
QPushButton#run:hover {{ background:#79c0ff; }}
QPushButton#run:disabled {{ background:{C['bg3']}; color:{C['dim']}; }}
QPushButton#stop {{ border-color:{C['accent2']}; color:{C['accent2']}; }}
QPushButton#stop:hover {{ background:{C['accent2']}; color:{C['bg0']}; }}

QTextEdit {{ background:{C['bg1']}; border:1px solid {C['border']};
    border-radius:6px; font-size:10px; padding:4px; }}
QStatusBar {{ background:{C['bg2']}; border-top:1px solid {C['border']};
    color:{C['accent3']}; font-size:10px; }}
QVideoWidget {{ background:{C['bg0']}; border-radius:8px; }}
"""
