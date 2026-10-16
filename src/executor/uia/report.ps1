## report.ps1 -- product code: export the open DIALux report as a PDF via
## the Windows "Microsoft Print to PDF" printer, then report when the file
## has landed.
##
## STATUS: SKELETON -- NOT yet validated on a real machine (written 2026-10-09).
##   The report-mode entry point and the print/save dialog control ids of
##   DIALux evo are not documented. This script is written to ugr.ps1's
##   contract (ASCII only, STEP lines, id escape hatches) so the first real
##   run only has to pin ids via the parameters below -- no logic rewrite.
##
## Steps emitted (parsed by src/executor/uia/report.py):
##   STEP report-mode  ok|fail <detail>
##   STEP report-print ok|fail <detail>
##   STEP report-save  ok|fail <detail>
##   STEP report-wait  ok|fail <detail>
##   STEP report-done  ok
##
## Dialog handling follows the file-dialog lessons already proven in this
## repo (KANBAN: menu -> UIA, dialogs -> Win32 window messages; SetWindowText
## must be written to BOTH the ComboBoxEx32 and its inner Edit; BM_CLICK 1).
##
## ASCII ONLY (PS 5.1 reads UTF-8 .ps1 as GBK; non-ASCII breaks parsing).
param(
    [Parameter(Mandatory = $true)][string]$PdfPath,
    [string]$ProcessName = 'DIALux_x64',
    [int]$WaitTimeoutMs = 60000,
    [int]$DialogTimeoutMs = 15000,
    [string]$ReportMenuId = '',
    [string]$PrintMenuId = '',
    [string]$FileNameId = '',
    [string]$SaveButtonId = ''
)
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

if (-not ([System.Management.Automation.PSTypeName]'RP.U').Type) {
Add-Type @"
using System;
using System.Text;
using System.Runtime.InteropServices;
namespace RP {
  public class U {
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, uint dx, uint dy, uint d, UIntPtr e);
    [DllImport("user32.dll")] public static extern bool AttachThreadInput(int a, int b, bool f);
    [DllImport("kernel32.dll")] public static extern int GetCurrentThreadId();
    [DllImport("user32.dll")] public static extern int GetWindowThreadProcessId(IntPtr h, ref int pid);
    [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern IntPtr FindWindowEx(IntPtr p, IntPtr c, string cls, string win);
    [DllImport("user32.dll")] public static extern IntPtr GetDlgItem(IntPtr h, int id);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern bool SetWindowText(IntPtr h, string t);
    [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, int m, IntPtr w, IntPtr l);
  }
}
"@
}

function Emit([string]$name, [string]$status, [string]$detail = '') {
    Write-Output ("STEP {0} {1} {2}" -f $name, $status, $detail)
}
function Fail([string]$name, [string]$detail) {
    Emit $name 'fail' $detail
    exit 1
}
function ById([string]$id, [int]$ms = 5000) {
    $c = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::AutomationIdProperty, $id)
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.ElapsedMilliseconds -lt $ms) {
        $e = $main.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $c)
        if ($e -ne $null) { return $e }
        Start-Sleep -Milliseconds 120
    }
    return $null
}
function Find-IdPattern([string]$pattern, [int]$ms = 4000) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.ElapsedMilliseconds -lt $ms) {
        $all = $main.FindAll([System.Windows.Automation.TreeScope]::Descendants,
                             [System.Windows.Automation.Condition]::TrueCondition)
        for ($i = 0; $i -lt $all.Count; $i++) {
            $el = $all.Item($i)
            try {
                if ($el.Current.AutomationId -match $pattern) { return $el }
            } catch { }
        }
        Start-Sleep -Milliseconds 200
    }
    return $null
}
function ClickCenter([object]$el) {
    $rect = $el.Current.BoundingRectangle
    $x = [int]($rect.X + ($rect.Width / 2.0))
    $y = [int]($rect.Y + ($rect.Height / 2.0))
    [void][RP.U]::SetCursorPos($x, $y)
    Start-Sleep -Milliseconds 150
    [RP.U]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    [RP.U]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
}
function Wait-Dialog([string]$titleMatch, [int]$ms) {
    # Wait for a #32770 dialog whose title matches (ASCII pattern), return hwnd.
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.ElapsedMilliseconds -lt $ms) {
        $h = [RP.U]::FindWindowEx([IntPtr]::Zero, [IntPtr]::Zero, '#32770', $null)
        while ($h -ne [IntPtr]::Zero) {
            if ([RP.U]::IsWindowVisible($h)) { return $h }
            $h = [RP.U]::FindWindowEx([IntPtr]::Zero, $h, '#32770', $null)
        }
        Start-Sleep -Milliseconds 250
    }
    return [IntPtr]::Zero
}

# ------------------------------------------------------------------ context
$proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } |
        Sort-Object StartTime -Descending | Select-Object -First 1
if ($proc -eq $null) { Fail 'report-mode' 'no-window-process' }
$root = [System.Windows.Automation.AutomationElement]::RootElement
$pc = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ProcessIdProperty, $proc.Id)
$main = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $pc)
if ($main -eq $null) { Fail 'report-mode' 'main-window-not-found' }

# Re-acquire the foreground window right before any click (2026-10-08 lesson).
$hMain = [IntPtr]$proc.MainWindowHandle
$hFg = [RP.U]::GetForegroundWindow()
$tidFg = 0
if ($hFg -ne [IntPtr]::Zero) { [void][RP.U]::GetWindowThreadProcessId($hFg, [ref]$tidFg) }
$tidMe = [RP.U]::GetCurrentThreadId()
$attached = $false
if ($tidFg -ne 0 -and $tidFg -ne $tidMe) {
    $attached = [RP.U]::AttachThreadInput($tidMe, $tidFg, $true)
}
[void][RP.U]::SetForegroundWindow($hMain)
if ($attached) { [void][RP.U]::AttachThreadInput($tidMe, $tidFg, $false) }
Start-Sleep -Milliseconds 400

# ------------------------------------------------------- 1) report mode
# NOTE: pin with -ReportMenuId on first real run; fallback scans for an id
# containing "Report".
$mode = $null
if ($ReportMenuId -ne '') { $mode = ById $ReportMenuId 4000 }
else { $mode = Find-IdPattern 'Report|report' 4000 }
if ($mode -eq $null) { Fail 'report-mode' 'report-entry-not-found-use-ReportMenuId' }
try { $mode.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }
catch { Fail 'report-mode' 'report-entry-invoke-failed' }
Start-Sleep -Milliseconds 1500
Emit 'report-mode' 'ok'

# ------------------------------------------------------- 2) trigger print
$pr = $null
if ($PrintMenuId -ne '') { $pr = ById $PrintMenuId 4000 }
else { $pr = Find-IdPattern 'Print|print' 4000 }
if ($pr -eq $null) { Fail 'report-print' 'print-entry-not-found-use-PrintMenuId' }
try { $pr.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }
catch { ClickCenter $pr }
Start-Sleep -Milliseconds 1200
Emit 'report-print' 'ok'

# ------------------------------------------------------- 3) save dialog
# Assumes the default printer is already "Microsoft Print to PDF"; the print
# dialog may or may not appear. Handle the save (#32770) dialog with the
# proven file-dialog technique.
$dlg = Wait-Dialog '' $DialogTimeoutMs
if ($dlg -eq [IntPtr]::Zero) { Fail 'report-save' 'save-dialog-not-found' }
$combo = $null
if ($FileNameId -ne '') { $combo = [RP.U]::GetDlgItem($dlg, [int]$FileNameId) }
else { $combo = [RP.U]::GetDlgItem($dlg, 1148) }   # ComboBoxEx32 (file dialog id)
if ($combo -eq [IntPtr]::Zero) { Fail 'report-save' 'file-name-combo-not-found' }
[void][RP.U]::SetWindowText($combo, $PdfPath)
$edit = [RP.U]::FindWindowEx($combo, [IntPtr]::Zero, 'Edit', $null)
if ($edit -ne [IntPtr]::Zero) { [void][RP.U]::SetWindowText($edit, $PdfPath) }
Start-Sleep -Milliseconds 400
$saveBtn = $null
if ($SaveButtonId -ne '') { $saveBtn = [RP.U]::GetDlgItem($dlg, [int]$SaveButtonId) }
else { $saveBtn = [RP.U]::GetDlgItem($dlg, 1) }    # IDOK
if ($saveBtn -eq [IntPtr]::Zero) { Fail 'report-save' 'save-button-not-found' }
[void][RP.U]::SendMessage($saveBtn, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)  # BM_CLICK
Emit 'report-save' 'ok' ("path=" + $PdfPath)

# ------------------------------------------------------- 4) wait for the file
$sw = [Diagnostics.Stopwatch]::StartNew()
$lastSize = -1
$stable = 0
while ($sw.ElapsedMilliseconds -lt $WaitTimeoutMs) {
    if (Test-Path -LiteralPath $PdfPath) {
        $sz = (Get-Item -LiteralPath $PdfPath).Length
        if ($sz -gt 0 -and $sz -eq $lastSize) { $stable++ } else { $stable = 0 }
        $lastSize = $sz
        if ($stable -ge 2) {
            Emit 'report-wait' 'ok' ("bytes={0}" -f $sz)
            Emit 'report-done' 'ok'
            exit 0
        }
    }
    Start-Sleep -Milliseconds 500
}
Fail 'report-wait' 'pdf-not-produced'
