"""Quote-parity gates for report.ps1 -- the eighteenth shot's blind spot.

The eighteenth batch shipped a file-level parse-time ParserError
(``report.ps1:834`` -- one missing closing single quote in a ``('...' -f ...)``
template) while every static gate stayed green: ASCII scan, bracket pairing
``{}[]()`` and 328 contract tests never look at quotes. These gates close
that hole with two cheap invariants verified against the real file shape:

* **Gate A** -- every *code* line (line comments and trailing comments
  stripped) must carry an even number of single quotes, unless it matches an
  explicitly exempted cross-string shape (e.g. ``-replace "'", ''`` where one
  double-quoted string and one empty single-quoted string legitimately sum
  to an odd count on a single line). Comment prose (``shot's``) is stripped
  with the comment, so the 38 odd comment lines in the file do not trip it.
* **Gate B** -- the file-wide double-quote count must be even (paired
  strings plus the ``@"``/``"@`` here-string pair).

Both invariants were fitted to this file and then NEGATIVELY VERIFIED against
the pre-fix HEAD revision (see test_quote_gate_catches_prefx_shape): the old
line 834 shape must trip Gate A, the repaired shape must pass.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PS1 = REPO / "src" / "executor" / "uia" / "report.ps1"

# Cross-string shapes that legitimately produce an odd single-quote count on
# ONE line. Matched against content (never line numbers, which drift).
ODD_EXEMPT_PATTERNS = (
    re.compile(r'''-replace\s+"'"'''),  # -replace "'", ''  (strip-quote idiom)
)

# Strip a trailing comment that starts at whitespace + # or // . A '#' glued
# to a quote (e.g. '#32770') has no preceding space, so string literals that
# contain controller class names survive.
_TRAIL_COMMENT = re.compile(r"\s+(?:#|//).*$")


def _code_lines(text: str) -> list[str]:
    out = []
    for raw in text.splitlines():
        line = _TRAIL_COMMENT.sub("", raw).strip()
        if not line or line.startswith(("#", "//")):
            continue
        out.append(line)
    return out


def _odd_single_quote_lines(text: str) -> list[str]:
    bad = []
    for line in _code_lines(text):
        if line.count("'") % 2 == 0:
            continue
        if any(p.search(line) for p in ODD_EXEMPT_PATTERNS):
            continue
        bad.append(line)
    return bad


def test_gate_a_no_odd_single_quote_code_lines() -> None:
    """Every code line has paired single quotes (or a listed exemption)."""
    text = PS1.read_text(encoding="utf-8")
    bad = _odd_single_quote_lines(text)
    assert not bad, "odd single-quote code line(s) -- unclosed string risk:\n" + "\n".join(
        f"  {line}" for line in bad
    )


def test_gate_b_global_double_quote_count_even() -> None:
    """File-wide double quotes pair up (strings + here-string open/close)."""
    text = PS1.read_text(encoding="utf-8")
    n = text.count('"')
    assert n % 2 == 0, f"double-quote count {n} is odd -- unpaired '\"'"


def test_exemption_shape_still_present() -> None:
    """The exempted idiom exists exactly where expected -- the list is alive."""
    text = PS1.read_text(encoding="utf-8")
    hits = [ln for ln in _code_lines(text) if any(p.search(ln) for p in ODD_EXEMPT_PATTERNS)]
    assert hits, "no exempted cross-string line found -- update ODD_EXEMPT_PATTERNS"


def test_quote_gate_catches_prefx_shape() -> None:
    """NEGATIVE VERIFICATION with an embedded pre-fix sample.

    The original eighteenth-shot line (five single quotes, unclosed format
    template) is spliced into the current file text; Gate A must flag it,
    while the working tree itself stays clean. No git dependency -- the gate
    is proven against the shape, not against a revision id.
    """
    good = PS1.read_text(encoding="utf-8")
    fixed = "('idx={0} name=''{1}''' -f $idx, $name)"
    broken = "('idx={0} name=''{1}'' -f $idx, $name)"
    assert fixed in good, "fixed template missing -- gate lost its live target"
    bad = good.replace(fixed, broken, 1)
    flagged = _odd_single_quote_lines(bad)
    assert any("' -f" in line for line in flagged), "broken shape must trip Gate A"
    assert not _odd_single_quote_lines(good), "working tree must be clean under Gate A"
