# Lints a mod, then mirrors it into the game copy's user mods folder so it shows up in-game.
# Usage: .\tools\deploy.ps1 -Mod MyModFolder
param([Parameter(Mandatory)][string]$Mod)

$root = Split-Path $PSScriptRoot -Parent
$src  = Join-Path $root "mods\$Mod"
$dst  = Join-Path $root "game\cdda-0.I-2026-06-06\mods\$Mod"

if (-not (Test-Path (Join-Path $src 'modinfo.json'))) { Write-Error "No modinfo.json in $src"; exit 1 }

& (Join-Path $PSScriptRoot 'lint.ps1') -Mod $Mod
if ($LASTEXITCODE -ne 0) { Write-Error 'Lint failed; not deploying.'; exit 1 }

# /MIR is scoped to this one mod folder only.
robocopy $src $dst /MIR /NFL /NDL /NJH /NJS /NP | Out-Null
if ($LASTEXITCODE -ge 8) { Write-Error "robocopy failed ($LASTEXITCODE)"; exit 1 }
Write-Host "Deployed $Mod -> $dst" -ForegroundColor Green
exit 0
