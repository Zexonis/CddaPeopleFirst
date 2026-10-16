# Brings the running game window to the front (restores it if minimized).  Needs two tries when Windows refuses the
# first SetForegroundWindow from a background process: AttachThreadInput first, then a plain retry.
# After this, take one screenshot before sending keys.
if (-not ('PFFocus.Win' -as [type])) {
    Add-Type -Namespace PFFocus -Name Win -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool IsIconic(System.IntPtr h);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool ShowWindow(System.IntPtr h, int n);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool SetForegroundWindow(System.IntPtr h);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool BringWindowToTop(System.IntPtr h);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern System.IntPtr GetForegroundWindow();
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(System.IntPtr h, System.IntPtr p);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool AttachThreadInput(uint a, uint b, bool f);
[System.Runtime.InteropServices.DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
'@
}
# A --check-mods run is a second cataclysm-tiles process with no window: take the one that has a window.
$p = Get-Process cataclysm-tiles-pf, cataclysm-tiles -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowHandle -ne [IntPtr]::Zero } | Select-Object -First 1
if (-not $p) { Write-Host 'Game not running.'; exit 1 }
$h = $p.MainWindowHandle
# Windows can report the game as the foreground window while Explorer is drawn on top of it (2026-10-12): always raise
# it once, even when it already counts as foreground.
# 2026-10-13: one raise still left Explorer drawn on top twice in a row; the second call always worked, so raise twice.
foreach ($r in 1..2) {
[PFFocus.Win]::ShowWindow($h, 9) | Out-Null; [PFFocus.Win]::BringWindowToTop($h) | Out-Null; [PFFocus.Win]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 300
}
for ($try = 1; $try -le 4; $try++) {
$fg = [PFFocus.Win]::GetForegroundWindow()
if ($fg -eq $h) { break }
$t1 = [PFFocus.Win]::GetWindowThreadProcessId($fg, [IntPtr]::Zero); $t2 = [PFFocus.Win]::GetCurrentThreadId()
[PFFocus.Win]::AttachThreadInput($t2, $t1, $true) | Out-Null
[PFFocus.Win]::ShowWindow($h, 9) | Out-Null; [PFFocus.Win]::BringWindowToTop($h) | Out-Null; [PFFocus.Win]::SetForegroundWindow($h) | Out-Null
[PFFocus.Win]::AttachThreadInput($t2, $t1, $false) | Out-Null
Start-Sleep -Milliseconds 300
[PFFocus.Win]::ShowWindow($h, 9) | Out-Null
[PFFocus.Win]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 400
}
# 2026-10-15: the game counted as foreground while still minimized (off-screen at -25600), so the loop above never ran
# and the desktop showed.  Restore while it's iconic.
for ($try = 1; $try -le 3 -and [PFFocus.Win]::IsIconic($h); $try++) {
[PFFocus.Win]::ShowWindow($h, 9) | Out-Null; [PFFocus.Win]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 400
}
$ok = ([PFFocus.Win]::GetForegroundWindow() -eq $h) -and -not [PFFocus.Win]::IsIconic($h)
Write-Host "Game in front (pid $($p.Id)): $ok (minimized: $([PFFocus.Win]::IsIconic($h)))"
