# Builds the People First engine (0.I "Ito" + engine/apply_patches.py) and installs it next to the official exe.
#   powershell -NoProfile -File engine\build.ps1            # apply patches (idempotent), incremental Release x64 build, install
#   powershell -NoProfile -File engine\build.ps1 -NoInstall
# Source: C:\pfbuild\cdda (shallow clone of 27939e2), vcpkg: C:\pfbuild\vcpkg (no global "integrate install":
# vcpkg's MSBuild props/targets are force-imported per build).  Log: C:\pfbuild\build.log.
# The result goes to game\cdda-0.I-2026-06-06\cataclysm-tiles-pf.exe; the official cataclysm-tiles.exe is untouched.
param([switch]$NoInstall)
$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$src = 'C:\pfbuild\cdda'
$v = 'C:\pfbuild\vcpkg\scripts\buildsystems\msbuild'
$msb = & 'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe' -products * -requires Microsoft.Component.MSBuild -find 'MSBuild\**\Bin\MSBuild.exe' | Select-Object -First 1

python -I (Join-Path $PSScriptRoot 'apply_patches.py') $src
if ($LASTEXITCODE -ne 0) { Write-Error 'Patching failed (an anchor moved?)'; exit 1 }

$log = 'C:\pfbuild\build.log'
& $msb (Join-Path $src 'msvc-full-features\Cataclysm-vcpkg-static.sln') /m /nologo /v:minimal /t:Cataclysm-vcpkg-static `
    /p:Configuration=Release /p:Platform=x64 "/p:ForceImportBeforeCppProps=$v\vcpkg.props" "/p:ForceImportAfterCppTargets=$v\vcpkg.targets" `
    /p:VcpkgEnableManifest=true "/p:VcpkgAdditionalInstallOptions=--overlay-ports=C:\pfbuild\overlay" *> $log
$ok = $LASTEXITCODE -eq 0
Get-Content $log | Select-String -Pattern ' error |error C|error LNK|fatal error' | Select-Object -First 20 | ForEach-Object { Write-Host $_ -ForegroundColor Red }
if (-not $ok) { Write-Error "Build failed (see $log)"; exit 1 }

$exe = Get-ChildItem $src -Filter 'cataclysm-tiles.exe' -Recurse -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $exe) { $exe = Get-ChildItem $src -Filter 'Cataclysm*.exe' -Recurse | Sort-Object LastWriteTime -Descending | Select-Object -First 1 }
Write-Host "Built: $($exe.FullName) ($([int]($exe.Length/1MB)) MB, $($exe.LastWriteTime))" -ForegroundColor Green
git -C $src diff "--output=$(Join-Path $PSScriptRoot 'people-first.patch')"   # not ">": PowerShell 5.1 writes UTF-16
if (-not $NoInstall) {
    $dest = Join-Path $root 'game\cdda-0.I-2026-06-06\cataclysm-tiles-pf.exe'
    Copy-Item $exe.FullName $dest -Force
    Write-Host "Installed: $dest" -ForegroundColor Green
    python -I (Join-Path $PSScriptRoot 'make_title.py') | Select-Object -Last 1                          # the title art (patch 11)
    python -I (Join-Path $PSScriptRoot 'install_data.py') (Join-Path $root 'game\cdda-0.I-2026-06-06')   # the People key binding, the title file
}
