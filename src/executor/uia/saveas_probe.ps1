## saveas_probe.ps1 -- READ-ONLY property dump of the DIALux report toolbar.
##
## WHY: the ninth-shot screenshot shows a "save as..." button next to Print
## on the report toolbar, and the tenth shot proved PrintDlgEx itself can
## crash the app (two AVs, WER buckets). A direct save route exists as a
## CANDIDATE -- switching to it is a coordinator-level, decision-carded call.
## This script only COLLECTS material: one read-only dump of every button
## around the measured ButtonPrintDocument anchor, so the coordinators can
## judge the candidate without another shot. It never clicks, never calls a
## pattern, never moves the mouse -- tests/test_e2_ps1_contracts.py enforces each
## absence as a negative assertion.
##
## Run (report page must be open; do NOT trigger Print first -- the print
## dialog is the crash source):
##   powershell -NoProfile -ExecutionPolicy Bypass -File saveas_probe.ps1 > probe_out.txt
## Output is UTF-8 (button Names are localized Chinese on this machine).
##
## ASCII ONLY (PS 5.1 reads a non-ASCII .ps1 as GBK and dies on braces).
param(
    [string]$ProcessName = 'DIALux_x64'
)
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { }

function Dump-Buttons([System.Windows.Automation.AutomationElement]$scope, [string]$label) {
    # Read-only: FindAll + Current properties + pattern REFERENCE checks.
    # Reading that a pattern exists is not calling it -- no pattern call here.
    $cond = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::Button)
    $all = $null
    try { $all = $scope.FindAll([System.Windows.Automation.TreeScope]::Descendants, $cond) } catch { }
    if ($all -eq $null) {
        [Console]::Out.WriteLine(("SCOPE {0} buttons=unreadable" -f $label))
        return 0
    }
    $n = $all.Count
    $shown = $n
    if ($n -gt 60) { $shown = 60 }
    [Console]::Out.WriteLine(("SCOPE {0} buttons={1} shown={2}" -f $label, $n, $shown))
    for ($i = 0; $i -lt $shown; $i++) {
        $e = $all.Item($i)
        $nm = '?'
        $aid = '?'
        $ct = '?'
        $rt = 'na'
        $inv = 0
        $sel = 0
        $ena = '?'
        try { $nm = [string]$e.Current.Name } catch { }
        try { $aid = [string]$e.Current.AutomationId } catch { }
        try { $ct = [string]$e.Current.ControlType.ProgrammaticName } catch { }
        try {
            $r = $e.Current.BoundingRectangle
            $rt = ('{0},{1},{2},{3}' -f [int]$r.X, [int]$r.Y, [int]$r.Width, [int]$r.Height)
        } catch { }
        try {
            $p = $e.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
            if ($p -ne $null) { $inv = 1 }
        } catch { }
        try {
            $p2 = $e.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern)
            if ($p2 -ne $null) { $sel = 1 }
        } catch { }
        try { if ($e.Current.IsEnabled) { $ena = '1' } else { $ena = '0' } } catch { }
        [Console]::Out.WriteLine(("BTN name='{0}' aid='{1}' rect={2} ct={3} invoke={4} sel={5} enabled={6}" -f $nm, $aid, $rt, $ct, $inv, $sel, $ena))
    }
    return $shown
}

$proc = Get-Process -Name $ProcessName -ErrorAction SilentlyContinue |
        Where-Object { $_.MainWindowHandle -ne 0 } |
        Sort-Object StartTime -Descending | Select-Object -First 1
if ($proc -eq $null) {
    [Console]::Out.WriteLine('PROBE saveas-toolbar ro=1 result=no-process')
    exit 0
}
$root = [System.Windows.Automation.AutomationElement]::RootElement
$pc = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::ProcessIdProperty, $proc.Id)
$main = $root.FindFirst([System.Windows.Automation.TreeScope]::Children, $pc)
if ($main -eq $null) {
    [Console]::Out.WriteLine('PROBE saveas-toolbar ro=1 result=no-uia-main')
    exit 0
}
[Console]::Out.WriteLine(('PROBE saveas-toolbar ro=1 pid={0}' -f $proc.Id))

# The anchor is the measured report-toolbar Print button (E2 id); dump its
# toolbar scope around it. Nothing is triggered on the way there.
$anchor = $null
$c = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::AutomationIdProperty, 'ButtonPrintDocument')
$sw = [Diagnostics.Stopwatch]::StartNew()
while ($sw.ElapsedMilliseconds -lt 2000 -and $anchor -eq $null) {
    $anchor = $main.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $c)
    if ($anchor -eq $null) { Start-Sleep -Milliseconds 200 }
}
if ($anchor -eq $null) {
    [Console]::Out.WriteLine('ANCHOR aid=ButtonPrintDocument not-found -- report page not open? nothing clicked')
    [void](Dump-Buttons $main 'window-fallback')
    exit 0
}
$ar = $anchor.Current.BoundingRectangle
[Console]::Out.WriteLine(('ANCHOR aid=ButtonPrintDocument rect={0},{1},{2},{3}' -f [int]$ar.X, [int]$ar.Y, [int]$ar.Width, [int]$ar.Height))

$walker = [System.Windows.Automation.TreeWalker]::RawViewWalker
$parent = $null
try { $parent = $walker.GetParent($anchor) } catch { }
$shown = 0
if ($parent -ne $null) {
    $shown = Dump-Buttons $parent 'toolbar-parent'
}
if ($shown -lt 2) {
    # The parent may wrap only the anchor itself -- walk one level up once,
    # and fall back to the whole window when even that yields nothing.
    $gp = $null
    try { if ($parent -ne $null) { $gp = $walker.GetParent($parent) } } catch { }
    if ($gp -ne $null -and -not $gp.Equals($main)) {
        [Console]::Out.WriteLine('SCOPE parent-too-narrow up-one')
        [void](Dump-Buttons $gp 'toolbar-grandparent')
    } elseif ($shown -eq 0) {
        [void](Dump-Buttons $main 'window-fallback')
    }
}
exit 0
