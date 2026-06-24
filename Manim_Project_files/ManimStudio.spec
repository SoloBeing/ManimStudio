# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas = []
binaries = []

# All platforms use pywebview's Qt backend (Qt WebEngine).
# pywebview's Windows-native backends (edgechromium, winforms) both require
# pythonnet/.NET interop which crashes in frozen PyInstaller builds.
hiddenimports = [
    "webview.platforms.qt",
    "qtpy",
    "PyQt6.QtWebEngineWidgets",
    "PyQt6.QtWebEngineCore",
    "PyQt6.QtNetwork",
    "PyQt6.QtPrintSupport",
]
# Exclude .NET-dependent backends on all platforms — they are discovered by
# collect_all but must never be imported in the frozen bundle.
excludes = [
    "webview.platforms.winforms",
    "webview.platforms.edgechromium",
    "clr",
    "pythonnet",
]

for package in ["manim", "manimpango", "pywebview"]:
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports
    hiddenimports += collect_submodules(package)

# Math / image companion libraries usable from the Playground. They are NOT
# imported by app.py or manim's entry path, so PyInstaller's static analysis
# would omit them — a user scene doing `import sympy` would then fail in the
# frozen app with ModuleNotFoundError. Force every module + data file (and
# native libs, e.g. shapely's GEOS) into the bundle so the whole stack works
# out of the box, no user install required.
for package in ["sympy", "mpmath", "skimage", "shapely", "pandas", "colour"]:
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += package_datas
    binaries += package_binaries
    hiddenimports += package_hiddenimports

# numpy/scipy/networkx/Pillow already ship as manim dependencies; top up their
# submodules so lazily-loaded parts (e.g. scipy.optimize, numpy.fft) are present
# for arbitrary Playground use too.
for package in ["numpy", "scipy", "networkx", "PIL"]:
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
