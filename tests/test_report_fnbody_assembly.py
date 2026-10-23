# -*- coding: utf-8 -*-
"""第十七批（2026-10-23 · 第十六枪根因定罪 Get-FnDef 缺括号）：三支修法契约。

第十六枪根因链（三处 ParseException 双跑逐字复现）：
- 支1 本体＝Get-FnDef 裸拼 ScriptBlock.ToString()（外层 {} 已剥、param 在内）
  → 'function Name param(...)'＝声明无主体，parse 错停在 param；
- 支2 第二形态＝Get-DlgUiText 手拼点自带 ({IntPtr}$h){} 与内层 param 重复冲突；
- 支3 信息位次＝probe 400 窗在 err 膨胀后挤掉 lvint/edit（实测 401/400）。

三组断言：
1. 拼接形态：format 串必须带 {{ }} 字面包回主体；python 模拟拼接产物必须
   是 'function <名> { … }' 且花括号配对（解析前的静态形态）；旧裸拼零命中。
2. 手拼零残留：全部 fnBody 组装走 Get-FnDef（含 L1421 改道），手拼形态零命中。
3. 信息位次：probe 窗 1000（400/200 零命中）、err 160 保留、edit 段在候选
   循环之前、lvint trace 在 msaa err 段之前（结构序）。

⚠ 无 pwsh：拼接产物能否真过 PowerShell 解析只能真机验（第十七枪），
本文件给的是解析前的静态形态契约（与派单一致：正则或括号计数）。
"""
from __future__ import annotations

import re
from pathlib import Path

REPORT_PS1 = Path(__file__).resolve().parent.parent / "src" / "executor" / "uia" / "report.ps1"


def _src() -> str:
    return REPORT_PS1.read_text(encoding="utf-8")


def test_get_fndef_wraps_braces_format():
    """组1-本体：format 串用 {{ }} 把裸体包回 function 主体；旧裸拼零命中。"""
    t = _src()
    assert "return ('function {0} {{ {1} }}' -f $n, [string]$c.ScriptBlock)" in t, (
        "Get-FnDef 必须用 {{ }} 字面花括号包主体（name 无参数括号、param 全在体内）")
    assert "('function {0} ' -f $n) + [string]" not in t, "旧的裸拼形态必须零命中"
    assert "'function Name { param(...) ... }'" in t, "目标形态的注释在场"


def test_assembled_body_static_shape_simulation():
    """组1-产物：模拟 Get-FnDef 拼接——按源码里的 format 模式把一个带 param
    与花括号的假体拼成运行时文本，断言三件事：首段 'function NAME {'、
    名字不带参数括号、全串花括号计数配对（解析前的静态可验形态）。"""
    t = _src()
    m = re.search(r"return \('function \{0\} \{\{ \{1\} \}\}' -f \$n, \[string\]\$c\.ScriptBlock\)", t)
    assert m, "format 串必须逐字匹配 'function {0} {{ {1} }}'"
    # 模拟运行时产物（ScriptBlock.ToString() 的规范化形态：param 在内、外层剥）
    fake_body = "param($acc, $child) {\n    $r = @{}\n    if ($r) { return $child }\n    return $acc\n}"
    name = "Get-AccName"
    assembled = "function %s { %s }" % (name, fake_body)   # 与 format 串语义等价
    assert assembled.startswith("function Get-AccName {"), "产物首段＝function <名> {"
    assert not re.match(r"function \S+\(", assembled.split("{", 1)[0]), "名字不带参数括号（参数只在内层 param）"
    assert assembled.count("{") == assembled.count("}"), "花括号计数配对"
    assert "param($acc, $child)" in assembled, "内层 param 保留在主体内"


def test_all_fnbodies_route_through_get_fndef():
    """组2：手拼零残留——全部 fnBody 组装点走 Get-FnDef（含改道的
    Get-DlgUiText），全文件 [string](Get-Command 手拼零命中。"""
    t = _src()
    assert "[string](Get-Command" not in t, "手拼 ScriptBlock 必须零残留"
    assert "('function Get-DlgUiText([IntPtr]$h) {' " not in t, "旧手拼 wrapper 必须零命中"
    for fn in ("Get-FnDef Get-AccName", "Get-FnDef Read-UiaList",
               "Get-FnDef Get-DlgUiText", "Get-FnDef Select-MsaaItem",
               "Get-FnDef Select-UiaItem", "Get-FnDef Read-MsaaList"):
        assert fn in t, f"组装点未走 Get-FnDef: {fn}"
    # 三处错误文本（Get-AccName / Read-UiaList / Get-DlgUiText）的载体同修
    assert t.count("function {0} {{ {1} }}") == 1, "统一修复点唯一"


def test_probe_window_and_field_order():
    """组3：probe 窗 1000、超时窗 600、err 160 不动；edit 段在候选循环之前、
    lvint trace 在 err 膨胀的 msaa 行之前（结构序＝挤不掉的保证）。"""
    t = _src()
    assert t.count("Substring(0, 1000)") == 2, "两处 probe 截断都在 1000"
    assert "Substring(0, 400)" not in t, "400 旧窗零命中"
    assert "Min(600," in t and "Min(200," not in t, "超时 trace 窗 600（200 零命中）"
    assert t.count("Substring(0, 160)") == 2, "err 每段 160 截断保留两处"
    # edit 执行在候选循环之前（trace 头）
    i_edit = t.index("[RP.U]::WMark('edit-text-read')")
    i_loop = t.index("foreach ($cd in ($cands | Sort-Object -Property pri))")
    assert i_edit < i_loop, "edit 段必须在候选循环之前（trace 头，截断挤不掉）"
    # lvint trace 在 msaa err 行之前（同候选内）
    i_lv = t.index('lvint=count:{0} cur:{1}')
    i_msaa_line = t.index("msaa={2} cnt={3} err=")
    assert i_lv < i_msaa_line, "lvint 先于 msaa err 行（截断先丢 msaa 尾）"
    # lvint 只 trace 一次（挪位后不得残留第二条追加）
    assert t.count('$traces += ("{0}@{1} {2}"') == 1, "lvint trace 行唯一"
    # edit 的 PDF 兑底判定仍在（只搬执行不改判据）
    assert "$read0 = 'edit'" in t
