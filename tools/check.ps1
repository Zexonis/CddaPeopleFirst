# Deploys a mod, then has the real game engine load and validate it headlessly (--check-mods).
# Usage: .\tools\check.ps1 -Mod PeopleFirst -Id people_first
#        .\tools\check.ps1 -Mod PeopleFirstEngine -Id people_first_engine -Engine   (needs the patched exe: u_set_name)
param([Parameter(Mandatory)][string]$Mod, [Parameter(Mandatory)][string]$Id, [switch]$Engine)
$exe = if ($Engine) { 'cataclysm-tiles-pf.exe' } else { 'cataclysm-tiles.exe' }

$root = Split-Path $PSScriptRoot -Parent
$game = Join-Path $root 'game\cdda-0.I-2026-06-06'

# Text style errors (three dots, one space after a period) only show in debug.log on world load, so catch them here.
python -I (Join-Path $PSScriptRoot 'textcheck.py') (Join-Path $root "mods\$Mod")
if ($LASTEXITCODE -ne 0) { Write-Host 'Text style check FAILED (see above).' -ForegroundColor Red; exit 1 }

& (Join-Path $PSScriptRoot 'deploy.ps1') -Mod $Mod
if ($LASTEXITCODE -ne 0) { exit 1 }

$out = Join-Path $env:TEMP 'cdda_check_out.txt'
$err = Join-Path $env:TEMP 'cdda_check_err.txt'
# The game resolves data/ and mods/ relative to the working directory.
$p = Start-Process -FilePath (Join-Path $game $exe) -ArgumentList '--check-mods', $Id `
    -WorkingDirectory $game -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -NoNewWindow
# Poll instead of blocking: a crash ("The program has crashed", SIGSEGV) or a load-error popup is a modal OS dialog
# that waits forever for a click.  Detect it, record it, kill the process, and fail fast (no human needed).
. (Join-Path $PSScriptRoot 'gamewatch.ps1')
$deadline = (Get-Date).AddSeconds(180)
while (-not $p.HasExited) {
    $pop = Get-GamePopups $p.Id
    if ($pop.Count -gt 0) {
        Start-Sleep -Milliseconds 1500
        Write-CrashReport $p.Id $pop 'check-mods'
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        Get-Content $err -ErrorAction SilentlyContinue | Select-Object -Last 20 | Write-Host -ForegroundColor Red
        Write-Host 'Engine check CRASHED or hit a popup (report above; also in game config\pf_crashes.log).' -ForegroundColor Red
        exit 2
    }
    if ((Get-Date) -gt $deadline) {
        Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        Get-Content $err -ErrorAction SilentlyContinue | Write-Host -ForegroundColor Red
        Write-Error 'check-mods timed out after 3 minutes (see above)'; exit 1
    }
    Start-Sleep -Seconds 1
}

Get-Content $out
$errors = Get-Content $err -Raw
if ($errors -and $errors.Trim()) {
    Write-Host $errors -ForegroundColor Red
    Write-Host 'Engine check FAILED.' -ForegroundColor Red
    exit 1
}
Write-Host 'Engine check passed: mod loaded with no errors.' -ForegroundColor Green
exit 0
