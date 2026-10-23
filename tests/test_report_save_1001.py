"""Twenty-second batch -- save-step dual legs + success-branch record.

Twenty-first shot proved both legacy legs dead on Win11:

1. ``GetDlgItem(hSave, 1001)`` returns NULL -- the filename Edit sits four
   levels deep (DUIViewWndClassName -> DirectUIHWND -> FloatNotifySink ->
   ComboBox -> Edit) and GetDlgItem only walks DIRECT children.
2. The ComboBox UIA search sees nothing -- Win11 hides it inside DirectUI;
   the tree only exposes FileNameControlHost (a Pane) wrapping Edit aid=1001,
   and aid=1001 also appears in the address bar (parent-chain disambiguation).

The save step now tries: UIA parent-chain leg -> Win32 five-hop dive leg ->
legacy direct lookup, each hop tagged in ``$saveHop`` and carried on both
the Fail line and the save ok line -- the record says WHICH leg filled it.
"""

from __future__ import annotations

from pathlib import Path

TEXT = (Path(__file__).resolve().parents[1] / "src" / "executor" / "uia" / "report.ps1").read_text(
    encoding="utf-8"
)


def test_dual_legs_precede_the_fail() -> None:
    """Twenty-second shape: UIA host-chain leg, Win32 five-hop dive leg, then
    the direct lookup -- all BEFORE the Fail, each tagged in $saveHop.
    """
    host_leg = TEXT.index("FileNameControlHost')")  # UIA parent-chain leg
    dive_leg = TEXT.index("'DUIViewWndClassName'")  # Win32 dive leg
    direct_leg = TEXT.index("GetDlgItem($hSave, 1001)")  # legacy third leg
    fail = TEXT.index("file-name-combo-not-found hop={0}")
    assert host_leg < dive_leg < direct_leg < fail, "leg order broken"
    # the five-hop skeleton must appear in measured order (searched WITHIN
    # the dive block -- 'ComboBox'/'Edit' appear earlier in the file too)
    hops = [
        "'DUIViewWndClassName'",
        "'DirectUIHWND'",
        "'FloatNotifySink'",
        "'ComboBox'",
        "'Edit'",
    ]
    dive_region = TEXT[dive_leg:]
    positions = [dive_region.index(h) for h in hops]
    assert positions == sorted(positions), "dive skeleton order broken"
    # the original Fail line itself must survive (both legs empty = loud fail)
    assert TEXT.count("file-name-combo-not-found") == 1, "Fail line duplicated"
    # hop carrier initialized before the legs
    assert "$saveHop = 'init'" in TEXT
    # the save ok line carries the hop too -- record of which leg filled it
    ok_line = [ln for ln in TEXT.splitlines() if "Emit 'report-save' 'ok'" in ln]
    assert len(ok_line) == 1 and "hop={1}" in ok_line[0], "save ok missing hop"
    assert "file-name-combo-not-found hop={0}" in TEXT, "fail missing hop tag"


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
