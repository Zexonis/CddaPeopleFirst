# Watches a running cataclysm-tiles process for OS-level popups (the "The program has crashed" box, SIGSEGV etc.)
# so a crash never needs a human to click OK.  On a popup: records its text, kills the process, prints a report.
#
# Standalone (in-game sessions, run in the background):
#   powershell -NoProfile -File tools\gamewatch.ps1 -ProcessId 1234 [-MaxMinutes 240]
#   Exit codes: 0 = the game closed normally, 3 = crashed (killed, report printed), 4 = gave up after MaxMinutes,
#   -Ignore 'regex','regex' skips known errors (e.g. test-world leftovers).
#   5 = an in-game error was logged (game left running: dismiss the error screen, fix, restart the watcher).
# Dot-sourced (check.ps1): provides Get-GamePopups and Write-CrashReport.
param([int]$ProcessId = 0, [int]$MaxMinutes = 240, [string[]]$Ignore = @())

$root = Split-Path $PSScriptRoot -Parent
$game = Join-Path $root 'game\cdda-0.I-2026-06-06'

if (-not ('PFWatch.Win' -as [type])) {
    Add-Type -Namespace PFWatch -Name Win -MemberDefinition @'
public delegate bool EnumProc(System.IntPtr h, System.IntPtr l);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc cb, System.IntPtr l);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool EnumChildWindows(System.IntPtr p, EnumProc cb, System.IntPtr l);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(System.IntPtr h, out uint pid);
[System.Runtime.InteropServices.DllImport("user32.dll")] public static extern bool IsWindowVisible(System.IntPtr h);
[System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)] public static extern int GetWindowText(System.IntPtr h, System.Text.StringBuilder s, int n);
[System.Runtime.InteropServices.DllImport("user32.dll", CharSet = System.Runtime.InteropServices.CharSet.Unicode)] public static extern int GetClassName(System.IntPtr h, System.Text.StringBuilder s, int n);
public static string Text(System.IntPtr h) { var s = new System.Text.StringBuilder(2048); GetWindowText(h, s, 2048); return s.ToString(); }
public static string Cls(System.IntPtr h) { var s = new System.Text.StringBuilder(256); GetClassName(h, s, 256); return s.ToString(); }
public static System.Collections.Generic.List<string> Popups(uint wanted) {
    var found = new System.Collections.Generic.List<string>();
    EnumWindows((h, l) => {
        uint pid; GetWindowThreadProcessId(h, out pid);
        if (pid == wanted && IsWindowVisible(h) && Cls(h) == "#32770") {
            var parts = new System.Collections.Generic.List<string>();
            parts.Add(Text(h));
            EnumChildWindows(h, (c, l2) => { if (Cls(c) == "Static") { var t = Text(c); if (t.Length > 0) parts.Add(t); } return true; }, System.IntPtr.Zero);
            found.Add(string.Join(" | ", parts));
        }
        return true;
    }, System.IntPtr.Zero);
    return found;
}
'@
}

function Get-GamePopups([int]$TargetPid) { return [PFWatch.Win]::Popups([uint32]$TargetPid) }

function Write-CrashReport([int]$TargetPid, [string[]]$Popups, [string]$Label) {
    $stamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $report = @("[$stamp] $Label crashed (pid $TargetPid).  Popup: $($Popups -join ' || ')")
    $crash = Join-Path $game 'config\crash.log'
    if (Test-Path $crash) {
        $age = (Get-Date) - (Get-Item $crash).LastWriteTime
        if ($age.TotalMinutes -lt 5) { $report += 'crash.log (fresh):'; $report += (Get-Content $crash | Select-String -Pattern 'dbghelp: (\S+)' | ForEach-Object { '  ' + $_.Matches[0].Groups[1].Value } | Select-Object -First 25) }
        else { $report += "crash.log is stale ($([int]$age.TotalMinutes) min old): the engine writes it after the popup is closed." }
    }
    $log = Join-Path $game 'config\debug.log'
    if (Test-Path $log) { $report += 'debug.log tail:'; $report += (Get-Content $log -Tail 12 | ForEach-Object { '  ' + $_.Substring(0, [Math]::Min(200, $_.Length)) }) }
    $report | Add-Content -Path (Join-Path $game 'config\pf_crashes.log')
    $report | Write-Host -ForegroundColor Red
}

# powershell -File passes -Ignore 'a','b' as the single string 'a,b'
$Ignore = @($Ignore | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
if ($ProcessId -gt 0) {
    $p = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
    if (-not $p) { Write-Host "No process $ProcessId."; exit 0 }
    $null = $p.Handle   # hold a handle now, or ExitCode can't be read once the process is gone
    $deadline = (Get-Date).AddMinutes($MaxMinutes)
    # In-game error screens ("An error has occurred!") are drawn inside the game window, not as OS dialogs, so also
    # tail debug.log: new ERROR lines (except the harmless stale-cache warnings) end the watch with exit 5, game left running.
    $log = Join-Path $game 'config\debug.log'
    $seen = if (Test-Path $log) { (Get-Item $log).Length } else { 0 }
    while ((Get-Date) -lt $deadline) {
        if ($p.HasExited) {
            # 2026-10-14: an invalid-talker error, then a segfault with no dialog; this said "closed normally".  A crash
            # without a popup still leaves a non-zero exit code and a Windows Error Reporting record.
            Start-Sleep -Seconds 3
            $code = try { $p.ExitCode } catch { $null }
            $wer = Get-WinEvent -FilterHashtable @{ LogName = 'Application'; Id = 1000; StartTime = $p.StartTime } -ErrorAction SilentlyContinue |
                Where-Object { $_.Message -match 'cataclysm' -and $_.Message -match ('0x{0:x}' -f $ProcessId) } | Select-Object -First 1
            if ($wer -or ($code -ne $null -and $code -ne 0)) {
                $why = if ($wer) { ($wer.Message -split "`n" | Select-String 'Exception code|Fault offset' | ForEach-Object { $_.ToString().Trim() }) -join '; ' } else { "exit code $code" }
                Write-CrashReport $ProcessId @("no dialog; $why") 'Game'
                exit 3
            }
            Write-Host "Game $ProcessId closed normally."; exit 0
        }
        if (Test-Path $log) {
            $len = (Get-Item $log).Length
            if ($len -lt $seen) { $seen = 0 }  # a new session rewrote the log
            if ($len -gt $seen) {
                $fs = [IO.File]::Open($log, 'Open', 'Read', 'ReadWrite'); $fs.Seek($seen, 'Begin') | Out-Null
                $new = (New-Object IO.StreamReader($fs)).ReadToEnd(); $fs.Close(); $seen = $len
                $errs = $new -split "`n" | Where-Object { $_ -match 'ERROR|DEBUG\s*:' -and $_ -notmatch 'Stale game data|load_flexbuffer_if_not_stale|error message will follow backtrace|Backtrace' }
                foreach ($pat in $Ignore) { $errs = $errs | Where-Object { $_ -notmatch $pat } }
                if ($errs) {
                    $report = @("[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] In-game error (pid $ProcessId, game still running):") + ($errs | Select-Object -First 15 | ForEach-Object { '  ' + $_.Trim().Substring(0, [Math]::Min(220, $_.Trim().Length)) })
                    $report | Add-Content -Path (Join-Path $game 'config\pf_crashes.log')
                    $report | Write-Host -ForegroundColor Yellow
                    exit 5
                }
            }
        }
        $pop = Get-GamePopups $ProcessId
        if ($pop.Count -gt 0) {
            Start-Sleep -Milliseconds 1500   # let the engine finish writing what it can
            Write-CrashReport $ProcessId $pop 'Game'
            Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
            exit 3
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "Watcher gave up after $MaxMinutes minutes; game $ProcessId still running."
    exit 4
}
