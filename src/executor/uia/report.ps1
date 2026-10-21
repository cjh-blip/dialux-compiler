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
    [int]$ReportTabIndex = -1,
    [string]$PrintMenuId = '',
    [string]$PrinterComboId = '',
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
    [DllImport("user32.dll", CharSet=CharSet.Auto)] public static extern int GetWindowText(IntPtr h, StringBuilder s, int max);
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
function Esc([string]$s) {
    # ASCII-safe rendering for detail payloads (selected tab names are CJK on
    # this build; PS 5.1 pipes must stay pure ASCII).
    $sb = New-Object System.Text.StringBuilder
    foreach ($ch in $s.ToCharArray()) {
        $c = [int][char]$ch
        if ($c -lt 32) { [void]$sb.Append(' ') }
        elseif ($c -lt 127) { [void]$sb.Append($ch) }
        else { [void]$sb.Append(('\u{0:X4}' -f $c)) }
    }
    return $sb.ToString()
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
function Wait-Dialog([int]$ms, [IntPtr]$skipHwnd) {
    # Wait for a visible #32770 OWNED BY DIALUX, optionally skipping one hwnd.
    # 2026-10-19 fixes (measured on the real machine):
    #   (a) $null marshals to an EMPTY string, so the old call only matched
    #       blank-title windows -- the same trap dialux_driver.ps1 documented;
    #   (b) no process filter: any application's dialog could be returned;
    #   (c) no way to wait for the SECOND dialog, but print -> save IS two.
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.ElapsedMilliseconds -lt $ms) {
        $h = [RP.U]::FindWindowEx([IntPtr]::Zero, [IntPtr]::Zero, '#32770', [NullString]::Value)
        while ($h -ne [IntPtr]::Zero) {
            if ($h -ne $skipHwnd -and [RP.U]::IsWindowVisible($h)) {
                $dpid = 0
                [void][RP.U]::GetWindowThreadProcessId($h, [ref]$dpid)
                if ($dpid -eq $proc.Id) { return $h }
            }
            $h = [RP.U]::FindWindowEx([IntPtr]::Zero, $h, '#32770', [NullString]::Value)
        }
        Start-Sleep -Milliseconds 250
    }
    return [IntPtr]::Zero
}
function Get-DlgUiText([IntPtr]$h) {
    # Joined UIA names of the dialog and its descendants. Used to CLASSIFY
    # print vs save without ever putting a Chinese title in this ASCII file.
    try {
        $w = [System.Windows.Automation.AutomationElement]::FromHandle($h)
        $head = ''
        try { $head = [string]$w.Current.Name } catch { }
        $all = $w.FindAll([System.Windows.Automation.TreeScope]::Descendants,
                          [System.Windows.Automation.Condition]::TrueCondition)
        $sb = New-Object System.Text.StringBuilder 4096
        for ($i = 0; $i -lt $all.Count; $i++) {
            try { [void]$sb.Append($all.Item($i).Current.Name).Append(' ') } catch { }
        }
        return ($head + ' ' + $sb.ToString())
    } catch { return '' }
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
# Measured 2026-10-19 E2: the entry is a TabItem inside 'ModeSelectionTabControl'
# with NO AutomationId, NO Invoke pattern, SelectionItem ONLY -- the old
# Find-IdPattern 'Report|report' scanned the whole tree and hit zero. Order:
#   1) -ReportMenuId (caller pinned id) wins;
#   2) else the id pattern scan (still right on English builds);
#   3) else TabItems of ModeSelectionTabControl: Name match first, then the
#      -ReportTabIndex ordinal. The ordinal is an ESCAPE HATCH whose index was
#      never measured here (only coordinates 701,158 were), so the default is
#      -1 = disabled -- we do not guess an index.
$mode = $null
$modeVia = ''
if ($ReportMenuId -ne '') { $mode = ById $ReportMenuId 4000; if ($mode -ne $null) { $modeVia = 'id' } }
if ($mode -eq $null) {
    $mode = Find-IdPattern 'Report|report' 3000
    if ($mode -ne $null) { $modeVia = 'id-pattern' }
}
if ($mode -eq $null) {
    $tabs = ById 'ModeSelectionTabControl' 3000
    if ($tabs -ne $null) {
        $tc = New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
            [System.Windows.Automation.ControlType]::TabItem)
        $all = $tabs.FindAll([System.Windows.Automation.TreeScope]::Descendants, $tc)
        $items = @()
        for ($i = 0; $i -lt $all.Count; $i++) { $items += $all.Item($i) }
        # 2026-10-20 real machine: 20 TabItems and NONE of them contains
        # 'Report' -- the report mode tab is
        # 'Dial.Dialux.InteractionModes.Results.ResultMode' (Result != Report),
        # and its 0-based index (19, measured under the calculation mode) shifts
        # with the tool tabs in [0..15]. Two passes: the old Report pattern
        # first, then the MODE namespace carrying Result -- tool tabs share this
        # control, so a bare 'Result' anywhere must not win over the mode tab.
        $namePats = @('Report|report', 'InteractionModes.*Result')
        $nameVia = @('tab-name', 'tab-name-resultmode')
        for ($pi = 0; $pi -lt $namePats.Count -and $mode -eq $null; $pi++) {
            foreach ($ti in $items) {
                $nm = ''
                try { $nm = [string]$ti.Current.Name } catch { }
                if ($nm -match $namePats[$pi]) { $mode = $ti; $modeVia = $nameVia[$pi]; break }
            }
        }
        if ($mode -eq $null -and $ReportTabIndex -ge 0 -and $ReportTabIndex -lt $items.Count) {
            $mode = $items[$ReportTabIndex]
            $modeVia = ("tab-index={0}" -f $ReportTabIndex)
        }
    }
}
if ($mode -eq $null) {
    Fail 'report-mode' 'report-entry-not-found-use-ReportMenuId-or-ReportTabIndex'
}
$acted = $false
try { $mode.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke(); $acted = $true }
catch { }
if (-not $acted) {
    try {
        $mode.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()
        $acted = $true
    } catch { Fail 'report-mode' 'report-entry-neither-invoke-nor-select' }
}
Start-Sleep -Milliseconds 1500
# 2026-10-20 second-gun receipt (item5, two runs): SelectionItem.Select()
# reported ok but the mode bar was still on the calculation tool afterwards,
# so every Print id scan downstream came back empty
# (print-entry-not-found-use-PrintMenuId). Read back WHICH tab actually
# carries the selection before continuing. The gate records what is
# observable now; WHY Select did not land (no-op vs re-bounced) is the next
# real-machine round's diagnosis, not a conclusion baked into this file.
# Accepted name = ResultMode: the measured report tab is
# Dial.Dialux.InteractionModes.Results.ResultMode on this build. The English
# 'Report' first pass above would need its pattern added to this gate too if
# such a build ever shows up -- pending real machine, not guessed now.
$selName = ''
$readback = 'no-tabcontrol'
$tabs2 = ById 'ModeSelectionTabControl' 2500
if ($tabs2 -ne $null) {
    $readback = 'no-selected-tab'
    $tc2 = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::TabItem)
    $all2 = $tabs2.FindAll([System.Windows.Automation.TreeScope]::Descendants, $tc2)
    $swSel = [Diagnostics.Stopwatch]::StartNew()
    while ($swSel.ElapsedMilliseconds -lt 2000) {
        for ($i2 = 0; $i2 -lt $all2.Count; $i2++) {
            $isSel = $false
            try { $isSel = $all2.Item($i2).Current.IsSelected } catch { }
            if ($isSel) {
                try { $selName = [string]$all2.Item($i2).Current.Name } catch { $selName = '?unreadable' }
                $readback = 'selected-tab'
                break
            }
        }
        if ($selName -ne '') { break }
        Start-Sleep -Milliseconds 250
    }
}
if ($selName -notmatch 'ResultMode') {
    # human-readable failure carrying the scene (Esc keeps the pipe ASCII)
    Fail 'report-mode' ("report-mode-not-confirmed selected='{0}' readback={1} via={2}" -f (Esc $selName), $readback, $modeVia)
}
Emit 'report-mode' 'ok' ("via={0} selected={1}" -f $modeVia, (Esc $selName))

# ------------------------------------------------------- 2) trigger print
# Measured 2026-10-19 E2: the entry id is ButtonPrintDocument, and a raw
# Find-IdPattern 'Print' ambiguously hits ReportModePrint (a radio button), so
# the pinned id or the measured id wins before the pattern scan.
$pr = $null
$prVia = ''
if ($PrintMenuId -ne '') { $pr = ById $PrintMenuId 4000; if ($pr -ne $null) { $prVia = 'id' } }
if ($pr -eq $null) { $pr = ById 'ButtonPrintDocument' 2500; if ($pr -ne $null) { $prVia = 'measured-id' } }
if ($pr -eq $null) { $pr = Find-IdPattern 'Print|print' 3000; if ($pr -ne $null) { $prVia = 'pattern' } }
if ($pr -eq $null) { Fail 'report-print' 'print-entry-not-found-use-PrintMenuId' }
try { $pr.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke() }
catch { ClickCenter $pr }
Start-Sleep -Milliseconds 1200
Emit 'report-print' 'ok' ("via=" + $prVia)

# ------------------------------------- 3) print dialog -> printer -> save dialog
# Measured 2026-10-19 E2: the Windows PRINT dialog opens first (#32770; print
# button = GetDlgItem(1) 'Print(&P)', cancel = 2), and the machine's default
# printer is an OFFLINE device, so the PDF printer must be chosen INSIDE this
# dialog -- system settings are outside the allowed scope. The Print-to-PDF
# SAVE window follows as the second dialog.
# Classification uses UIA text markers measured on the machine (the printer
# list carries 'Microsoft Print to PDF' / 'OneNote' / 'Brother'; the save
# window's type row carries '.pdf'). An unclassifiable dialog FAILS with its
# text attached instead of guessing -- no silent mis-routing.
$hDlg1 = Wait-Dialog $DialogTimeoutMs ([IntPtr]::Zero)
if ($hDlg1 -eq [IntPtr]::Zero) { Fail 'report-printer' 'print-dialog-not-found' }
$txt1 = Get-DlgUiText $hDlg1
$hSave = [IntPtr]::Zero

if ($txt1 -match 'Print to PDF|OneNote|Brother') {
    # --- select the printer: UIA expand + select on the printer combo;
    #     -PrinterComboId (Win32 control id) pins the combo when auto fails.
    $comboEl = $null
    if ($PrinterComboId -ne '') {
        $cw = [RP.U]::GetDlgItem($hDlg1, [int]$PrinterComboId)
        if ($cw -eq [IntPtr]::Zero) { Fail 'report-printer' 'printer-combo-id-not-found' }
        try { $comboEl = [System.Windows.Automation.AutomationElement]::FromHandle($cw) } catch { }
    } else {
        try {
            $dw = [System.Windows.Automation.AutomationElement]::FromHandle($hDlg1)
            $cc = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
                [System.Windows.Automation.ControlType]::ComboBox)
            $comboEl = $dw.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cc)
        } catch { }
    }
    $printerOk = $false
    if ($comboEl -ne $null) {
        try {
            $comboEl.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand()
            Start-Sleep -Milliseconds 600
            $lc = New-Object System.Windows.Automation.PropertyCondition(
                [System.Windows.Automation.AutomationElement]::NameProperty, 'Microsoft Print to PDF')
            $li = $comboEl.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $lc)
            if ($li -ne $null) {
                $li.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()
                $printerOk = $true
            }
            try { $comboEl.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Collapse() } catch { }
        } catch { }
    }
    if (-not $printerOk) {
        Fail 'report-printer' 'printer-not-selectable-use-PrinterComboId'
    }
    Start-Sleep -Milliseconds 500
    $hPrint = [RP.U]::GetDlgItem($hDlg1, 1)          # measured: print button = GetDlgItem(1)
    if ($hPrint -eq [IntPtr]::Zero) { Fail 'report-printer' 'print-button-not-found' }
    [void][RP.U]::SendMessage($hPrint, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)   # BM_CLICK
    Emit 'report-printer' 'ok' 'printer=Microsoft Print to PDF'
    $hSave = Wait-Dialog $DialogTimeoutMs $hDlg1     # the save window is the NEXT dialog
    if ($hSave -eq [IntPtr]::Zero) { Fail 'report-save' 'save-dialog-not-found' }
} elseif ($txt1 -match '\.pdf') {
    Emit 'report-printer' 'ok' 'print-dialog-absent-default-is-pdf'
    $hSave = $hDlg1
} else {
    $snip = ($txt1 -replace '\s+', ' ')
    if ($snip.Length -gt 120) { $snip = $snip.Substring(0, 120) }
    Fail 'report-printer' ("unclassified-dialog ui='{0}'" -f $snip)
}

# ------------------------------------------------------- 4) save dialog
# Measured 2026-10-19 E2: the Print-to-PDF window is custom -- NO 1148, the
# filename row is the wide ComboBox with the SMALLEST top (measured 1968172 at
# T=519 vs the type row at T=546; the wrong pick wrote the type field once),
# its inner Edit is 14748318, save = GetDlgItem(1). SetWindowText there reads
# back but never renders and BM_CLICK then does nothing; clipboard + WM_PASTE
# lands in about a second.
$combo = $null
$hEditS = [IntPtr]::Zero
if ($FileNameId -ne '') {
    $combo = [RP.U]::GetDlgItem($hSave, [int]$FileNameId)
}
if ($combo -eq [IntPtr]::Zero -or $combo -eq $null) {
    # auto: ComboBoxes that own an inner Edit, lowest top wins (measured rule)
    try {
        $dw = [System.Windows.Automation.AutomationElement]::FromHandle($hSave)
        $cc = New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
            [System.Windows.Automation.ControlType]::ComboBox)
        $ec = New-Object System.Windows.Automation.PropertyCondition(
            [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
            [System.Windows.Automation.ControlType]::Edit)
        $all = $dw.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cc)
        $bestY = [double]::MaxValue
        $bestEl = $null
        $bestEdit = $null
        for ($i = 0; $i -lt $all.Count; $i++) {
            $el = $all.Item($i)
            $ed = $el.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $ec)
            if ($ed -eq $null) { continue }
            $y = $el.Current.BoundingRectangle.Y
            if ($y -lt $bestY) { $bestY = $y; $bestEl = $el; $bestEdit = $ed }
        }
        if ($bestEl -ne $null) {
            $combo = [IntPtr]$bestEl.Current.NativeWindowHandle
            if ($bestEdit.Current.NativeWindowHandle -ne 0) {
                $hEditS = [IntPtr]$bestEdit.Current.NativeWindowHandle
            }
        }
    } catch { }
}
if (($combo -eq [IntPtr]::Zero -or $combo -eq $null) -and $hEditS -eq [IntPtr]::Zero) {
    Fail 'report-save' 'file-name-combo-not-found'
}
if ($hEditS -eq [IntPtr]::Zero -and $combo -ne [IntPtr]::Zero) {
    $hEditS = [RP.U]::FindWindowEx($combo, [IntPtr]::Zero, 'Edit', [NullString]::Value)
    if ($hEditS -eq [IntPtr]::Zero) {
        $hIn = [RP.U]::FindWindowEx($combo, [IntPtr]::Zero, 'ComboBox', [NullString]::Value)
        if ($hIn -ne [IntPtr]::Zero) {
            $hEditS = [RP.U]::FindWindowEx($hIn, [IntPtr]::Zero, 'Edit', [NullString]::Value)
        }
    }
}
$fillH = if ($hEditS -ne [IntPtr]::Zero) { $hEditS } else { $combo }
$fillVia = 'clipboard'
$oldClip = $null
$clipOk = $false
try { $oldClip = Get-Clipboard -Raw; $clipOk = $true } catch { }
try {
    Set-Clipboard -Value $PdfPath
    [void][RP.U]::SendMessage($fillH, 0x0302, [IntPtr]::Zero, [IntPtr]::Zero)   # WM_PASTE
    if ($hEditS -ne [IntPtr]::Zero -and $fillH -ne $hEditS) {
        [void][RP.U]::SendMessage($hEditS, 0x0302, [IntPtr]::Zero, [IntPtr]::Zero)
    }
    Start-Sleep -Milliseconds 300
} catch { $fillVia = 'settext' }
if ($clipOk) { try { Set-Clipboard -Value $oldClip } catch { } }   # restore the user's clipboard
$sb = New-Object System.Text.StringBuilder 1024
[void][RP.U]::GetWindowText($fillH, $sb, 1024)
if ($sb.ToString().Trim().Length -eq 0) {
    # fallback: legacy double-layer write (right on some builds)
    [void][RP.U]::SetWindowText($fillH, $PdfPath)
    Start-Sleep -Milliseconds 400
    $sb2 = New-Object System.Text.StringBuilder 1024
    [void][RP.U]::GetWindowText($fillH, $sb2, 1024)
    if ($sb2.ToString().Trim().Length -eq 0) { Fail 'report-save' 'filename-fill-had-no-effect' }
    $fillVia = 'settext-fallback'
}
$saveBtn = $null
if ($SaveButtonId -ne '') { $saveBtn = [RP.U]::GetDlgItem($hSave, [int]$SaveButtonId) }
else { $saveBtn = [RP.U]::GetDlgItem($hSave, 1) }    # measured: save = GetDlgItem(1)
if ($saveBtn -eq [IntPtr]::Zero) { Fail 'report-save' 'save-button-not-found' }
[void][RP.U]::SendMessage($saveBtn, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)  # BM_CLICK
Emit 'report-save' 'ok' ("via={0} path={1}" -f $fillVia, $PdfPath)

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
