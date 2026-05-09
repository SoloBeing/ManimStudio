# -*- mode: python ; coding: utf-8 -*-
import sys, os, glob, subprocess
from PyInstaller.utils.hooks import collect_all

datas = []
binaries = []
hiddenimports = []

for pkg in ('manim', 'manimpango', 'skia', 'av'):
    d, b, h = collect_all(pkg)
    datas += d; binaries += b; hiddenimports += h


# ── GStreamer (Linux only) ────────────────────────────────────────────────────
# Qt6 Multimedia uses GStreamer as its backend on Linux. We bundle the core
# shared libs and the plugins needed for MP4/H.264 playback so the preview
# player works on machines that don't have GStreamer installed.
if sys.platform == 'linux':
    def _gst_dir(pkg_config_var, *fallbacks):
        try:
            p = subprocess.check_output(
                ['pkg-config', '--variable=' + pkg_config_var, 'gstreamer-1.0'],
                stderr=subprocess.DEVNULL, text=True,
            ).strip()
            if p and os.path.isdir(p):
                return p
        except Exception:
            pass
        for fb in fallbacks:
            if os.path.isdir(fb):
                return fb
        return None

    _lib_dir = _gst_dir(
        'libdir',
        '/usr/lib/x86_64-linux-gnu',
        '/usr/lib/aarch64-linux-gnu',
        '/usr/lib',
        '/usr/lib64',
    )
    _plugin_dir = _gst_dir(
        'pluginsdir',
        *([os.path.join(_lib_dir, 'gstreamer-1.0')] if _lib_dir else []),
    )

    if _lib_dir:
        _seen = set()
        _core_patterns = [
            'libgstreamer-1.0.so*',
            'libgstbase-1.0.so*',
            'libgstvideo-1.0.so*',
            'libgstaudio-1.0.so*',
            'libgstpbutils-1.0.so*',
            'libgstapp-1.0.so*',
            'libgstgl-1.0.so*',
            'libgsttag-1.0.so*',
        ]
        for pat in _core_patterns:
            for p in glob.glob(os.path.join(_lib_dir, pat)):
                real = os.path.realpath(p)
                if real not in _seen and os.path.isfile(real):
                    _seen.add(real)
                    binaries.append((real, '.'))

    if _plugin_dir:
        _needed_plugins = [
            'libgstcoreelements.so',
            'libgsttypefindfunctions.so',
            'libgstplayback.so',
            'libgstisomp4.so',           # MP4 / H.264 demuxer
            'libgstmatroska.so',         # MKV demuxer
            'libgstvideoconvertscale.so',
            'libgstaudioconvert.so',
            'libgstaudioresample.so',
            'libgstvolume.so',
            'libgstautodetect.so',
            'libgstvideoparsersbad.so',
            'libgstaudiofx.so',
            'libgstopengl.so',
            'libgstlibav.so',            # gst-libav H.264/AAC decoder (optional)
        ]
        for name in _needed_plugins:
            p = os.path.join(_plugin_dir, name)
            if os.path.exists(p):
                binaries.append((p, 'gst-plugins'))
# ─────────────────────────────────────────────────────────────────────────────


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['rthooks/pyi_rth_gstreamer.py'],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ManimStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
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
    name='ManimStudio',
)
