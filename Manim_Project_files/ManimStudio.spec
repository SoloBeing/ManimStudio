# -*- mode: python ; coding: utf-8 -*-

import sys as _sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []

# Platform-specific WebView backend hidden imports.
# Windows: use Edge WebView2 (edgechromium) — no pythonnet/clr needed.
# Linux/macOS: use Qt WebEngine backend.
if _sys.platform == "win32":
    hiddenimports = [
        "webview.platforms.edgechromium",
    ]
    excludes = [
        # Exclude winforms backend and its pythonnet dependency — they are
        # bundled by collect_all but crash in frozen builds on Windows.
        "webview.platforms.winforms",
        "clr",
        "pythonnet",
    ]
else:
    hiddenimports = [
        # PyWebView Qt backend — dynamically imported at runtime
        "webview.platforms.qt",
        "qtpy",
        # Qt WebEngine (required by PyWebView's Qt backend)
        "PyQt6.QtWebEngineWidgets",
        "PyQt6.QtWebEngineCore",
        "PyQt6.QtNetwork",
        "PyQt6.QtPrintSupport",
    ]
    excludes = []

for package in ["manim", "manimpango", "pywebview"]:
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports
    hiddenimports += collect_submodules(package)

# Bundle the React UI build (served via HTTP at runtime)
datas += [("ui/dist", "ui/dist")]


a = Analysis(
    ["app.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ManimStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ManimStudio",
)
