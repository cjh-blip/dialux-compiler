# -*- coding: utf-8 -*-
"""第十八批（2026-10-23 · 第十七枪读取层首通）：雷A 参数构造＋雷B 两空间口径。

第十七枪：读取层首通（msaa cnt=4、三台打印机名齐、lvint count=3）；选中层
浮出 `Object[]→IntPtr` 参数转换错（format 括号内逗号＝数组构造＝单实参）；
names 4 行含 DefView 容器节点、lv 3 行＝两索引空间（acc＝names 循环源，
lv＝LVM 系），容器 offset=1。

三组断言：
1. 雷A：`([IntPtr]{0}, {1})` 括号逗号零命中；空格分隔形态在场；目标三函数
   双参签名匹配调用形态。
2. 雷B：fixture——本枪原文 4 行名单+count=3 → offset=1、PDF 的 acc 索引=2、
   尾 3 行 lv 视图含 PDF 且其 lv 索引=1（两口径都钉）；码中换算式与
   rowmismatch 互证在场。
3. 双确认：Get-MsaaItemName（lv→acc 换算 +offset）＋ Get-SelectReadBack
   （range 判＋name==PDF 判）＋三处回读点全走 helper。

⚠ 无 pwsh：真机行为（Select 走 accChild、读回换算、双确认过闸）在第十八枪，
本文件为静态契约＋离线 fixture。
"""
from __future__ import annotations

from pathlib import Path

REPORT_PS1 = Path(__file__).resolve().parent.parent / "src" / "executor" / "uia" / "report.ps1"

# 第十七枪 probe 原文（fixture，抄自回执点2）
PILOT_NAMES = "文件夹视图;Brother HL-1218W Printer;Microsoft Print to PDF;OneNote (Desktop)".split(";")
PILOT_LV_COUNT = 3


def _src() -> str:
    return REPORT_PS1.read_text(encoding="utf-8")


def test_leia_paren_comma_gone_space_separated_form_present():
    """组1-雷A：括号逗号构造零命中；空格分隔形态五处+helper；目标签名双参。"""
    t = _src()
    assert "([IntPtr]{0}, {1})" not in t, "括号内逗号（Object[] 构造）必须零命中"
    # 空格分隔调用形态（五处选中调用 + helper 的名字读回调用）
    space_forms = [
        "'Select-MsaaItem ([IntPtr]{0}) {1}'",
        "'Select-UiaItem ([IntPtr]{0}) {1}'",
        "'Get-MsaaItemRect ([IntPtr]{0}) {1}'",
        "'Get-MsaaItemName ([IntPtr]{0}) {1}'",
    ]
    for f in space_forms:
        assert f in t, f"空格分隔形态缺失: {f}"
    assert t.count("'Select-MsaaItem ([IntPtr]{0}) {1}'") == 2, "msaa-select 主路+备路两处"
    assert t.count("'Select-UiaItem ([IntPtr]{0}) {1}'") == 2, "uia-select 主路+备路两处"
    # 目标函数双参签名（与两实参调用匹配）
    assert "function Select-MsaaItem([IntPtr]$h, [int]$i)" in t
    assert "function Get-MsaaItemRect([IntPtr]$h, [int]$i)" in t
    assert "function Select-UiaItem([IntPtr]$h, [int]$i)" in t
    assert "function Get-MsaaItemName([IntPtr]$h, [int]$i)" in t


def test_two_index_spaces_fixture_and_conversion_math():
    """组2-雷B fixture（第十七枪原文）：4 行名单+count=3 → offset=1；PDF 的
    acc 索引=2（names 空间，Select 用它）、尾 3 行 lv 视图含 PDF 且其 lv
    索引=1（LVM 空间，回读/滚动用它）——两口径都钉，off-by-one 无处可躲。"""
    # acc 空间：names 顺序＝accChild 循环顺序
    pick_acc = PILOT_NAMES.index("Microsoft Print to PDF")
    assert pick_acc == 2, "PDF 在 acc/names 空间的索引＝2（Select 传它）"
    # 容器 offset 与 lv 空间
    offset = len(PILOT_NAMES) - PILOT_LV_COUNT
    assert offset == 1, "容器节点数＝1"
    rows = PILOT_NAMES[-PILOT_LV_COUNT:]
    assert len(rows) == PILOT_LV_COUNT, "尾部 lvCount 个＝行视图（长度互证）"
    pick_lv = rows.index("Microsoft Print to PDF")
    assert pick_lv == 1, "PDF 的 lv 索引＝1（不是 2——off-by-one 钉死）"
    assert pick_acc - offset == pick_lv, "acc - offset == lv 的换算自洽"
    # 码中的对应物
    t = _src()
    assert "$offset = @($listInfo.names).Count - $lvCount" in t, "offset 换算式"
    assert "$pickLv = $pickIdx - $offset" in t, "EnsureVisible 的 acc→lv 换算"
    assert "($idx + $offset)" in t, "回读 idx(lv)→acc 换算"
    assert "Select-Object -Last $lvCount" in t, "尾部行视图过滤"
    assert "rowmismatch=" in t, "互证失败的现场码（既有前缀尾追）"
    assert "$lvCount -gt 0" in t, "lvCount 守卫（edit 兑底路径无 lvcount）"
    # lvcount 字段来源（读取层返回）
    assert "lvcount = $lvN" in t and "$lvN = 0" in t, "lvcount 初始化与两处 return"


def test_double_confirm_readback_gate():
    """组3：双确认制——range 判＋选中行文本==PDF（lv→acc 换算后经 msaa 读回）；
    三个回读点全走 helper；helper 的调用点零直读 ListSelIndex（读回只在一处）。"""
    t = _src()
    assert "function Get-SelectReadBack(" in t, "双确认 helper 在场"
    assert "function Get-MsaaItemName(" in t, "acc 空间读名函数在场"
    # range 判 + out-of-range 现场
    assert "$idx -ge $lvCount" in t and "out-of-range" in t, "选中 idx 必须落在 [0, lvCount)"
    # 文本判据
    assert "$name -notmatch 'Microsoft Print to PDF'" in t, "选中行文本必须＝PDF"
    assert "'msaa-name'" in t, "读名走 L1 同构超时"
    # 回读点全走 helper（主路/备路/扫描逐 hop＋扫描保底/rect-no 分支）
    assert t.count("Get-SelectReadBack $listInfo.ctrl $listInfo.ch $lvCount $offset") == 5, (
        "五处回读点（主路/备路/扫描循环内/扫描保底/rect-no）全走双确认")
    # 判据本体：最终 gate 用 rbObj.ok 而非裸 idx 比对
    assert "if (-not $rbObj.ok) {" in t, "终局 gate＝双确认结果"
    assert "$selIdx -ne $pickIdx" not in t, "旧的裸索引比对判据必须零命中"
    # msaaSelBody 装入读名函数
    assert "(Get-FnDef Get-MsaaItemName)" in t, "msaaSelBody 组装含 Get-MsaaItemName"
