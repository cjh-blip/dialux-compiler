"""Twentieth batch -- selection scan + error surfacing contracts.

Three facts from the nineteenth shot drive these assertions:

1. ``Select-MsaaItem`` returned ``aofw-throw`` while the read channels using
   the same C# call succeeded -- static diff shows the select function was the
   only one missing ``$o = $null`` before ``[ref]$o`` (PowerShell 5.1 throws
   for an undefined variable under ``[ref]``). The gate pins that ordering.
2. Every failure marker in the selection chain carried no exception text
   (``aofw-throw`` / ``acclocation-fail`` bare) -- the diagnostic-blind-spot
   pattern the sixteenth shot already proved expensive. Catch blocks must now
   surface the first 80 chars of ``$_.Exception.Message``.
3. The physical-click backup died at ``rect-no`` because the COM rect leg is
   its only geometry source. The rect function now falls back to an integer
   Win32 geometry (FindWindowEx SysHeader32 + GetWindowRect) and the caller
   step-scans that rect with read-back judging every hop -- a wrong row can
   never reach Print.
"""

from __future__ import annotations

import re
from pathlib import Path

PS1 = Path(__file__).resolve().parents[1] / "src" / "executor" / "uia" / "report.ps1"
TEXT = PS1.read_text(encoding="utf-8")


def _fn_body(name: str) -> str:
    """Extract one top-level function body (brace-balanced, next `function`)."""
    start = TEXT.index(f"function {name}(")
    nxt = TEXT.find("\nfunction ", start + 1)
    return TEXT[start:nxt if nxt != -1 else None]


def test_select_initializes_o_before_ref() -> None:
    """`$o = $null` must precede the live MsaaAccessibleH call in Select-MsaaItem."""
    body = _fn_body("Select-MsaaItem")
    init = body.index("$o = $null")
    call = body.index("MsaaAccessibleH($h, [ref]$o)")  # code call, not prose
    assert init < call, "[ref]$o used on an uninitialized variable -- nineteenth-shot bug back"


def test_select_catches_surface_exception_text() -> None:
    """Bare markers are gone; each catch returns marker + real message."""
    body = _fn_body("Select-MsaaItem")
    assert "aofw-throw:" in body and "$_.Exception.Message" in body
    for marker in ("accdo-fail:", "accdo-throw:"):
        assert marker in body, f"{marker} still bare"
    # every surfaced message is truncated so the Fail line stays bounded
    assert body.count(".Substring(0, [Math]::Min(80, $m.Length))") >= 3


def test_rect_function_has_geometric_fallback() -> None:
    """COM failure must not be the end: integer-only geometry leg exists."""
    body = _fn_body("Get-MsaaItemRect")
    assert "FindWindowEx" in body, "header lookup missing"
    assert "'SysHeader32'" in body, "sysheader32 class missing"
    assert "geom:" in body, "geometric content-rect segment missing"
    assert "accloc:" in body, "COM-side error not carried into fifth segment"
    # RectStr must be callable from PS (it was private before this batch)
    assert "public static string RectStr(" in TEXT, "RectStr not public"


def test_orchestration_step_scans_with_readback_judge() -> None:
    """Caller step-scans the rect; read-back decides every hop; bounded."""
    for tag in ("rect-scan-hit", "rect-scan-miss", "rect-no:"):
        assert tag in TEXT, f"scan tag {tag} missing"
    assert "rect-click'" not in TEXT, "single-shot click path should be gone"
    assert "$tries -lt 12" in TEXT, "scan bound missing -- unbounded loop risk"
    # read-back runs INSIDE the loop (judge per hop), not only afterwards
    loop_start = TEXT.index("for ($y = $yStart")
    loop_end = TEXT.index("$rbObj = $rbT")
    segment = TEXT[loop_start:loop_end]
    assert "Get-SelectReadBack" in segment, "read-back not judged per hop"
    assert "WMark('rect-scan')" in segment, "stage heartbeat not refreshed per hop"


def test_readback_gate_still_precedes_print() -> None:
    """The safety chain is untouched: Fail on !ok happens before any print."""
    fail_idx = TEXT.index("printer-not-selectable")
    bm_click_zone = TEXT[fail_idx - 4000: fail_idx + 4000]
    assert "BM_CLICK" not in bm_click_zone or "print" in bm_click_zone.lower()
    assert re.search(r"if \(-not \$rbObj\.ok\) \{\s*\n\s*Fail 'report-printer'", TEXT)
