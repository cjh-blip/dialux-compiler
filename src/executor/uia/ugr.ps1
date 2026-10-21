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

# Joined UIA names of a dialog (report.ps1's proven classifier). Returned raw
# for in-memory matching; callers Esc() before printing so this ASCII file
# never carries CJK.
function Get-DlgUiText([IntPtr]$h) {
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

# The DIALux confirm raised when fresh results are about to be invalidated.
# 2026-10-20 second gun (4b): it sat between the place-Invoke and the viewport
# click and swallowed the click whole (the reason 4b/4c never got
# PositionVectorControl). The message is Chinese; the fingerprint is built
# from char codes at runtime ('results will be invalid'), so this file stays
# pure ASCII. A visible DIALux #32770 that is NOT that confirm fails with its
# escaped text -- no guessing which dialog to click.
function Find-ResultInvalidModal([int]$timeout) {
    $fp = -join ([char[]]@(0x7ED3, 0x679C, 0x5C06, 0x65E0, 0x6548))
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($sw.ElapsedMilliseconds -lt $timeout) {
        $h = [IntPtr]::Zero
        while ($true) {
            $h = [UG.U]::FindWindowEx([IntPtr]::Zero, $h, '#32770', [NullString]::Value)
            if ($h -eq [IntPtr]::Zero) { break }
            $wpid = 0
            [void][UG.U]::GetWindowThreadProcessId($h, [ref]$wpid)
            if ($wpid -ne $proc.Id) { continue }
            if (-not [UG.U]::IsWindowVisible($h)) { continue }
            $txt = Get-DlgUiText $h
            if ($txt.IndexOf($fp) -ge 0) { return $h }
            $snip = ($txt -replace '\s+', ' ')
            if ($snip.Length -gt 120) { $snip = $snip.Substring(0, 120) }
            Fail 'ugr-point' ("unexpected-modal ui='{0}'" -f (Esc $snip))
        }
        Start-Sleep -Milliseconds 150
    }
    return [IntPtr]::Zero
}
# Returns 'none' or 'confirmed'; fails with scene on an unknown modal.
function Confirm-ResultInvalidModal([int]$timeout) {
    $h = Find-ResultInvalidModal $timeout
    if ($h -eq [IntPtr]::Zero) { return 'none' }
    $yes = [UG.U]::GetDlgItem($h, 6)   # IDYES of a standard confirm box
    if ($yes -eq [IntPtr]::Zero) { Fail 'ugr-point' 'result-invalid-modal-yes-missing' }
    [void][UG.U]::SendMessage($yes, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)   # BM_CLICK
    Start-Sleep -Milliseconds 600
    # If it is still up we did not really dismiss it -- say so instead of
    # letting the next click vanish into the modal again (4b verbatim).
    if ((Find-ResultInvalidModal 600) -ne [IntPtr]::Zero) { Fail 'ugr-point' 'result-invalid-modal-not-dismissed' }
    return 'confirmed'
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
    # ---- layer 1: bottom-bar object type must be POINT before placing.
    # 2026-10-20 second-gun receipt (4b/4c, three-layer evidence):
    # aid_NewPointCalculationObject is a GENERIC 'place calculation element'
    # button (rect 81,218 286x34) -- with the bar still on SURFACE every
    # Invoke+click created a calculation SURFACE and PositionVectorControl
    # never appeared. The bar's camera/point/surface entries are ListItems
    # with SelectionItemPattern; the type lives in THAT layer. Measured
    # manual sequence (4d): select bottom-bar point -> place -> click.
    # The item name is Chinese -> built from char codes at runtime so the
    # file stays pure ASCII.
    $ptName = -join ([char[]]@(0x8BA1, 0x7B97, 0x70B9))   # 'calculation point'
    $liCond = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::ListItem)
    $barItems = $main.FindAll([System.Windows.Automation.TreeScope]::Descendants, $liCond)
    $ptItem = $null
    $barCand = @()
    for ($i = 0; $i -lt $barItems.Count; $i++) {
        $li = $barItems.Item($i)
        $selPat = $null
        try { $selPat = $li.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern) } catch { }
        if ($selPat -eq $null) { continue }
        $nm = ''
        try { $nm = [string]$li.Current.Name } catch { }
        if ($nm.IndexOf($ptName) -ge 0) { $ptItem = $li; break }
        if ($nm -ne '') { $barCand += $nm }
    }
    if ($ptItem -eq $null) {
        # not found = scene with the candidate names attached, so the next
        # real-machine round can pin the right item instead of guessing.
        $cand = ($barCand | Select-Object -First 12) -join ' ; '
        Fail 'ugr-point' ("bottombar-point-item-not-found candidates='{0}'" -f (Esc $cand))
    }
    try {
        $ptItem.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Select()
    } catch {
        Fail 'ugr-point' 'bottombar-point-select-failed'
    }
    # Select() claiming ok is exactly the item5 report-mode trap; confirm the
    # item really carries the selection before anything gets clicked.
    $typeOk = $false
    $swT = [Diagnostics.Stopwatch]::StartNew()
    while ($swT.ElapsedMilliseconds -lt 1500) {
        $isSel = $false
        try { $isSel = $ptItem.Current.IsSelected } catch { }
        if ($isSel) { $typeOk = $true; break }
        Start-Sleep -Milliseconds 200
    }
    if (-not $typeOk) {
        $nmMatched = ''
        try { $nmMatched = [string]$ptItem.Current.Name } catch { }
        Fail 'ugr-point' ("bottombar-point-not-selected name='{0}'" -f (Esc $nmMatched))
    }

    $newPoint = ById 'aid_NewPointCalculationObject' 3000
    if ($newPoint -eq $null) { Fail 'ugr-point' 'point-tool-missing' }
    $render = ById '_renderHost' 2000
    if ($render -eq $null) { Fail 'ugr-point' 'render-host-missing' }
    try {
        $newPoint.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
        Start-Sleep -Milliseconds 300
    } catch {
        Fail 'ugr-point' 'point-create-failed'
    }
    # ---- layer 2: the results-invalid confirm can raise right here (4b had
    # fresh results from the run before) and swallow the viewport click.
    $modalVia = Confirm-ResultInvalidModal 2500
    try {
        ClickCenter $render
        Start-Sleep -Milliseconds 1200
    } catch {
        Fail 'ugr-point' 'point-create-failed'
    }
    # ...and it can also raise off the click itself; bounded check, then move
    # on -- the position-fields gate below still reports a swallowed click.
    if ((Confirm-ResultInvalidModal 1500) -eq 'confirmed') { $modalVia = 'confirmed-after-click' }
    # ---- layer 4: the property panel's position section is COLLAPSED by
    # default (second cause in 4b/4c) and the PositionVectorControl fields
    # only enter the tree once it is expanded. Section name is Chinese ->
    # char codes at runtime. Best effort: if it never expands, the
    # position-controls gate below still fails with its own scene.
    $locName = -join ([char[]]@(0x5B9A, 0x4F4D))   # 'position'
    $allEls = $main.FindAll([System.Windows.Automation.TreeScope]::Descendants,
                            [System.Windows.Automation.Condition]::TrueCondition)
    for ($i = 0; $i -lt $allEls.Count; $i++) {
        $sec = $allEls.Item($i)
        $nm = ''
        try { $nm = [string]$sec.Current.Name } catch { }
        if ($nm.IndexOf($locName) -lt 0) { continue }
        $ecp = $null
        try { $ecp = $sec.GetCurrentPattern([System.Windows.Automation.ExpandCollapsePattern]::Pattern) } catch { }
        if ($ecp -eq $null) { continue }
        try { $ecp.Expand(); Start-Sleep -Milliseconds 400 } catch { }
        break
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
    Emit 'ugr-point' 'ok' ("new x={0} y={1} z={2} type=bottombar-point modal={3}" -f $PointX, $PointY, $PointZ, $modalVia)
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
# 2026-10-20 review round: on the real machine this button came back
# enabled=False / name='' and the Invoke threw ('calculation-invoke-failed')
# on a scene with NO calculation point and the calculation SURFACE selected,
# while the toolbar play button still LOOKED green (UIA vs pixels disagree --
# logged as measured). Guard BEFORE Invoke so the failure is words rather than
# a raw invoke exception. Whether DIALux disables calculation when the scene
# carries no calculation point is a SCENE/SEQUENCE question (the E checklist
# has no 'place calculation point' step) -- NOT judged a code defect here;
# pending the next real-machine round.
$calcEnabled = $true
try { $calcEnabled = $calc.Current.IsEnabled } catch { }
if (-not $calcEnabled) { Fail 'ugr-calc' 'calc-button-disabled scene-may-lack-calculation-point' }
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
# 2026-10-20 second-gun receipt (4d, via=result at sec=12): on a RECALC the
# panel is CLEARED to '-' first -- work-plane row included -- and the numbers
# fill in only afterwards, so with res_before carrying values the old
# 'anything changed' rule fired on the CLEAR itself and the action returned
# reading all '-' while the calculation was still running (4a's first run had
# res_before empty and never saw a clear, which is why 56 s was honest).
# Gate now:
#   * valueless read = rows present but no digit adjacent to the measured
#     'lx' cell (a transient EMPTY read does NOT count as a clear);
#   * a baseline WITH values only completes after dashSeen -> a value really
#     emerged from '-'; identical final numbers are allowed (a recalc can
#     reproduce them exactly);
#   * a baseline without values keeps the old change rule.
$hadValue = ($resBefore -match '\d+(?:\.\d+)?\s*lx')
$dashSeen = $false
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
    # (B) result panel -- gate per the comment above; the 10 s floor stays.
    $resNow = Read-UgrResultText $ResultId 120
    if ($resNow -ne '') {
        $nowHasValue = ($resNow -match '\d+(?:\.\d+)?\s*lx')
        if (-not $nowHasValue) {
            $dashSeen = $true
        } elseif ($sw.Elapsed.TotalSeconds -ge 10) {
            if ($hadValue) {
                if ($dashSeen) { $done = $true; $via = 'result'; break }
            } elseif ($resNow -ne $resBefore) {
                $done = $true; $via = 'result'; break
            }
        }
    }
    Start-Sleep -Milliseconds 1000
}
if (-not $done) {
    $b = ($resBefore -replace '\s+', ' '); if ($b.Length -gt 120) { $b = $b.Substring(0, 120) }
    $a = ($resNow -replace '\s+', ' '); if ($a.Length -gt 120) { $a = $a.Substring(0, 120) }
    $ds = 0; if ($dashSeen) { $ds = 1 }
    Fail 'ugr-calc' ("calculation-timeout via=none dash_seen={2} res_before='{0}' res_after='{1}'" -f $b, $a, $ds)
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
