<#
.SYNOPSIS
  Build the Windows installer (.exe) for ManimStudio from the PyInstaller
  --onedir bundle, using Inno Setup. The Windows counterpart of build_deb.sh.

.DESCRIPTION
  Builds the React UI + runs PyInstaller (unless -SkipBuild), then compiles
  manimstudio.iss with ISCC into <Dist>\ManimStudio-Setup-<version>.exe.

.PARAMETER Version
  Package version, e.g. 2.0.19. Default: latest git tag (v-prefix stripped),
  falling back to 2.0.19.

.PARAMETER SkipBuild
  Reuse an existing PyInstaller bundle instead of rebuilding the UI + bundle.

.PARAMETER Dist
  Directory containing the built "ManimStudio\" bundle. Default: <project>\dist

.EXAMPLE
  .\build_installer.ps1 2.0.19
.EXAMPLE
  .\build_installer.ps1 2.0.19 -SkipBuild -Dist C:\path\to\dist
#>
[CmdletBinding()]
param(
  [string]$Version = "",
  [switch]$SkipBuild,
  [string]$Dist = ""
)

$ErrorActionPreference = "Stop"

$Here = Split-Path -Parent $MyInvocation.MyCommand.Path
$Proj = (Resolve-Path (Join-Path $Here "..\..")).Path    # Manim_Project_files
if (-not $Dist) { $Dist = Join-Path $Proj "dist" }

if (-not $Version) {
  try {
    $tag = (git -C $Proj describe --tags --abbrev=0 2>$null)
    if ($tag) { $Version = $tag -replace '^v', '' }
  } catch { }
}
if (-not $Version) { $Version = "2.0.19" }

Write-Host ">> ManimStudio installer  version=$Version  dist=$Dist  skipBuild=$SkipBuild"

# ---------------------------------------------------------------------------
# 1. Build the app bundle (unless reusing an existing one)
# ---------------------------------------------------------------------------
if (-not $SkipBuild) {
  Write-Host ">> Building React UI"
  Push-Location (Join-Path $Proj "ui")
  try { npm ci; if ($LASTEXITCODE) { throw "npm ci failed" }
        npm run build; if ($LASTEXITCODE) { throw "npm run build failed" } }
  finally { Pop-Location }

  Write-Host ">> Running PyInstaller"
  Push-Location $Proj
  try {
    uv run python -m PyInstaller --clean --noconfirm `
      --distpath $Dist --workpath (Join-Path $Proj "build") ManimStudio.spec
    if ($LASTEXITCODE) { throw "PyInstaller failed" }
  } finally { Pop-Location }
}

$Src = Join-Path $Dist "ManimStudio\ManimStudio.exe"
if (-not (Test-Path $Src)) {
  throw "bundle not found at $Src (build first, or pass -Dist)"
}

# ---------------------------------------------------------------------------
# 2. Ensure the icon exists
# ---------------------------------------------------------------------------
$Ico = Join-Path $Here "manimstudio.ico"
if (-not (Test-Path $Ico)) {
  Write-Host ">> Generating icon"
  Push-Location $Proj
  try { uv run python (Join-Path $Here "make_ico.py") $Ico }
  finally { Pop-Location }
}

# ---------------------------------------------------------------------------
# 3. Locate ISCC (Inno Setup compiler)
# ---------------------------------------------------------------------------
$Iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $Iscc) {
  foreach ($p in @(
      "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
      "${env:ProgramFiles}\Inno Setup 6\ISCC.exe")) {
    if ($p -and (Test-Path $p)) { $Iscc = $p; break }
  }
}
if (-not $Iscc) {
  throw "ISCC.exe not found. Install Inno Setup 6 (e.g. 'choco install innosetup -y')."
}

# ---------------------------------------------------------------------------
# 4. Compile the installer
# ---------------------------------------------------------------------------
Write-Host ">> Compiling with $Iscc"
& $Iscc "/DMyAppVersion=$Version" "/DDistDir=$Dist" (Join-Path $Here "manimstudio.iss")
if ($LASTEXITCODE) { throw "ISCC failed (exit $LASTEXITCODE)" }

$Out = Join-Path $Dist "ManimStudio-Setup-$Version.exe"
Write-Host ">> Done: $Out"
