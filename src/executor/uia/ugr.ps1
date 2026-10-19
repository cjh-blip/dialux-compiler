## ugr.ps1 -- product code: place/select a UGR calculation point in the open
## DIALux project, set the step (deg) and the viewing range, run the
## calculation and read the maximum UGR value back.
##
## This is the productised form of the 2026-10-08 hand probe (calculation
## object -> UGR metric + step/range -> CalculationButtonStart -> results
## overview). One call, machine-readable STEP lines, same contract as
## luminaire.ps1 / furniture.ps1.
##
## Steps emitted (parsed by src/executor/uia/ugr.py):
##   STEP ugr-tool   ok|fail <detail>
##   STEP ugr-point  ok|fail <detail>
##   STEP ugr-metric ok|fail <detail>
##   STEP ugr-params ok|fail <detail>
##   STEP ugr-calc   ok|fail <detail>
##   STEP ugr-read   ok|fail <detail>   (detail = text=<escaped panel text>)
##   STEP ugr-done   ok
##
## The text= payload is escaped: every character above 0x7E becomes \uXXXX so
## the pipe stays pure ASCII (PS 5.1 writes the .ps1 / stdout as ANSI, CJK
## would be mangled). src/executor/uia/ugr.py decodes it back.
##
## ASCII ONLY (PS 5.1 reads UTF-8 .ps1 as GBK; CJK breaks parsing).
##
## Escape hatch for the real machine: the property-panel control ids of DIALux
## evo are not documented. The -UgrCheckId / -StepId / -RangeFromId /
## -RangeToId / -ResultId parameters let a run pin the exact AutomationId
## without editing this script.
##
## 2026-10-19 real-machine calibration (E phase 2): the localised property panel
## does not match the English scan patterns; measured ids are now tried FIRST
## in the default path (see section 4) and can still be overridden:
##   spacing      = StepSize_Ugr
##   angle begin  = AngleRangeBegin_Ugr
##   angle end    = AngleRangeEnd_Ugr
##   UGR toggle   = aid 'Ugr'
## -CalcButtonId (new) pins the start button the same way.
param(
    [string]$PointX = '',
    [string]$PointY = '',
    [string]$PointZ = '',
    [double]$StepDeg = 15,
    [double]$RangeFromDeg = 0,
    [double]$RangeToDeg = 360,
    [double]$Target = 19.0,
    [string]$ProcessName = 'DIALux_x64',
    [int]$TimeoutMs = 8000,
    [int]$CalcTimeoutMs = 300000,
    [string]$UgrCheckId = '',
    [string]$StepId = '',
    [string]$RangeFromId = '',
    [string]$RangeToId = '',
    [string]$ResultId = '',
    [string]$CalcButtonId = ''
)
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes

if (-not ([System.Management.Automation.PSTypeName]'UG.U').Type) {
Add-Type @"
using System;
using System.Text;
using System.Collections.Generic;
using System.Runtime.InteropServices;
namespace UG {
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
    [DllImport("user32.dll")] public static extern IntPtr SendMessage(IntPtr h, int m, IntPtr w, IntPtr l);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, int m, IntPtr w, IntPtr l);
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
function Find-Pattern([string]$pattern, [int]$ms = 4000) {
    # Scan every descendant; used for controls whose AutomationId is unknown
    # (UGR checkbox / step / range fields). ASCII pattern only.
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.ElapsedMilliseconds -lt $ms) {
        $all = $main.FindAll([System.Windows.Automation.TreeScope]::Descendants,
                             [System.Windows.Automation.Condition]::TrueCondition)
        for ($i = 0; $i -lt $all.Count; $i++) {
            $el = $all.Item($i)
            try {
                $id = $el.Current.AutomationId
                $nm = $el.Current.Name
                if ($id -match $pattern -or $nm -match $pattern) { return $el }
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
    [void][UG.U]::SetCursorPos($x, $y)
    Start-Sleep -Milliseconds 150
    [UG.U]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
    [UG.U]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
}
function Set-Val([object]$el, [string]$value) {
    $el.GetCurrentPattern([System.Windows.Automation.ValuePattern]::Pattern).SetValue($value)
}
function Ensure-On([object]$el) {
    try {
        $tg = $el.GetCurrentPattern([System.Windows.Automation.TogglePattern]::Pattern)
        if ($tg.Current.ToggleState -ne 'On') { $tg.Toggle() }
    } catch { }
}

$proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } |
        Sort-Object StartTime -Descending | Select-Object -First 1
if ($proc -eq $null) { Fail 'ugr-tool' 'no-window-process' }
$root = [System.Windows.Automation.AutomationElement]::RootElement
$pc = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ProcessIdProperty, $proc.Id)
$main = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $pc)
if ($main -eq $null) { Fail 'ugr-tool' 'main-window-not-found' }

# Re-acquire the foreground window right before any click (2026-10-08 lesson:
# a probe click once landed in a remote-desktop window instead of DIALux).
$hMain = [IntPtr]$proc.MainWindowHandle
$hFg = [UG.U]::GetForegroundWindow()
$tidFg = 0
if ($hFg -ne [IntPtr]::Zero) { [void][UG.U]::GetWindowThreadProcessId($hFg, [ref]$tidFg) }
$tidMe = [UG.U]::GetCurrentThreadId()
$attached = $false
if ($tidFg -ne 0 -and $tidFg -ne $tidMe) {
    $attached = [UG.U]::AttachThreadInput($tidMe, $tidFg, $true)
}
[void][UG.U]::SetForegroundWindow($hMain)
if ($attached) { [void][UG.U]::AttachThreadInput($tidMe, $tidFg, $false) }
Start-Sleep -Milliseconds 500

# ------------------------------------------------------- 1) calculation tool
if ((ById 'aid_NewPointCalculationObject' 1200) -eq $null) {
    $construction = ById 'MenuGotoConstructionMode' 6000
    if ($construction -eq $null) { Fail 'ugr-tool' 'construction-menu-missing' }
    try { $construction.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Collapse() } catch { }
    Start-Sleep -Milliseconds 300
    $construction.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern).Expand()
    Start-Sleep -Milliseconds 800
    $tool = ById 'MenuGotoShowCalculationObjectTool' 6000
    if ($tool -eq $null) { Fail 'ugr-tool' 'calculation-object-menu-item-missing' }
    $tool.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
    Start-Sleep -Milliseconds 1500
}
if ((ById 'aid_NewPointCalculationObject' 2000) -eq $null) {
    Fail 'ugr-tool' 'calculation-object-tool-not-active'
}
Emit 'ugr-tool' 'ok'

# ------------------------------------------------------- 2) calculation point
$haveCoords = ($PointX -ne '' -and $PointY -ne '' -and $PointZ -ne '')
if ($haveCoords) {
    $newPoint = ById 'aid_NewPointCalculationObject' 3000
    if ($newPoint -eq $null) { Fail 'ugr-point' 'point-tool-missing' }
    $render = ById '_renderHost' 2000
    if ($render -eq $null) { Fail 'ugr-point' 'render-host-missing' }
    try {
        $newPoint.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
        Start-Sleep -Milliseconds 300
        ClickCenter $render
        Start-Sleep -Milliseconds 1200
    } catch {
        Fail 'ugr-point' 'point-create-failed'
    }
    # Drawing the point only creates/selects it; exact world coordinates are
    # written through the numeric fields that appear afterwards.
    $xEl = ById 'PositionVectorControl_X' 3000
    $yEl = ById 'PositionVectorControl_Y' 3000
    $zEl = ById 'PositionVectorControl_Z' 3000
    if ($xEl -eq $null -or $yEl -eq $null -or $zEl -eq $null) {
        Fail 'ugr-point' 'position-controls-missing-after-point'
    }
    try {
        Set-Val $xEl $PointX
        Set-Val $yEl $PointY
        Set-Val $zEl $PointZ
        Start-Sleep -Milliseconds 800
    } catch {
        Fail 'ugr-point' 'position-set-failed'
    }
    Emit 'ugr-point' 'ok' ("new x={0} y={1} z={2}" -f $PointX, $PointY, $PointZ)
} else {
    # No coordinates: reuse the calculation point already in the project. The
    # caller is responsible for it being selected; we only verify that the
    # point-tool context is live.
    Emit 'ugr-point' 'ok' 'existing'
}

# ------------------------------------------------------- 3) UGR metric
$ugr = $null
if ($UgrCheckId -ne '') {
    $ugr = ById $UgrCheckId 4000
    if ($ugr -eq $null) { Fail 'ugr-metric' 'ugr-check-id-not-found' }
} else {
    # UGR is ASCII, so a name scan is safe even though the UI is localised.
    $ugr = Find-Pattern 'UGR|Ugr' 4000
    if ($ugr -eq $null) {
        foreach ($cand in @('UgrCheckBox', 'CheckBoxUGR', 'CalculationParameterUGR', 'UGR')) {
            $ugr = ById $cand 1200
            if ($ugr -ne $null) { break }
        }
    }
}
if ($ugr -eq $null) {
    Fail 'ugr-metric' 'ugr-checkbox-not-found-use-UgrCheckId'
}
Ensure-On $ugr
Start-Sleep -Milliseconds 800
Emit 'ugr-metric' 'ok'

# ------------------------------------------------------- 4) step + range
# Default path = measured ids first (2026-10-19: the Chinese UI never matches
# the English patterns below, so pattern-only search cost us two real runs),
# then the historical name scan as a second chance.
$stepEl = $null
if ($StepId -ne '') { $stepEl = ById $StepId 4000 }
else {
    foreach ($cand in @('StepSize_Ugr', 'StepSize', 'StepDeg', 'UgrStep', 'SpacingStep')) {
        $stepEl = ById $cand 600
        if ($stepEl -ne $null) { break }
    }
    if ($stepEl -eq $null) { $stepEl = Find-Pattern 'StepSize|StepDeg|UgrStep|SpacingStep' 3000 }
}
$fromEl = $null
if ($RangeFromId -ne '') { $fromEl = ById $RangeFromId 4000 }
else {
    foreach ($cand in @('AngleRangeBegin_Ugr', 'ViewingAngleFrom', 'ViewRangeFrom', 'AngleFrom')) {
        $fromEl = ById $cand 600
        if ($fromEl -ne $null) { break }
    }
    if ($fromEl -eq $null) { $fromEl = Find-Pattern 'ViewingAngleFrom|ViewRangeFrom|AngleFrom' 3000 }
}
$toEl = $null
if ($RangeToId -ne '') { $toEl = ById $RangeToId 4000 }
else {
    foreach ($cand in @('AngleRangeEnd_Ugr', 'ViewingAngleTo', 'ViewRangeTo', 'AngleTo')) {
        $toEl = ById $cand 600
        if ($toEl -ne $null) { break }
    }
    if ($toEl -eq $null) { $toEl = Find-Pattern 'ViewingAngleTo|ViewRangeTo|AngleTo' 3000 }
}

if ($stepEl -eq $null -or $fromEl -eq $null -or $toEl -eq $null) {
    # Do not silently run with DIALux defaults when the caller asked for a
    # specific grid: that would report numbers for parameters we never set.
    Fail 'ugr-params' 'ugr-param-controls-not-found-use-StepId-RangeFromId-RangeToId'
}
try {
    Set-Val $stepEl ([string]$StepDeg)
    Set-Val $fromEl ([string]$RangeFromDeg)
    Set-Val $toEl ([string]$RangeToDeg)
    Start-Sleep -Milliseconds 1000
} catch {
    Fail 'ugr-params' 'ugr-param-set-failed'
}
Emit 'ugr-params' 'ok' ("step={0} from={1} to={2}" -f $StepDeg, $RangeFromDeg, $RangeToDeg)

# ------------------------------------------------------- 5) calculation
# Best-effort read of the result panel text; used as the completion FALLBACK
# signal and for diagnostics. Two timeouts: long for snapshots, short when
# polled inside the wait loop.
function Read-UgrResultText([string]$resultId, [int]$ms) {
    if ($resultId -ne '') {
        $el = ById $resultId $ms
        if ($el -ne $null) { try { return $el.Current.Name } catch { } }
        return ''
    }
    $chunks = @()
    foreach ($cand in @('ResultsMonitorList', 'ResultsMonitorSurfaceResultAverage', 'ResultsMonitorSurfaceUniformityAverage')) {
        $el = ById $cand $ms
        if ($el -eq $null) { continue }
        try {
            $items = $el.FindAll([System.Windows.Automation.TreeScope]::Descendants,
                                 [System.Windows.Automation.Condition]::TrueCondition)
            for ($i = 0; $i -lt $items.Count; $i++) {
                $nm = ''
                try { $nm = $items.Item($i).Current.Name } catch { }
                if ($nm -ne '') { $chunks += $nm }
            }
        } catch { }
    }
    return ($chunks -join ' | ')
}

$calc = $null
if ($CalcButtonId -ne '') { $calc = ById $CalcButtonId 5000 }
if ($calc -eq $null) { $calc = ById 'CalculationButtonStart' 5000 }
if ($calc -eq $null) { Fail 'ugr-calc' 'calculation-button-missing-use-CalcButtonId' }
$before = ''
try { $before = $calc.Current.Name } catch { }
# Result panel BEFORE we click: baseline for the fallback comparison.
$resBefore = Read-UgrResultText $ResultId 800
try {
    $calc.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
} catch {
    Fail 'ugr-calc' 'calculation-invoke-failed'
}
# Completion: PRIMARY = CalculationCommandText reverts to its pre-click label
# (the CALCULATING -> IDLE edge calc_watch_trigger / UiState uses).
# FALLBACK (added 2026-10-19, real machine): on evo 14.0 the label NEVER
# flipped although the calculation had finished in ~45-60 s, so a label-only
# wait burned the whole 300 s budget and failed with 'calculation-timeout'.
# The result panel text changing (empty -> value counts) is observable in the
# same runs, so poll BOTH and only declare done when at least one fired;
# a 10 s floor keeps a late panel render from firing instantly.
$sw = [Diagnostics.Stopwatch]::StartNew()
$busySeen = $false
$done = $false
$via = ''
$resNow = ''
while ($sw.ElapsedMilliseconds -lt $CalcTimeoutMs) {
    # (A) label edge -- never skip the rest when the label element is absent
    #     (the old code 'continue'd here and could never see any other signal).
    $cur = ById 'CalculationCommandText' 1500
    if ($cur -ne $null) {
        $name = ''
        try { $name = $cur.Current.Name } catch { }
        if ($name -ne $before) { $busySeen = $true }
        elseif ($busySeen) { $done = $true; $via = 'label'; break }
    }
    # (B) result panel changed
    $resNow = Read-UgrResultText $ResultId 120
    if ($resNow -ne '' -and $resNow -ne $resBefore -and $sw.Elapsed.TotalSeconds -ge 10) {
        $done = $true; $via = 'result'; break
    }
    Start-Sleep -Milliseconds 1000
}
if (-not $done) {
    $b = ($resBefore -replace '\s+', ' '); if ($b.Length -gt 120) { $b = $b.Substring(0, 120) }
    $a = ($resNow -replace '\s+', ' '); if ($a.Length -gt 120) { $a = $a.Substring(0, 120) }
    Fail 'ugr-calc' ("calculation-timeout via=none res_before='{0}' res_after='{1}'" -f $b, $a)
}
Start-Sleep -Milliseconds 1500
Emit 'ugr-calc' 'ok' ("sec={0} via={1}" -f [int]($sw.Elapsed.TotalSeconds), $via)

# ------------------------------------------------------- 6) read result
$chunks = @()
if ($ResultId -ne '') {
    $res = ById $ResultId 4000
    if ($res -ne $null) {
        try { $chunks += $res.Current.Name } catch { }
    }
} else {
    foreach ($cand in @('ResultsMonitorList', 'ResultsMonitorSurfaceResultAverage', 'ResultsMonitorSurfaceUniformityAverage')) {
        $el = ById $cand 1500
        if ($el -eq $null) { continue }
        try {
            $items = $el.FindAll([System.Windows.Automation.TreeScope]::Descendants,
                                 [System.Windows.Automation.Condition]::TrueCondition)
            for ($i = 0; $i -lt $items.Count; $i++) {
                $nm = ''
                try { $nm = $items.Item($i).Current.Name } catch { }
                if ($nm -ne '') { $chunks += $nm }
            }
        } catch { }
    }
}
if ($chunks.Count -eq 0) {
    # Last resort: any element whose name carries the UGR token.
    $any = Find-Pattern 'UGR|RUG' 3000
    if ($any -ne $null) {
        try { $chunks += $any.Current.Name } catch { }
    }
}
if ($chunks.Count -eq 0) { Fail 'ugr-read' 'ugr-result-not-found' }
$raw = ($chunks -join ' | ')
Emit 'ugr-read' 'ok' ("text=" + (Esc $raw) + (" target={0} step={1} from={2} to={3}" -f $Target, $StepDeg, $RangeFromDeg, $RangeToDeg))
Emit 'ugr-done' 'ok'
exit 0
