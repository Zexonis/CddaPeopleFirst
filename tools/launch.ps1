# Starts the game for a test session: closes a running instance (only if -Restart), clears the mod's flexbuffer cache
# (a stale cache can keep old JSON alive after a deploy), launches, and prints the PID.
# Then start the watcher in the background:  powershell -NoProfile -File tools\gamewatch.ps1 -ProcessId <pid>
param([string]$Mod = 'PeopleFirst', [switch]$Restart, [switch]$Engine)
$root = Split-Path $PSScriptRoot -Parent
$game = Join-Path $root 'game\cdda-0.I-2026-06-06'
$running = Get-Process cataclysm-tiles, cataclysm-tiles-pf -ErrorAction SilentlyContinue
if ($running) {
    if (-not $Restart) { Write-Host "Game already running (pid $($running.Id -join ', ')).  Use -Restart to close it first (save before!)."; exit 1 }
    $running | Stop-Process -Force; Start-Sleep -Seconds 1
}
Remove-Item -Recurse -Force (Join-Path $game "cache\mods\$Mod") -ErrorAction SilentlyContinue
$exe = if ($Engine) { 'cataclysm-tiles-pf.exe' } else { 'cataclysm-tiles.exe' }   # -Engine: the People First engine build
$p = Start-Process -FilePath (Join-Path $game $exe) -WorkingDirectory $game -PassThru
Write-Output $p.Id
