# ManimStudio — Windows installer (.exe)

Builds a native Windows installer with [Inno Setup](https://jrsoftware.org/isinfo.php)
so ManimStudio installs to **Program Files**, gets Start Menu (and optional
desktop) shortcuts, and uninstalls cleanly from **Add/Remove Programs**. The
Windows counterpart of the `.deb` packaging.

## Layout

| Path | Purpose |
|------|---------|
| `build_installer.ps1` | Orchestrates the build: app bundle → `ISCC` → installer `.exe`. |
| `manimstudio.iss` | Inno Setup script. `MyAppVersion` / `DistDir` passed in at compile time. |
| `make_ico.py` | Packs `../deb/manimstudio.png` into a multi-res `manimstudio.ico`. |
| `manimstudio.ico` | Committed icon (16–256px) used for shortcuts + the setup `.exe`. |

## Installed files

```
%ProgramFiles%\ManimStudio\ManimStudio.exe        PyInstaller bundle
%ProgramFiles%\ManimStudio\_internal\…            bundled deps
%ProgramFiles%\ManimStudio\manimstudio.ico        shortcut icon
Start Menu\Manim Studio                            menu shortcut
Desktop\Manim Studio                               optional (unchecked task)
```

## Build (on Windows)

Requires Inno Setup 6 (`choco install innosetup -y`) and the usual toolchain
(Node, uv). From `Manim_Project_files\`:

```powershell
# Full build (React UI + PyInstaller + installer)
powershell -ExecutionPolicy Bypass -File packaging\windows\build_installer.ps1 2.0.19

# Reuse an existing dist\ManimStudio bundle (fast)
packaging\windows\build_installer.ps1 2.0.19 -SkipBuild

# Point at a non-default bundle location (CI uses this)
packaging\windows\build_installer.ps1 2.0.19 -SkipBuild -Dist C:\path\to\dist
```

Version defaults to the latest git tag (`v` stripped), falling back to `2.0.19`.
Output: `dist\ManimStudio-Setup-<version>.exe`.

## Install / uninstall

Double-click `ManimStudio-Setup-<version>.exe` (per-machine by default; a
non-admin can pick a per-user location at the UAC prompt). Uninstall from
**Settings → Apps** or **Add/Remove Programs**.

User data in `%USERPROFILE%\ManimStudio\` (renders, history) is left untouched
on uninstall — Inno only removes what it installed.

## LaTeX

Windows has no system package manager to pull LaTeX in automatically, so the
installer shows a one-time notice pointing to [MiKTeX](https://miktex.org) when
`latex` isn't on `PATH`. MathTex/Tex and coordinate labels need it; plain
`Text()` animations don't. The in-app preflight guard blocks LaTeX-requiring
renders and shows the install hint, so LaTeX can be added later at any time.

> **Note:** `ISCC` (the Inno Setup compiler) is Windows-only — the installer
> cannot be built or compile-checked on Linux/macOS. CI builds it on the
> `windows-latest` runner.
