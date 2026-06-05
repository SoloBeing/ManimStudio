#!/usr/bin/env bash
# Build a Debian package (.deb) for ManimStudio from the PyInstaller --onedir
# bundle. Lays out /opt/manimstudio + a /usr/bin launcher + .desktop + icon,
# then runs dpkg-deb. Uninstall is handled natively by apt/dpkg.
#
# Usage:
#   ./build_deb.sh [VERSION] [--skip-build] [--dist DIR]
#
#   VERSION        package version, e.g. 2.0.19. Default: latest git tag
#                  (v-prefix stripped), falling back to 2.0.19.
#   --skip-build   reuse an existing PyInstaller bundle instead of rebuilding
#                  the React UI + running PyInstaller.
#   --dist DIR     directory containing the built "ManimStudio/" bundle.
#                  Default: <project>/dist
#
# Output: <dist>/manimstudio_<version>_amd64.deb
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ="$(cd "$HERE/../.." && pwd)"          # Manim_Project_files

VERSION=""
SKIP_BUILD=0
DIST="$PROJ/dist"

while [ $# -gt 0 ]; do
  case "$1" in
    --skip-build) SKIP_BUILD=1; shift ;;
    --dist)       DIST="$2"; shift 2 ;;
    --dist=*)     DIST="${1#--dist=}"; shift ;;
    -*)           echo "unknown option: $1" >&2; exit 2 ;;
    *)            VERSION="$1"; shift ;;
  esac
done

if [ -z "$VERSION" ]; then
  VERSION="$(git -C "$PROJ" describe --tags --abbrev=0 2>/dev/null | sed 's/^v//' || true)"
fi
[ -z "$VERSION" ] && VERSION="2.0.19"

echo ">> ManimStudio .deb  version=$VERSION  dist=$DIST  skip_build=$SKIP_BUILD"

# ---------------------------------------------------------------------------
# 1. Build the app bundle (unless reusing an existing one)
# ---------------------------------------------------------------------------
if [ "$SKIP_BUILD" -eq 0 ]; then
  echo ">> Building React UI"
  ( cd "$PROJ/ui" && npm ci && npm run build )
  echo ">> Running PyInstaller"
  ( cd "$PROJ" && uv run python -m PyInstaller --clean --noconfirm \
      --distpath "$DIST" --workpath "$PROJ/build" ManimStudio.spec )
fi

SRC="$DIST/ManimStudio"
if [ ! -x "$SRC/ManimStudio" ]; then
  echo "ERROR: bundle not found at $SRC/ManimStudio (build first, or pass --dist)" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. Ensure the icon exists
# ---------------------------------------------------------------------------
ICON="$HERE/manimstudio.png"
if [ ! -f "$ICON" ]; then
  echo ">> Generating icon"
  python3 "$HERE/make_icon.py" "$ICON" || echo "WARN: icon generation failed; continuing without it"
fi

# ---------------------------------------------------------------------------
# 3. Stage the package tree
# ---------------------------------------------------------------------------
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

install -d "$STAGE/opt/manimstudio"
cp -a "$SRC/." "$STAGE/opt/manimstudio/"
# Strip group/other write bits (umask leftovers) so dpkg/lintian don't flag
# world- or group-writable files; keeps owner-exec bits on binaries intact.
chmod -R go-w "$STAGE/opt/manimstudio"

install -d "$STAGE/usr/bin"
cat > "$STAGE/usr/bin/manimstudio" <<'EOF'
#!/bin/sh
exec /opt/manimstudio/ManimStudio "$@"
EOF
chmod 0755 "$STAGE/usr/bin/manimstudio"

install -d "$STAGE/usr/share/applications"
install -m 0644 "$HERE/manimstudio.desktop" "$STAGE/usr/share/applications/manimstudio.desktop"

if [ -f "$ICON" ]; then
  install -d "$STAGE/usr/share/icons/hicolor/256x256/apps"
  install -m 0644 "$ICON" "$STAGE/usr/share/icons/hicolor/256x256/apps/manimstudio.png"
fi

# ---------------------------------------------------------------------------
# 4. Control + maintainer scripts
# ---------------------------------------------------------------------------
install -d "$STAGE/DEBIAN"
SIZE_KB="$(du -ks "$STAGE" | cut -f1)"
sed -e "s/@VERSION@/$VERSION/" -e "s/@SIZE@/$SIZE_KB/" \
    "$HERE/control.template" > "$STAGE/DEBIAN/control"
install -m 0755 "$HERE/postinst" "$STAGE/DEBIAN/postinst"
install -m 0755 "$HERE/postrm"   "$STAGE/DEBIAN/postrm"

# ---------------------------------------------------------------------------
# 5. Build the .deb
# ---------------------------------------------------------------------------
OUT="$DIST/manimstudio_${VERSION}_amd64.deb"
echo ">> dpkg-deb --build (this can take a while for a large bundle)"
dpkg-deb --root-owner-group --build "$STAGE" "$OUT"

echo ">> Done: $OUT"
dpkg-deb --info "$OUT" | sed 's/^/   /'
echo ">> Install with:  sudo apt install $OUT"
echo ">> Remove with:   sudo apt remove manimstudio"
