# ManimStudio — Debian package (.deb)

Builds a native `.deb` so ManimStudio installs to `/opt`, gets a menu launcher
and icon, and uninstalls cleanly through `apt`/`dpkg`.

## Layout

| Path | Purpose |
|------|---------|
| `build_deb.sh` | Orchestrates the build: app bundle → staged tree → `dpkg-deb`. |
| `control.template` | Package metadata. `@VERSION@` / `@SIZE@` filled in at build time. |
| `manimstudio.desktop` | Menu entry (`Exec=/opt/manimstudio/ManimStudio`). |
| `postinst` / `postrm` | Refresh desktop+icon caches; nudge about LaTeX. |
| `make_icon.py` | Generates `manimstudio.png` (256×256, Atom One Dark). |

## Installed files

```
/opt/manimstudio/…                                  PyInstaller bundle
/usr/bin/manimstudio                                launcher wrapper
/usr/share/applications/manimstudio.desktop         menu entry
/usr/share/icons/hicolor/256x256/apps/manimstudio.png
```

## Build

From `Manim_Project_files/`:

```bash
# Full build (React UI + PyInstaller + .deb)
packaging/deb/build_deb.sh 2.0.19

# Reuse an existing dist/ManimStudio bundle (fast)
packaging/deb/build_deb.sh 2.0.19 --skip-build

# Point at a non-default bundle location (CI uses this)
packaging/deb/build_deb.sh 2.0.19 --skip-build --dist /path/to/dist
```

Version defaults to the latest git tag (`v` stripped), falling back to `2.0.19`.
Output: `dist/manimstudio_<version>_amd64.deb`.

## Install / uninstall

```bash
sudo apt install ./dist/manimstudio_2.0.19_amd64.deb   # pulls deps + LaTeX
sudo apt remove manimstudio                            # uninstall
```

## Dependencies

- **Depends:** `ffmpeg` (Manim render backend) + Qt WebEngine runtime libs
  (`libnss3`, `libgbm1`, `libxcb-cursor0`).
- **Recommends:** `texlive-latex-base texlive-latex-extra
  texlive-fonts-recommended dvisvgm` — installed by default so MathTex/Tex and
  coordinate labels work. Skip with `--no-install-recommends`; the in-app
  preflight guard then blocks LaTeX renders and points users to the install
  command. Plain `Text()` animations work without LaTeX.

> A `.deb` cannot run `apt` from its own `postinst` (dpkg holds the lock), so
> "offer optional LaTeX" is implemented the idiomatic Debian way: a
> `Recommends:` (on by default, declinable) plus a `postinst` message when
> LaTeX is absent.

User data in `~/ManimStudio/` (renders, history) is left untouched on removal.
