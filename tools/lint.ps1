# Formats/validates every .json file in a mod using the game's bundled json_formatter.
# Usage: .\tools\lint.ps1 -Mod MyModFolder      (or omit -Mod to lint all mods)
param([string]$Mod)

$root      = Split-Path $PSScriptRoot -Parent
$game      = Join-Path $root 'game\cdda-0.I-2026-06-06'
$formatter = Join-Path $game 'json_formatter.exe'
$target    = if ($Mod) { Join-Path $root "mods\$Mod" } else { Join-Path $root 'mods' }

if (-not (Test-Path $target)) { Write-Error "Not found: $target"; exit 1 }

$failed = 0
Get-ChildItem $target -Recurse -Filter *.json | ForEach-Object {
    # A UTF-8 BOM crashes json_formatter silently, so reject it up front.
    $head = [IO.File]::ReadAllBytes($_.FullName) | Select-Object -First 3
    if ($head.Count -eq 3 -and $head[0] -eq 0xEF -and $head[1] -eq 0xBB -and $head[2] -eq 0xBF) {
        $failed++; Write-Host "FAIL $($_.FullName): has a UTF-8 BOM; save as UTF-8 without BOM" -ForegroundColor Red; return
    }
    # json_formatter exits 1 both when it reformats a file and on a parse error, so check the text.
    $out = & $formatter $_.FullName 2>&1
    if ($out -match 'Json error' -or $LASTEXITCODE -notin 0, 1) { $failed++; Write-Host "FAIL $($_.FullName)" -ForegroundColor Red; $out | Write-Host }
    elseif ($out -match 'Has been linted') { Write-Host "fixed $($_.Name)" -ForegroundColor Yellow }
}
if ($failed) { Write-Host "$failed file(s) failed to parse." -ForegroundColor Red; exit 1 }
Write-Host 'All JSON parsed OK.' -ForegroundColor Green
exit 0
