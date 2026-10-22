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
    [string]$SaveButtonId = '',
    [string]$BreadCrumbPath = ''   # 13th batch: breadcrumb file for ARMED/STAGE/HEART/FACE (empty = %TEMP% default)
)
$ErrorActionPreference = 'Continue'
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName WindowsBase    # System.Windows.Point for ElementFromPoint scan (eighth batch)

# Tenth batch -- encoding layer only, no field semantics touched. PS 5.1
# writes redirected stdout with the machine OEM code page (zh-CN = GBK) while
# python read it as UTF-8 + errors=replace, which turned the ninth shot's ui=
# Chinese scene into U+FFFD on the pipe. Declare this process's output
# encoding as UTF-8 so both ends agree; the python side additionally reads
# GBK bytes, so the scene survives either way (asserted in
# tests/test_report_pipe_encoding.py). Best effort: if the host refuses the
# change (no console), the decoder fallback still covers the real machine.
try { [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false) } catch { }

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
    // ---- tenth batch (9th shot 2026-10-22): Win32 printer-list channel. The
    // ---- print dialog's UIA FolderView pane reports ZERO named children (two
    // ---- samples 6s apart), so classification and selection move to window
    // ---- messages; E2 (2026-10-19) read this dialog's list via Win32.
    public delegate bool EnumProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumChildWindows(IntPtr p, EnumProc cb, IntPtr l);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassNameW(IntPtr h, StringBuilder s, int max);
    [DllImport("user32.dll")] public static extern int GetDlgCtrlID(IntPtr h);
    [DllImport("user32.dll")] public static extern IntPtr GetParent(IntPtr h);
    [StructLayout(LayoutKind.Sequential)] public struct PT { public int X; public int Y; }
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct LVITEMW {
      public int mask; public int iItem; public int iSubItem;
      public uint state; public uint stateMask;
      public IntPtr pszText; public int cchTextMax; public int iImage; public IntPtr lParam;
    }
    [DllImport("user32.dll")] public static extern bool ClientToScreen(IntPtr h, ref PT p);
    [DllImport("winspool.drv", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool GetDefaultPrinterW(StringBuilder s, ref int n);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L; public int T; public int R; public int B; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern IntPtr SendMessageTimeout(IntPtr h, int m, UIntPtr w, IntPtr l, uint flags, uint timeout, out UIntPtr result);

    // Read-side messages must not hang on a dying or hung dialog (tenth shot:
    // PrintDlgEx self-crashed mid-read, 49s tail never located). 3s,
    // SMTO_ABORTIFHUNG; a timeout/hung target reads back as 0 -- an honest
    // empty string, never a stuck runner. ACTION messages (BM_CLICK) keep
    // plain SendMessage so click behavior stays byte-identical.
    public static IntPtr SafeSend(IntPtr h, int m, IntPtr w, IntPtr l) {
      UIntPtr res;
      IntPtr ok = SendMessageTimeout(h, m, (UIntPtr)w, l, 0x0002 /*SMTO_ABORTIFHUNG*/, 3000, out res);
      if (ok == IntPtr.Zero) return IntPtr.Zero;
      return (IntPtr)((long)res);
    }

    // ---- twelfth batch: step watchdog (L2) + stage marks. The eleventh shot
    // ---- hung report-printer 2/2 with NO step line at all -- the 600s shell
    // ---- watchdog killed the process before any code face existed. Arm at
    // ---- step entry, disarm before each ok; if the main thread is stuck at
    // ---- ANY point (UIA call, foreground input, pipe -- root cause not
    // ---- assumed), a pure-.NET timer thread writes the fail line straight to
    // ---- stdout and force-exits. The callback runs NO PowerShell code (not
    // ---- legal off the pipeline thread): Console write + Environment.Exit
    // ---- only, both .NET. Field names mirror the L1 timeout code so the
    // ---- two faces are indistinguishable in the log.
    // ---- Thirteenth batch, from the twelfth shot (all three inner timeouts
    // ---- silent 4/4): the timer callback alone could not testify WHY it did
    // ---- not fire, so every transition now ALSO appends to a breadcrumb file
    // ---- that needs no stdout channel: ARMED/STAGE/HEART/TARGET/DISARMED/
    // ---- FACE, each with an epoch-ms stamp. The timer became a 5s heartbeat
    // ---- that only writes the code face once the budget is spent -- the face
    // ---- goes to the FILE FIRST, then stdout, then the process exits; a
    // ---- blocked Console can no longer swallow it. External readers judge
    // ---- liveness from STAGE lines (written by the main thread), which is
    // ---- the only channel that stops when the main thread stops.
    public static string LastStage = "printer-start";
    private static System.Threading.Timer wTimer;
    private static int wStartTick;
    private static IntPtr wTarget;
    private static string wStep = "report-printer";
    private static string wCrumb = "";
    private static long NowMs() {
      return (long)(DateTime.UtcNow - new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc)).TotalMilliseconds;
    }
    private static void Crumb(string line) {
      if (wCrumb == null || wCrumb.Length == 0) return;
      try { System.IO.File.AppendAllText(wCrumb, line + "\n"); } catch { }
    }
    public static void WSetCrumb(string path) { wCrumb = path == null ? "" : path; }
    public static void WMark(string stage) {
      LastStage = stage;
      Crumb("STAGE " + NowMs() + " stage=" + stage);
    }
    public static void WTarget(IntPtr h) {
      wTarget = h;
      Crumb("TARGET " + NowMs() + " target=0x" + h.ToInt64().ToString("x"));
    }
    public static void WArm(int budgetMs, string stepName) {
      wStartTick = Environment.TickCount;
      wStep = stepName;
      Crumb("ARMED " + NowMs() + " budget=" + budgetMs + " step=" + stepName);
      if (wTimer != null) { wTimer.Dispose(); wTimer = null; }
      // 5s-period heartbeat; the budget check lives INSIDE the callback, so a
      // silenced stdout face still leaves FACE in the file before exit.
      wTimer = new System.Threading.Timer(delegate(object s) {
        long elapsed = (long)(uint)Environment.TickCount - (long)(uint)wStartTick;
        Crumb("HEART " + NowMs() + " stage=" + LastStage + " elapsed=" + elapsed);
        if (elapsed < budgetMs) return;
        string fg = "?";
        try {
          IntPtr fh = GetForegroundWindow();
          int fpid = 0;
          GetWindowThreadProcessId(fh, ref fpid);
          System.Text.StringBuilder tb = new System.Text.StringBuilder(96);
          GetWindowText(fh, tb, 96);
          string title = tb.ToString().Replace('\r', ' ').Replace('\n', ' ');
          if (title.Length > 40) title = title.Substring(0, 40);
          fg = fpid + ":" + title;
        } catch { }
        string face = "STEP " + wStep + " fail printer-step-hang-timeout stage=watchdog last="
          + LastStage + " elapsed=" + elapsed + " fg='" + fg + "' target=0x"
          + wTarget.ToInt64().ToString("x") + " budget=" + budgetMs;
        Crumb("FACE " + NowMs() + " " + face);
        try {
          Console.WriteLine(face);
          Console.Out.Flush();
        } catch { }
        Environment.Exit(1);
      }, null, 5000, 5000);
    }
    public static void WDisarm() {
      Crumb("DISARMED " + NowMs() + " stage=" + LastStage);
      if (wTimer != null) { wTimer.Dispose(); wTimer = null; }
    }

    // "hwnd|class|text|l,t,r,b" per child (recursive): the scene that travels
    // back in failures; the rect lets the caption-anchored container pick
    // prove itself geometrically instead of by class name.
    public static string[] ChildScene(IntPtr p) {
      System.Collections.Generic.List<string> rows = new System.Collections.Generic.List<string>();
      EnumChildWindows(p, delegate(IntPtr h, IntPtr l) {
        StringBuilder cls = new StringBuilder(256);
        GetClassNameW(h, cls, 256);
        StringBuilder txt = new StringBuilder(512);
        GetWindowText(h, txt, 512);
        rows.Add(((long)h).ToString() + "|" + cls.ToString() + "|" + txt.ToString() + "|" + RectStr(h));
        return true;
      }, IntPtr.Zero);
      return rows.ToArray();
    }
    private static string RectStr(IntPtr h) {
      RECT r;
      if (!GetWindowRect(h, out r)) return "-1,-1,-1,-1";
      return r.L + "," + r.T + "," + r.R + "," + r.B;
    }
    // Read-only default-printer query (winspool). This query is the whole
    // allowance: never a system-setting write -- the printer is chosen
    // in-dialog only, per the boundary from the task order.
    public static string GetDefaultPrinterName() {
      StringBuilder sb = new StringBuilder(256);
      int n = 256;
      if (GetDefaultPrinterW(sb, ref n)) return sb.ToString();
      if (n <= 256) return "";
      StringBuilder big = new StringBuilder(n + 1);
      return GetDefaultPrinterW(big, ref n) ? big.ToString() : "";
    }
    public static string DlgItemText(IntPtr h, int id) {
      IntPtr c = GetDlgItem(h, id);
      if (c == IntPtr.Zero) return "";
      StringBuilder sb = new StringBuilder(256);
      GetWindowText(c, sb, 256);
      return sb.ToString();
    }
    // List channel of one candidate control: ComboBox / ListBox /
    // SysListView32 (a shell FolderView hides its list this way). Unknown
    // messages answer 0, so probing arbitrary children is harmless.
    public static string ListChannel(IntPtr h) {
      if ((long)SafeSend(h, 0x0146, IntPtr.Zero, IntPtr.Zero) > 0) return "cb";   // CB_GETCOUNT
      if ((long)SafeSend(h, 0x018B, IntPtr.Zero, IntPtr.Zero) > 0) return "lb";   // LB_GETCOUNT
      if ((long)SafeSend(h, 0x1004, IntPtr.Zero, IntPtr.Zero) > 0) return "lv";   // LVM_GETITEMCOUNT
      return "";
    }
    // Item text WITH the per-item reply count (eleventh-batch fix: the count
    // said 3 while every text came back empty, so the reply count travels in
    // the probe and 'wrong message' vs 'virtual list answers nothing' is
    // readable from the failure itself). lv: LVM_GETITEMTEXTW with the index
    // in wParam AND in the struct (tenth batch had wParam=0 -- air), then the
    // A variant decoded as cp936; cb/lb: CB_GETLBTEXT/LB_GETTEXT with the
    // same empty-read A fallback.
    private static string ListItemByChannel(IntPtr h, string ch, int i) {
      int rc;
      return ListItemByChannelEx(h, ch, i, out rc);
    }
    private static string ListItemByChannelEx(IntPtr h, string ch, int i, out int rc) {
      rc = 0;
      if (ch == "lv") {
        IntPtr buf = Marshal.AllocHGlobal(1024);
        IntPtr p = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(LVITEMW)));
        try {
          LVITEMW it = new LVITEMW();
          it.mask = 1; it.iItem = i; it.iSubItem = 0;
          it.pszText = buf; it.cchTextMax = 511;
          Marshal.Copy(new byte[1024], 0, buf, 1024);
          Marshal.StructureToPtr(it, p, false);
          rc = (int)(long)SafeSend(h, 0x1073, (IntPtr)i, p);   // LVM_GETITEMTEXTW, wParam = index
          string txtW = Marshal.PtrToStringUni(buf) ?? "";
          if (txtW.Length > 0) return txtW;
          Marshal.Copy(new byte[1024], 0, buf, 1024);
          Marshal.StructureToPtr(it, p, false);
          int rcA = (int)(long)SafeSend(h, 0x102D, (IntPtr)i, p);   // LVM_GETITEMTEXTA
          if (rcA > rc) rc = rcA;
          return AnsiFrom(buf);
        } finally { Marshal.FreeHGlobal(p); Marshal.FreeHGlobal(buf); }
      }
      IntPtr b = Marshal.AllocHGlobal(1024);
      try {
        Marshal.Copy(new byte[1024], 0, b, 1024);
        if (ch == "cb") rc = (int)(long)SafeSend(h, 0x0148, (IntPtr)i, b);  // CB_GETLBTEXT
        else rc = (int)(long)SafeSend(h, 0x0189, (IntPtr)i, b);             // LB_GETTEXT
        string txt = Marshal.PtrToStringUni(b) ?? "";
        if (txt.Length > 0) return txt;
        return AnsiFrom(b);
      } finally { Marshal.FreeHGlobal(b); }
    }
    private static string AnsiFrom(IntPtr buf) {
      byte[] raw = new byte[1024];
      Marshal.Copy(buf, raw, 0, 1024);
      int z = 0;
      while (z < 1024 && raw[z] != 0) z++;
      if (z == 0) return "";
      try { return Encoding.GetEncoding(936).GetString(raw, 0, z); }
      catch { return System.Text.Encoding.ASCII.GetString(raw, 0, z); }
    }
    private static int ListCount(IntPtr h, string ch) {
      int n = 0;
      if (ch == "cb") n = (int)(long)SafeSend(h, 0x0146, IntPtr.Zero, IntPtr.Zero);
      else if (ch == "lb") n = (int)(long)SafeSend(h, 0x018B, IntPtr.Zero, IntPtr.Zero);
      else if (ch == "lv") n = (int)(long)SafeSend(h, 0x1004, IntPtr.Zero, IntPtr.Zero);
      if (n < 0) n = 0;
      return n;
    }
    public static string[] ListRead(IntPtr h, string ch) {
      int n = ListCount(h, ch);
      if (n > 64) n = 64;
      string[] items = new string[n];
      for (int i = 0; i < n; i++) items[i] = ListItemByChannel(h, ch, i);
      return items;
    }
    // One-line forensic for the probe field: channel, count, every item's
    // reply count, first item text -- travels in every printer-list failure.
    public static string ListReadInfo(IntPtr h, string ch) {
      if (ch == null || ch.Length == 0) return "ch=none";
      int n = ListCount(h, ch);
      if (n > 64) n = 64;
      int[] rcs = new int[n];
      string first = "";
      for (int i = 0; i < n; i++) {
        int rc;
        string txt = ListItemByChannelEx(h, ch, i, out rc);
        rcs[i] = rc;
        if (i == 0) first = txt;
      }
      StringBuilder sb = new StringBuilder();
      sb.Append(ch).Append('=').Append(n).Append(" rc=");
      for (int i = 0; i < n; i++) { if (i > 0) sb.Append(','); sb.Append(rcs[i]); }
      if (n == 0) { sb.Append(" first=none"); return sb.ToString(); }
      sb.Append(" first='").Append(first.Length > 30 ? first.Substring(0, 30) : first).Append("'");
      return sb.ToString();
    }
    public static int ListSelIndex(IntPtr h, string ch) {
      if (ch == "cb") return (int)(long)SafeSend(h, 0x0147, IntPtr.Zero, IntPtr.Zero);   // CB_GETCURSEL
      if (ch == "lb") return (int)(long)SafeSend(h, 0x0188, IntPtr.Zero, IntPtr.Zero);   // LB_GETCURSEL
      return (int)(long)SafeSend(h, 0x100C, (IntPtr)(-1), (IntPtr)2);                    // LVM_GETNEXTITEM from -1, LVNI_SELECTED
    }
    public static string ListSelText(IntPtr h, string ch) {
      int i = ListSelIndex(h, ch);
      if (i < 0) return "";
      return ListItemByChannel(h, ch, i);
    }
    // Select by control type -- MESSAGE ONLY (twelfth batch): no foreground,
    // no mouse, no rect. cb/lb: SETCURSEL + the parent's WM_COMMAND
    // notification (dialogs read selection lazily; CBN/LBN_SELCHANGE = 1).
    // lv: LVIS selection-state message; returns 'msg-not-stuck' when the
    // message did not take, which is the .ps1's cue to run the rect-click
    // backup (foreground arranged THERE, never on this path). The read-back
    // gate in the .ps1 is unchanged and still gates the Print click.
    public static string ListSelect(IntPtr h, string ch, int i) {
      if (ch == "cb") {
        SafeSend(h, 0x014E, (IntPtr)i, IntPtr.Zero);            // CB_SETCURSEL
        IntPtr pc = GetParent(h);
        int idc = GetDlgCtrlID(h);
        if (pc != IntPtr.Zero && idc != 0) SafeSend(pc, 0x0111, (IntPtr)((1 << 16) | idc), h);  // CBN_SELCHANGE
        return "set-cur";
      }
      if (ch == "lb") {
        SafeSend(h, 0x0186, (IntPtr)i, IntPtr.Zero);            // LB_SETCURSEL
        IntPtr pl = GetParent(h);
        int idl = GetDlgCtrlID(h);
        if (pl != IntPtr.Zero && idl != 0) SafeSend(pl, 0x0111, (IntPtr)((1 << 16) | idl), h);  // LBN_SELCHANGE
        return "set-cur";
      }
      int cap = Marshal.SizeOf(typeof(LVITEMW));
      IntPtr ps = Marshal.AllocHGlobal(cap);
      try {
        LVITEMW st = new LVITEMW();
        st.mask = 0x0008;   // LVIF_STATE
        st.iItem = i; st.iSubItem = 0;
        st.state = 0x0003; st.stateMask = 0x0003;                  // SELECTED | FOCUSED
        Marshal.StructureToPtr(st, ps, false);
        SafeSend(h, 0x102A, IntPtr.Zero, ps);                      // LVM_SETITEMSTATE
        if (ListSelIndex(h, "lv") == i) return "set-itemstate";
        return "msg-not-stuck";
      } finally { Marshal.FreeHGlobal(ps); }
    }
    // Backup path ONLY (twelfth batch): ensure-visible + item-rect real click,
    // invoked by the .ps1 after the message path did not stick. The .ps1
    // arranges the foreground immediately before calling this -- that is the
    // ONLY place in the printer step where foreground state is touched. Dual
    // rect-layout attempts kept from the previous batch; the read-back gate
    // after the click is what keeps a mis-click from reaching Print.
    public static string ListRectClick(IntPtr h, string ch, int i) {
      if (ch != "lv") return "no-backup";   // cb/lb are message-only by design
      int cap = Marshal.SizeOf(typeof(LVITEMW));
      IntPtr pr = Marshal.AllocHGlobal(cap);
      try {
        SafeSend(h, 0x100F, (IntPtr)i, IntPtr.Zero);               // LVM_ENSUREVISIBLE
        // attempt A: wParam = item index, RECT written at lParam
        Marshal.Copy(new byte[cap], 0, pr, cap);
        SafeSend(h, 0x100E, (IntPtr)i, pr);                        // LVM_GETITEMRECT
        if (ClickItemRect(h, pr)) return "rect-click";
        // attempt B: wParam = LVIR_BOUNDS(0), item seeded in LVITEM layout
        byte[] seed = new byte[cap];
        BitConverter.GetBytes(i).CopyTo(seed, 4);                  // iItem at offset 4
        Marshal.Copy(seed, 0, pr, cap);
        SafeSend(h, 0x100E, IntPtr.Zero, pr);
        if (ClickItemRect(h, pr)) return "rect-click";
        return "no-rect";
      } finally { Marshal.FreeHGlobal(pr); }
    }
    private static bool ClickItemRect(IntPtr h, IntPtr buf) {
      int l = Marshal.ReadInt32(buf, 0);
      int t = Marshal.ReadInt32(buf, 4);
      int r = Marshal.ReadInt32(buf, 8);
      int b = Marshal.ReadInt32(buf, 12);
      if (r - l <= 4 || b - t <= 4) return false;
      PT pt = new PT();
      pt.X = l + (r - l) / 2;
      pt.Y = t + (b - t) / 2;
      if (!ClientToScreen(h, ref pt)) return false;
      SetCursorPos(pt.X, pt.Y);
      mouse_event(0x0002, 0, 0, 0, UIntPtr.Zero);
      mouse_event(0x0004, 0, 0, 0, UIntPtr.Zero);
      return true;
    }
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
function Get-FgLabel() {
    # 'pid:title' of the foreground window -- the context field both timeout
    # faces (L1 fail line and L2 watchdog line) carry.
    $h = [RP.U]::GetForegroundWindow()
    if ($h -eq [IntPtr]::Zero) { return '0:none' }
    $fpid = 0
    [void][RP.U]::GetWindowThreadProcessId($h, [ref]$fpid)
    $sb = New-Object System.Text.StringBuilder 96
    [void][RP.U]::GetWindowText($h, $sb, 96)
    $t = $sb.ToString() -replace '[\r\n]+', ' '
    if ($t.Length -gt 40) { $t = $t.Substring(0, 40) }
    return ('{0}:{1}' -f $fpid, $t)
}
function Invoke-StageTimeout([string]$stage, [string]$fnBody, [string]$call, [int]$timeoutMs, [string]$targetHex) {
    # L1 hard timeout around the genuinely unbounded cross-process calls (UIA
    # tree walk, spooler query). A fresh runspace executes the helper text +
    # the call under a WaitOne ceiling; on timeout the fail line is emitted
    # FIRST (code face before the 600s shell watchdog, printer-step-hang-
    # timeout with stage/elapsed/fg/target) and the process exits. Deliberately
    # NO Stop()/Dispose on the timeout path -- stopping a stuck COM call can
    # itself block; the exit tears everything down instead.
    $rs = [runspacefactory]::CreateRunspace()
    $rs.Open()
    $ps = [powershell]::Create()
    $ps.Runspace = $rs
    [void]$ps.AddScript($fnBody + "`n" + $call)
    $ih = $ps.BeginInvoke()
    if (-not $ih.AsyncWaitHandle.WaitOne($timeoutMs)) {
        Fail 'report-printer' ("printer-step-hang-timeout stage={0} elapsed={1} fg='{2}' target={3}" -f $stage, $timeoutMs, (Get-FgLabel), $targetHex)
    }
    $out = $null
    try { $out = $ps.EndInvoke($ih) } catch { $out = $null }
    try { $ps.Dispose() } catch { }
    try { $rs.Close() } catch { }
    if ($out -eq $null -or $out.Count -eq 0) { return '' }
    return [string]$out[0]
}
function Get-KidClassSummary([string[]]$kids) {
    # Compact 'class:count,...' summary of the dialog's Win32 children -- the
    # scene that travels back in failures when nothing is classifiable.
    $cnt = @{}
    foreach ($k in $kids) {
        $p = $k.Split([char]'|', 3)
        if ($p.Length -lt 2) { continue }
        $cls = $p[1]
        if ($cls -eq '') { $cls = '(none)' }
        if ($cnt.ContainsKey($cls)) { $cnt[$cls] = $cnt[$cls] + 1 } else { $cnt[$cls] = 1 }
    }
    $parts = @()
    foreach ($key in @($cnt.Keys | Sort-Object)) { $parts += ('{0}:{1}' -f $key, $cnt[$key]) }
    return ($parts -join ',')
}
function Test-ListAdjToCaption([string]$rect, [string]$anchor) {
    # Geometry rank for the caption-anchored pick (eleventh batch): the Static
    # caption 'select printers' (CJK assembled from char codes, file stays
    # ASCII) marks the list sitting right under or around it. Ranks only --
    # NEVER excludes -- so a wrong pick still shows up in the probe instead of
    # hiding behind it.
    if ($anchor -eq '' -or $rect -eq '') { return $false }
    $a = $anchor.Split([char]',')
    $c = $rect.Split([char]',')
    if ($a.Length -lt 4 -or $c.Length -lt 4) { return $false }
    $al = [double]$a[0]; $at = [double]$a[1]; $ar = [double]$a[2]; $ab = [double]$a[3]
    $cl = [double]$c[0]; $ct = [double]$c[1]; $cr = [double]$c[2]; $cb = [double]$c[3]
    if ($cl -ge $ar -or $cr -le $al) { return $false }                  # no x overlap
    if ($ct -ge ($ab - 4) -and $ct -le ($ab + 100)) { return $true }    # top just below
    if ($ct -le $at -and $cb -ge $ab) { return $true }                  # caption inside
    return $false
}
function Read-W32PrinterList([IntPtr]$h, [string[]]$kids, [string]$pinId) {
    # The printer list among the dialog children -> @{names; ctrl; ch; probe}.
    # Window-message channels per candidate: ComboBox / ListBox / SysListView32
    # -- E2 measured this same dialog's list (Brother / Microsoft Print to PDF /
    # OneNote) through Win32; the ninth shot's UIA FolderView path reports zero
    # named children, so the marker match never fired.
    # Eleventh-batch fixes on top (tenth shot: n=3 but list=';;'):
    #   - ORDER is caption-anchored, not class-guessed: the Static caption
    #     marks the real container; adjacency ranks, presence never excludes
    #     (pin still outranks geometry -- caller pinned it deliberately);
    #   - EVERY readable candidate is read AND traced (ch, per-item reply
    #     counts, first text) so the probe tells 'right control, wrong
    #     message' apart from 'virtual list answers nothing' by itself.
    # -PrinterComboId stays the pinned escape hatch: given but absent = the
    # old printer-combo-id-not-found hard stop (meaning unchanged).
    $selWord = ([char]0x9009).ToString() + ([char]0x62E9).ToString() + ([char]0x6253).ToString() + ([char]0x5370).ToString() + ([char]0x673A).ToString()  # select printers
    $anchorRect = ''
    foreach ($k in $kids) {
        $p = $k.Split([char]'|', 4)
        if ($p.Length -lt 4) { continue }
        if ($p[1] -eq 'Static' -and $p[2].Contains($selWord)) { $anchorRect = $p[3]; break }
    }
    $cands = @()
    if ($pinId -ne '') {
        $ph = [RP.U]::GetDlgItem($h, [int]$pinId)
        if ($ph -eq [IntPtr]::Zero) { Fail 'report-printer' 'printer-combo-id-not-found' }
        $cands += @{ hw = $ph; cls = 'pinned'; rect = ''; pri = 4 }
    }
    $auto = @()
    foreach ($k in $kids) {
        $p = $k.Split([char]'|', 4)
        if ($p.Length -lt 4) { continue }
        $hw = [IntPtr]([long]$p[0])
        $cls = $p[1]
        $rect = $p[3]
        $auto += @{ hw = $hw; cls = $cls; rect = $rect; pri = 0 }
        if ($cls -eq 'SysListView32' -or $cls -eq 'ListBox' -or $cls -eq 'ComboBox' -or $cls -eq 'ComboBoxEx32') {
            $pri = 1
            if (Test-ListAdjToCaption $rect $anchorRect) { $pri = 3 }
            $cands += @{ hw = $hw; cls = $cls; rect = $rect; pri = $pri }
        }
    }
    if ($cands.Count -eq 0) { $cands = $auto }   # class-blind probe fallback
    $traces = @()
    # Twelfth batch: total budget for the whole probe loop. Single messages
    # are already bounded by SafeSend (3s); this caps the SUM so a wall of
    # candidates x items can never reach the shell watchdog -- on breach we
    # fail HERE with the same timeout code face (stage=win32-list) + trace.
    $budget = [Diagnostics.Stopwatch]::StartNew()
    $names0 = @(); $ctrl0 = [IntPtr]::Zero; $ch0 = ''
    foreach ($cd in ($cands | Sort-Object -Property pri)) {
        if ($budget.ElapsedMilliseconds -gt 15000) {
            Fail 'report-printer' ("printer-step-hang-timeout stage=win32-list elapsed={0} fg='{1}' target=0x{2} probe='{3}'" -f $budget.ElapsedMilliseconds, (Get-FgLabel), $h.ToInt64().ToString('x'), (($traces -join ' ; ').Substring(0, [Math]::Min(200, ($traces -join ' ; ').Length))))
        }
        $ch = [RP.U]::ListChannel($cd.hw)
        if ($ch -eq '') { $traces += ("{0}:no-channel" -f $cd.cls); continue }
        $names = @([RP.U]::ListRead($cd.hw, $ch))
        $info = [RP.U]::ListReadInfo($cd.hw, $ch)
        $traces += ("{0}@{1}:{2}" -f $cd.cls, ($cd.hw.ToInt64().ToString('x')), $info)
        if ($names.Count -eq 0) { continue }
        if (($names -join ' ') -match 'Microsoft Print to PDF') {
            $pb = ($traces -join ' ; ')
            if ($pb.Length -gt 400) { $pb = $pb.Substring(0, 400) }
            return @{ names = $names; ctrl = $cd.hw; ch = $ch; probe = $pb }
        }
        if ($names0.Count -eq 0) { $names0 = $names; $ctrl0 = $cd.hw; $ch0 = $ch }
    }
    $pb = ($traces -join ' ; ')
    if ($traces.Count -eq 0) { $pb = 'na' }
    if ($pb.Length -gt 400) { $pb = $pb.Substring(0, 400) }
    return @{ names = $names0; ctrl = $ctrl0; ch = $ch0; probe = $pb }
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
# EIGHTH BATCH (2026-10-22) -- the entry act chain is GONE.
# Seventh-gun modebar probe (read-only, two evidence files): the strip has
# only 4 UIA TabItems -- ProjectInfoMode(313,158) / BuildingConstructionMode
# (395,158) / LightingDesignMode(466,158) / InteractionModes.Results.
# ResultMode(537,158,91,43) isSel=True -- and the SELECTED ResultMode's
# VISUAL label is the 'calculation element' tab, while the strip VISUALLY
# shows seven labels (design/draft/light/calc/export/report/brand) whose
# export/report/brand have NO TabItem element at all (UIA unreachable).
# Meaning: everything the old chain invoked/selected was the CALCULATION
# page -- that alone explains three guns (lit calculation bar + target_pat=1
# + print_btn=0). So the legacy match above is kept as a RECORD only
# (legacy= in the scene): no Invoke, no Select, no not-found hard stop, and
# the mode change now goes through the VISUAL scan (report/export label ->
# click -> print_btn confirmation) further down.
$legacy = 'miss'
if ($modeVia -ne '') { $legacy = $modeVia }
$selName = ''
$readback = 'no-tabcontrol'
$readErr = 0
# Sixth batch history (kept for context): '?' as an initial value leaked as
# a fifth state whenever a non-target tab was found first. The closed set is
# now 1|0|null|err everywhere, target reads are UNCONDITIONAL before Fail,
# and -- since the eighth batch -- the gate predicate is print_btn alone;
# the old found-but-wrong-tab retry predicate retired with the retry.
$targetSel = 'err'
$targetPat = 'err'
$sameRid = '-'
$containerVia = 'none'
$ancState = 'miss'
$crect = '-'
$coff = '-'
$tfind = 'miss'
# 2026-10-21 fifth batch (fourth-gun evidence): the provider returned NULL
# for IsSelected and an empty RuntimeId on these elements (err=0, not an
# exception) -- so every single-path read that assumed a True/False answer
# was reading a hole. Three upgrades, intent unchanged (confirm the report
# page really carried the selection): (a) read BOTH paths -- the property
# (.Current.IsSelected) and the pattern (.GetCurrentPattern(...).Current
# .IsSelected) -- and accept EITHER as True; (b) record every read as one of
# 1/0/null/err so an empty answer can never masquerade as False again;
# (c) the print button (ButtonPrintDocument) exists ONLY on the report page
# (both guns: whole-tree Print scan zero hits while unselected; measured id
# when selected in E2) -> it becomes a second, functional way through the
# gate, recorded as print_btn= either way.
$tcIdCond = New-Object System.Windows.Automation.PropertyCondition(
    [System.Windows.Automation.AutomationElement]::AutomationIdProperty, 'ModeSelectionTabControl')
$tabs2 = $null
$anc = $null
if ($mode -eq $null) {
    $ancState = 'no-entry'
} else {
    try {
        $anc = $mode.FindFirst([System.Windows.Automation.TreeScope]::Ancestors, $tcIdCond)
        if ($anc -ne $null) { $ancState = 'hit' }
    } catch { $ancState = 'err' }
}
if ($anc -ne $null) {
    $tabs2 = $anc
    $containerVia = 'ancestors'
} else {
    $tabs2 = ById 'ModeSelectionTabControl' 2500
    $containerVia = 'byid'
}
if ($tabs2 -ne $null) {
    $readback = 'no-selected-tab'
    try {
        $cb = $tabs2.Current.BoundingRectangle
        $crect = ("{0},{1},{2},{3}" -f [int]$cb.X, [int]$cb.Y, [int]$cb.Width, [int]$cb.Height)
        $coff = [string]$tabs2.Current.IsOffscreen
    } catch { $crect = 'unreadable' }
    $tc2 = New-Object System.Windows.Automation.PropertyCondition(
        [System.Windows.Automation.AutomationElement]::ControlTypeProperty,
        [System.Windows.Automation.ControlType]::TabItem)
    # Seventh batch located the target here; eighth batch keeps the
    # relocation as a READ-ONLY evidence source (tfind=/target_*) but drops
    # the select replay and its retry rounds: selecting ResultMode switches
    # to the CALCULATION page (seventh-gun modebar probe: its visual label
    # IS the calculation tab), so retrying it just reproduces three guns of
    # failure. The selected-tab readback moved AFTER the visual click.
    # Whether entry/gate containers are truly different instances stays
    # pending real machine -- tfind=/anc= in the scene will tell.
    $targetNow = $null
    $tnItems = $tabs2.FindAll([System.Windows.Automation.TreeScope]::Descendants, $tc2)
    for ($k = 0; $k -lt $tnItems.Count; $k++) {
        $tnm = ''
        try { $tnm = [string]$tnItems.Item($k).Current.Name } catch { }
        if ($tnm -match 'ResultMode') { $targetNow = $tnItems.Item($k); $tfind = 'hit'; break }
    }
    $tnRid = ''
    if ($targetNow -ne $null) {
        try { $tnRid = (($targetNow.Current.RuntimeId) -join '.') } catch { }
    }
    # UNCONDITIONAL target reads on the SAME-SOURCE element (fifth-gun '?'
    # never again; sixth-gun two-path contradiction now means one element):
    # absent target -> both err, scene carries tfind=miss.
    if ($targetNow -eq $null) {
        $targetSel = 'err'
        $targetPat = 'err'
    } else {
        try {
            $tv = $targetNow.Current.IsSelected
            if ($null -eq $tv) { $targetSel = 'null' } elseif ($tv) { $targetSel = '1' } else { $targetSel = '0' }
        } catch { $targetSel = 'err'; $readErr++ }
        try {
            $tpv = $targetNow.GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Current.IsSelected
            if ($null -eq $tpv) { $targetPat = 'null' } elseif ($tpv) { $targetPat = '1' } else { $targetPat = '0' }
        } catch { $targetPat = 'err' }
    }
}
# ---- FOURTH WAY (eighth batch): visual scan of the mode strip ----
# Seventh-gun modebar probe settled the target question (see the entry
# comment): export/report are VISUAL labels with no element, so trust no id
# and no name match -- hit-test pixels with ElementFromPoint along the
# measured TabItem line, take the point whose runtime name carries the
# report word (export as second choice), click it, and let the print button
# -- which exists ONLY on the report page (four guns of evidence) -- decide
# pass. Nothing resolution-hardcoded: the row line and the span come from
# ONE picked row of live TabItems (ninth batch -- cluster into rows and pick
# the mode bar, see ROW PICK below; span extends +320px right of the picked
# row for the three label-only tabs; structural margin, not a coordinate);
# 8px is the step; EVERY named hit
# lands in the scene and a miss fails with that list -- never a blind click.
# Already on the report page (print_btn=1 before any click) short-circuits.
$printBtn = 0
$pe0 = ById 'ButtonPrintDocument' 400
if ($pe0 -ne $null) { $printBtn = 1 }
$hitWord = '-'
$clickVia = '-'
$hits = @()
$rowsScene = 'na'   # row-set summary 'centerY:count;...' (ninth batch; AGG diagnostics demoted to this)
$rowGeo = 'na'      # picked row geometry y/x-range (ninth batch)
if ($printBtn -eq 0) {
    $repW = -join ([char[]]@(0x62A5, 0x8868))   # report
    $expW = -join ([char[]]@(0x5BFC, 0x51FA))   # export
    $tabRow = @()
    if ($tabs2 -ne $null) {
        try { $tabRow = $tnItems } catch { $tabRow = @() }
    }
    # ---- ROW PICK (ninth batch): cluster TabItems into rows, pick ONE ----
    # Eighth-gun probe closed the line-level root cause (no re-guessing):
    # ModeSelectionTabControl's rect covers the whole workspace
    # (112,158,1424,760) and its 23 TabItems are left tool strip 16 + right
    # tool strip 3 + mode bar 4 (tool tabs and mode tabs share one control).
    # The eighth batch averaged all 22 readable rects -> midY=381 (that line
    # answers window title / tool tab names / the pseudo-color button), the
    # scan never touched the mode bar (true centerY 179.5) and scanX0=104
    # (left strip x=112 dragged to the window edge). Probe scene: AGG n=22
    # midY=381 scanX0=104 vs hits first x=104 equal VERBATIM; the four mode
    # bar items all carry centerY=179.5.
    # Fix: cluster by centerY (ascending, +-8 tolerance), then pick ONE row
    # and take minX/maxX/centerY from THAT row only -- never the aggregate:
    #   layer 1 -- the row whose Name carries 'ResultMode'. Only one of the
    #     four bar items carries the dotted namespace prefix (the other
    #     three are bare names), so a prefix-wide match would keep a single
    #     ITEM instead of a row; 'ResultMode' anchors exactly that item and
    #     the whole row it sits in.
    #   layer 2 -- among rows with >=2 TabItems take the smallest centerY,
    #     span desc as tie-break (span desc alone would pick a tool row:
    #     left+right strips share centerY and span the full width).
    #   both empty -> modebar-row-empty n= rows= scene, FAIL right here:
    #     no fallback to the unfiltered aggregate, no scan, no blind click.
    # The +320 span margin applies to the PICKED row (export/report/brand
    # labels have no UIA element and sit right of the 4 tabs' right edge --
    # the margin is their only chance to be hit-tested).
    $items4 = @()
    for ($q = 0; $q -lt $tabRow.Count; $q++) {
        try {
            $r4 = $tabRow.Item($q).Current.BoundingRectangle
            if ($r4.Width -le 0) { continue }
            $nmA = ''
            try { $nmA = [string]$tabRow.Item($q).Current.Name } catch { $nmA = '' }
            $items4 += [pscustomobject]@{
                X    = [double]$r4.X
                R    = [double]($r4.X + $r4.Width)
                Cy   = [double]($r4.Y + ($r4.Height / 2.0))
                Name = $nmA
            }
        } catch { $readErr++ }
    }
    if ($items4.Count -eq 0) {
        Fail 'report-mode' ("modebar-scan-miss hits='no-tabrow' read_err={0} legacy={1}" -f $readErr, $legacy)
    }
    $items4 = @($items4 | Sort-Object -Property Cy)
    $rows4 = @()
    $curRow = @()
    $anchorCy = 0.0
    foreach ($itA in $items4) {
        if ($curRow.Count -eq 0) {
            $curRow = @($itA)
            $anchorCy = $itA.Cy
        } elseif ([math]::Abs(($itA.Cy - $anchorCy)) -le 8.0) {
            $curRow += $itA
        } else {
            $rows4 += ,$curRow
            $curRow = @($itA)
            $anchorCy = $itA.Cy
        }
    }
    if ($curRow.Count -gt 0) { $rows4 += ,$curRow }
    $rowTxts = @()
    foreach ($rowA in $rows4) {
        $cySum = 0.0
        foreach ($itB in $rowA) { $cySum += $itB.Cy }
        $cyAvg = ($cySum / $rowA.Count)
        $cyTxt = $cyAvg.ToString('0.#', [System.Globalization.CultureInfo]::InvariantCulture)
        $rowTxts += ("{0}:{1}" -f $cyTxt, $rowA.Count)
    }
    $rowsScene = ($rowTxts -join ';')
    if ($rowTxts.Count -gt 16) {
        $rowsScene = (($rowTxts[0..15]) -join ';') + ';+more'
    }
    $pick4 = $null
    $pickWhy = 'none'
    foreach ($rowA in $rows4) {
        $anchorHit = $false
        foreach ($itB in $rowA) {
            if ($itB.Name -match 'ResultMode') { $anchorHit = $true; break }
        }
        if ($anchorHit) { $pick4 = $rowA; $pickWhy = 'resultmode-row'; break }
    }
    if ($pick4 -eq $null) {
        $candA = @()
        foreach ($rowA in $rows4) {
            if ($rowA.Count -lt 2) { continue }
            $mnB = [double]::MaxValue
            $mxB = 0.0
            $cySum = 0.0
            foreach ($itB in $rowA) {
                if ($itB.X -lt $mnB) { $mnB = $itB.X }
                if ($itB.R -gt $mxB) { $mxB = $itB.R }
                $cySum += $itB.Cy
            }
            $candA += [pscustomobject]@{
                Row  = $rowA
                Cy   = ($cySum / $rowA.Count)
                Span = ($mxB - $mnB)
            }
        }
        if ($candA.Count -gt 0) {
            $bestA = $candA | Sort-Object -Property @{Expression = 'Cy'; Ascending = $true}, @{Expression = 'Span'; Descending = $true} | Select-Object -First 1
            $pick4 = $bestA.Row
            $pickWhy = 'min-centerY-span'
        }
    }
    if ($pick4 -eq $null) {
        # No row qualified (empty row set or no row passed both layers):
        # FAIL here with the full row scene. This code must NEVER fall back
        # to the unfiltered aggregate scan (ninth batch, negative contract).
        Fail 'report-mode' ("modebar-row-empty n={0} rows='{1}' read_err={2} legacy={3} print_btn={4}" -f $items4.Count, $rowsScene, $readErr, $legacy, $printBtn)
    }
    $minX = [double]::MaxValue
    $maxX = 0.0
    $midY = 0.0
    $n4 = 0
    foreach ($itC in $pick4) {
        if ($itC.X -lt $minX) { $minX = $itC.X }
        if ($itC.R -gt $maxX) { $maxX = $itC.R }
        $midY += $itC.Cy
        $n4++
    }
    $midY = [int]($midY / $n4)
    $scanX0 = [int]($minX - 8)
    $scanX1 = [int]($maxX + 320)
    $rowGeo = ("y={0} x={1}..{2} n={3} pick={4}" -f $midY, $scanX0, $scanX1, $n4, $pickWhy)
    $hitRep = $null
    $hitRepX = 0
    $hitExp = $null
    $hitExpX = 0
    for ($sx = $scanX0; $sx -le $scanX1; $sx += 8) {
        $el4 = $null
        try { $el4 = [System.Windows.Automation.AutomationElement]::FromPoint((New-Object System.Windows.Point($sx, $midY))) } catch { }
        if ($el4 -eq $null) { continue }
        $nm4 = ''
        try { $nm4 = [string]$el4.Current.Name } catch { }
        $nm4 = ($nm4 -replace '\s+', ' ').Trim()
        if ($nm4 -eq '') { continue }
        if ($hits.Count -lt 10) {
            $short = $nm4
            if ($short.Length -gt 24) { $short = $short.Substring(0, 24) }
            $hits += ("{0}:{1}" -f $sx, (Esc $short))
        }
        if ($hitRep -eq $null -and $nm4.IndexOf($repW) -ge 0) { $hitRep = $el4; $hitRepX = $sx }
        if ($hitExp -eq $null -and $nm4.IndexOf($expW) -ge 0) { $hitExp = $el4; $hitExpX = $sx }
    }
    $target4 = $null
    $targetX = 0
    if ($hitRep -ne $null) { $target4 = $hitRep; $targetX = $hitRepX; $hitWord = 'report' }
    elseif ($hitExp -ne $null) { $target4 = $hitExp; $targetX = $hitExpX; $hitWord = 'export' }
    if ($target4 -eq $null) {
        # nothing on the strip carried the words -- scene = what the pixels
        # DID answer (names may be empty there; the list says so)
        Fail 'report-mode' ("modebar-scan-miss hits='{0}' legacy={1} print_btn={2} rows='{3}' row='{4}'" -f (($hits -join ' ; ')), $legacy, $printBtn, $rowsScene, $rowGeo)
    }
    # click: Invoke when available, else the element center, else the exact
    # scanned pixel (label-only tabs may carry no element bounds)
    try {
        $target4.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern).Invoke()
        $clickVia = 'invoke'
    } catch {
        $rw4 = 0.0
        $rh4 = 0.0
        try { $r4b = $target4.Current.BoundingRectangle; $rw4 = $r4b.Width; $rh4 = $r4b.Height } catch { }
        if ($rw4 -gt 0 -and $rh4 -gt 0) {
            ClickCenter $target4
            $clickVia = 'center'
        } else {
            [void][RP.U]::SetCursorPos($targetX, $midY)
            Start-Sleep -Milliseconds 150
            [RP.U]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
            [RP.U]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
            $clickVia = 'pixel'
        }
    }
    Start-Sleep -Milliseconds 800
    $pe = ById 'ButtonPrintDocument' 2500
    if ($pe -ne $null) { $printBtn = 1 }
}
# post-click selected-tab readback (dual-path, four-state) -- a SCENE field,
# not the gate: what the bar reports after the click, whatever the label
# truth is (the pixel label lives in the screenshots, not in these names).
$selName = ''
$readback = 'no-tabcontrol'
if ($tabs2 -ne $null) {
    $readback = 'no-selected-tab'
    $all2 = $null
    try { $all2 = $tabs2.FindAll([System.Windows.Automation.TreeScope]::Descendants, $tc2) } catch { $readback = 'container-stale' }
    if ($all2 -ne $null) {
        $swSel = [Diagnostics.Stopwatch]::StartNew()
        while ($swSel.ElapsedMilliseconds -lt 1200 -and $selName -eq '') {
            for ($i2 = 0; $i2 -lt $all2.Count; $i2++) {
                $s1 = 'err'
                try {
                    $v1 = $all2.Item($i2).Current.IsSelected
                    if ($null -eq $v1) { $s1 = 'null' } elseif ($v1) { $s1 = '1' } else { $s1 = '0' }
                } catch { $readErr++ }
                $s2 = 'err'
                try {
                    $v2 = $all2.Item($i2).GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Current.IsSelected
                    if ($null -eq $v2) { $s2 = 'null' } elseif ($v2) { $s2 = '1' } else { $s2 = '0' }
                } catch { $readErr++ }
                if ($s1 -ne '1' -and $s2 -ne '1') { continue }
                try { $selName = [string]$all2.Item($i2).Current.Name } catch { $selName = 'unreadable' }
                $readback = 'selected-tab'
                $sRid = ''
                try { $sRid = (($all2.Item($i2).Current.RuntimeId) -join '.') } catch { }
                if ($sRid -eq '' -or $tnRid -eq '') { $sameRid = 'na' }
                elseif ($sRid -eq $tnRid) { $sameRid = '1' }
                else { $sameRid = '0' }
                break
            }
            if ($selName -ne '') { break }
            Start-Sleep -Milliseconds 250
        }
    }
}
if ($printBtn -ne 1) {
    # human-readable failure: the click happened (or was skipped) but the
    # report page did not confirm -- full scene, no conclusion words
    Fail 'report-mode' ("report-mode-not-confirmed via=modebar-scan word={0} click={1} selected='{2}' readback={3} legacy={4} target_selected={5} target_pat={6} same={7} container={8} anc={9} crect={10} coff={11} read_err={12} print_btn={13} tfind={14} hits='{15}'" -f $hitWord, $clickVia, (Esc $selName), $readback, $legacy, $targetSel, $targetPat, $sameRid, $containerVia, $ancState, $crect, $coff, $readErr, $printBtn, $tfind, (($hits -join ' ; ')))
}
Emit 'report-mode' 'ok' ("via=modebar-scan word={0} click={1} selected='{2}' same={3} print_btn=1 legacy={4} tfind={5} rows='{6}' row='{7}'" -f $hitWord, $clickVia, (Esc $selName), $sameRid, $legacy, $tfind, $rowsScene, $rowGeo)

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
# dialog -- system settings are outside the allowed scope (read-only queries
# only, never a system-setting write, no paper). The Print-to-PDF SAVE window
# follows as the second dialog (its type row carries '.pdf'; its button 1 is
# measured 'Save(&S)').
# 2026-10-22 TENTH BATCH, from the ninth shot's two-sample root cause: the UIA
# tree of this dialog is 30 Panes and the printer list FolderView has ZERO
# named children (samples 6s apart byte-identical), so the old
# '$txt1 -match <printer names>' classification structurally never fired and
# every run died at unclassified-dialog. What moves:
#   - CLASSIFY by the measured accelerator on button 1 ('&P' = print dialog,
#     '&S'/'\.pdf' = save window; the UIA marker set stays as fallback when
#     the button text cannot be read),
#   - SELECT via Win32 list messages (E2 read the list contents through Win32
#     on this same dialog; the 30-Pane UIA text survives as the ui= evidence
#     field, nothing else about it changes),
#   - SHORTCUT when the read-only default printer already is the PDF one,
#   - every failure carries the Win32 child scene + default printer; no blind
#     clicks, and report-printer says ok ONLY after the print dialog closed
#     and the save window appeared.
#   - twelfth batch (eleventh shot: step hung 2/2, 600s shell watchdog, NO
#     code face): step watchdog armed at entry (120s pure-.NET timer thread
#     writes printer-step-hang-timeout with stage/elapsed/fg/target and
#     force-exits -- legal off the pipeline thread because it runs no PS),
#     L1 runspace ceilings on the unbounded cross-process calls (UIA tree,
#     spooler), a 15s total budget on the list probe loop, stage marks at
#     every sub-action for watchdog localization. Root cause is NOT assumed:
#     whichever of the three suspicions sticks, a code face comes back.
# Thirteenth batch: the breadcrumb path is set BEFORE arming so the very first
# transition (ARMED) lands on disk -- no stdout channel involved.
$crumb = $BreadCrumbPath
if ($crumb -eq '') { $crumb = (Join-Path $env:TEMP 'dialux_report_printer_crumb.txt') }
[RP.U]::WSetCrumb($crumb)
[RP.U]::WArm(120000, 'report-printer')
[RP.U]::WTarget([IntPtr]::Zero)
[RP.U]::WMark('wait-dialog')
$hDlg1 = Wait-Dialog $DialogTimeoutMs ([IntPtr]::Zero)
if ($hDlg1 -eq [IntPtr]::Zero) { Fail 'report-printer' 'print-dialog-not-found' }
[RP.U]::WTarget($hDlg1)
[RP.U]::WMark('uia-dialog-text')
$uiaHex = ('0x{0:x}' -f $hDlg1.ToInt64())
# L1: the UIA tree walk is the one call in this step that can block forever
# on a foreign provider (twelfth-batch suspicion, not a conclusion) -- fresh
# runspace, 10s ceiling, timeout fails with the same code face.
$txt1 = Invoke-StageTimeout 'uia-dialog-text' ('function Get-DlgUiText([IntPtr]$h) {' + [string](Get-Command Get-DlgUiText).ScriptBlock + '}') ('Get-DlgUiText ([IntPtr]{0})' -f $hDlg1.ToInt64()) 10000 $uiaHex
[RP.U]::WMark('win32-scene')
$kids = [RP.U]::ChildScene($hDlg1)
$classSummary = Get-KidClassSummary $kids
[RP.U]::WMark('default-printer')
# L1: spooler RPC can stall on a wedged service -- 5s ceiling, same face.
$defName = Invoke-StageTimeout 'default-printer' '' '[RP.U]::GetDefaultPrinterName()' 5000 $uiaHex
[RP.U]::WMark('btn1-text')
$btn1t = [RP.U]::DlgItemText($hDlg1, 1)
$snip = ($txt1 -replace '\s+', ' ')
if ($snip.Length -gt 120) { $snip = $snip.Substring(0, 120) }
$hSave = [IntPtr]::Zero
$printerOk = $false
$printerVia = ''
$selVia = ''
$listNames = ''
$probe = 'na'
$pickIdx = -1
if ($btn1t -match '&P' -or ($btn1t -eq '' -and $txt1 -match 'FolderView|Print to PDF|OneNote|Brother')) {
    # this is the print dialog: read the list (one settle re-read, the list
    # fills after the dialog paints), then pick the PDF entry.
    [RP.U]::WMark('win32-list-read')
    $listInfo = Read-W32PrinterList $hDlg1 $kids $PrinterComboId
    if (@($listInfo.names).Count -eq 0) {
        [RP.U]::WMark('win32-list-settle')
        Start-Sleep -Milliseconds 800
        $listInfo = Read-W32PrinterList $hDlg1 $kids $PrinterComboId
    }
    $probe = [string]$listInfo.probe
    $listNames = (@($listInfo.names) -join ';')
    if ($listNames -ne '' -and $listNames -match 'Microsoft Print to PDF') {
        # main route: MESSAGE select + read-back -- no foreground, no mouse on
        # this path (twelfth batch: the eleventh shot's foreground exposure is
        # removed from the main route; Print stays gated by the read-back).
        for ($ci = 0; $ci -lt @($listInfo.names).Count; $ci++) {
            if ($listInfo.names[$ci] -match 'Microsoft Print to PDF') { $pickIdx = $ci; break }
        }
        [RP.U]::WMark('printer-select-msg')
        $selVia = [RP.U]::ListSelect($listInfo.ctrl, $listInfo.ch, $pickIdx)
        $readBack = [RP.U]::ListSelText($listInfo.ctrl, $listInfo.ch)
        if ($readBack -notmatch 'Microsoft Print to PDF') {
            # backup path: rect real click. Foreground is arranged ONLY here
            # (foreground is never a precondition of the main route), and the
            # read-back gate below still decides whether Print is ever clicked.
            [RP.U]::WMark('rect-backup-foreground')
            $fg = [RP.U]::GetForegroundWindow()
            if ($fg -ne $hDlg1) { [void][RP.U]::SetForegroundWindow($hDlg1); Start-Sleep -Milliseconds 300 }
            [RP.U]::WMark('rect-backup-click')
            $selVia = ('{0}+{1}' -f $selVia, [RP.U]::ListRectClick($listInfo.ctrl, $listInfo.ch, $pickIdx))
            $readBack = [RP.U]::ListSelText($listInfo.ctrl, $listInfo.ch)
        }
        if ($readBack -notmatch 'Microsoft Print to PDF') {
            Fail 'report-printer' ("printer-not-selectable-use-PrinterComboId via=win32-list ch={0} selvia={1} idx={2} readback='{3}' list='{4}' default='{5}' btn1='{6}' win32='{7}' probe='{8}' ui='{9}'" -f $listInfo.ch, $selVia, $pickIdx, $readBack, $listNames, $defName, $btn1t, $classSummary, $probe, $snip)
        }
        $printerVia = 'win32-list'
        $printerOk = $true
    } elseif ($listNames -ne '') {
        Fail 'report-printer' ("printer-not-in-win32-list n={0} list='{1}' ch={2} default='{3}' btn1='{4}' win32='{5}' probe='{6}' ui='{7}'" -f (@($listInfo.names).Count), $listNames, $listInfo.ch, $defName, $btn1t, $classSummary, $probe, $snip)
    } elseif ($defName -match 'Microsoft Print to PDF') {
        # short route (read-only): the dialog opens on the default printer and
        # the default IS Microsoft Print to PDF -- nothing to select.
        $printerVia = 'default-shortcut'
        $selVia = 'none'
        $printerOk = $true
    } else {
        Fail 'report-printer' ("printer-list-win32-unreadable win32='{0}' default='{1}' btn1='{2}' probe='{3}' ui='{4}'" -f $classSummary, $defName, $btn1t, $probe, $snip)
    }
} elseif ($btn1t -match '&S' -or $txt1 -match '\.pdf') {
    # the SAVE window came directly (no print dialog in between)
    [RP.U]::WDisarm()
    Emit 'report-printer' 'ok' 'print-dialog-absent-default-is-pdf'
    $hSave = $hDlg1
} else {
    Fail 'report-printer' ("unclassified-dialog ui='{0}' win32='{1}' default='{2}' btn1='{3}'" -f $snip, $classSummary, $defName, $btn1t)
}
if ($printerOk) {
    # functional gate: after the click the print dialog must CLOSE and the save
    # window must APPEAR -- "it was clicked" is never the ok. BM_CLICK is a
    # message post: no foreground precondition anywhere in this block.
    [RP.U]::WMark('print-click')
    $hPrint = [RP.U]::GetDlgItem($hDlg1, 1)          # measured: print button = GetDlgItem(1)
    if ($hPrint -eq [IntPtr]::Zero) { Fail 'report-printer' 'print-button-not-found' }
    [void][RP.U]::SendMessage($hPrint, 0x00F5, [IntPtr]::Zero, [IntPtr]::Zero)   # BM_CLICK
    [RP.U]::WMark('gate-printdlg-close')
    $gsw = [Diagnostics.Stopwatch]::StartNew()
    while ($gsw.ElapsedMilliseconds -lt 5000 -and [RP.U]::IsWindowVisible($hDlg1)) {
        Start-Sleep -Milliseconds 200
    }
    if ([RP.U]::IsWindowVisible($hDlg1)) {
        Fail 'report-printer' ("print-dialog-still-open via={0} list='{1}' default='{2}' btn1='{3}' probe='{4}' ui='{5}'" -f $printerVia, $listNames, $defName, $btn1t, $probe, $snip)
    }
    [RP.U]::WMark('gate-save-appear')
    $hSave = Wait-Dialog $DialogTimeoutMs $hDlg1     # the save window is the NEXT dialog
    if ($hSave -eq [IntPtr]::Zero) { Fail 'report-save' 'save-dialog-not-found' }
    [RP.U]::WDisarm()
    Emit 'report-printer' 'ok' ("via={0} printer='Microsoft Print to PDF' selvia={1} ch={2} list='{3}' default='{4}'" -f $printerVia, $selVia, $listInfo.ch, $listNames, $defName)
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
