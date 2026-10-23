"""Twenty-first batch -- save-step Win11 bypass + success-branch record.

Twentieth shot proved two facts that drive these contracts:

1. The Win11 save-as tree has NO ComboBox (0 hits; FileNameControlHost is a
   Pane wrapping Edit aid=1001), so the legacy ComboBox search always landed
   on ``file-name-combo-not-found``. GetDlgItem(hSave, 1001) must be tried
   BEFORE the Fail -- value-parameter handle plumbing, cross-process safe.
2. The success line of report-printer carried no read-back record (Fail-only
   fields), forcing inference (lv=1/acc=2) instead of an actual sample. The
   ok detail now carries rb text, resolved index and the rect line.
"""

from __future__ import annotations

from pathlib import Path

TEXT = (Path(__file__).resolve().parents[1] / "src" / "executor" / "uia" / "report.ps1").read_text(
    encoding="utf-8"
)


def test_1001_bypass_precedes_the_fail() -> None:
    """GetDlgItem(1001) attempt must come before the combo-not-found Fail."""
    bypass = TEXT.index("edit-1001")
    fail = TEXT.index("Fail 'report-save' 'file-name-combo-not-found'")
    assert bypass < fail, "1001 bypass placed after the Fail -- dead code"
    assert "GetDlgItem($hSave, 1001)" in TEXT, "direct aid=1001 lookup missing"
    # the original Fail line itself must survive (bypass is a fallback, not a
    # replacement -- a save window without 1001 must still fail loudly)
    assert TEXT.count("Fail 'report-save' 'file-name-combo-not-found'") == 1


def test_success_detail_carries_record_fields() -> None:
    """report-printer ok line carries rb / idx / geom -- record, not inference.

    Two legit ok emits exist (the default-is-PDF short circuit and the main
    chain); the record fields ride the main-chain one.
    """
    ok_lines = [ln for ln in TEXT.splitlines() if "Emit 'report-printer' 'ok'" in ln]
    assert len(ok_lines) == 2, "short-circuit + main-chain emits expected"
    line = next(ln for ln in ok_lines if "via={0}" in ln)
    for field in ("rb='{6}'", "idx={7}", "geom='{8}'"):
        assert field in line, f"success detail missing {field}"
    # the three carriers are computed defensively before the Emit
    assert "$rbIdx = -1" in TEXT and "$rbTxt = ''" in TEXT and "$geomTxt = ''" in TEXT


def test_save_button_keeps_measured_default() -> None:
    """E2-measured save = GetDlgItem(1) stays as the default path."""
    assert "GetDlgItem($hSave, 1)" in TEXT, "measured save-button default gone"
    assert "BM_CLICK" in TEXT, "save click path gone"
