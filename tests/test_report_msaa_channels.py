# -*- coding: utf-8 -*-
"""第十五批（2026-10-23 · 第十四枪崩溃 3/3 坐实）：崩因禁令与读取换靶契约。

机制（第十四枪事件日志＋我方静态坐实）：跨进程 SendMessage 不封送 lParam——
LVM_GETITEMTEXT 的 LVITEM*/LVM_SETITEMSTATE 的 LVITEM*/LVM_GETITEMRECT 的
RECT* 到达目标进程后指向**它自己**地址空间的同值地址：Comctl32 解引用
→ AV(c0000005, 模块偏移 0x70cc6)，或恰好有映射读到垃圾、我方 SafeSend 对
垂死线程 3s 超时回空（e10 的 n=3+三个空串 = 崩溃连带中间态）。
WM_GETTEXT 是例外：user32 对它做跨进程封送（GetWindowText 建于其上），合法。

三组断言：
1. 裸指针消息零命中（十六进制调用字面 + 宿主方法名双管；符号名允许出现在
   禁令注释里——注释是记录，调用才是禁令）；
2. 三通道与超时地板（MSAA/UIA/WM_GETTEXT 读、MSAA accDoDefaultAction 与
   UIA SelectionItem 选、accLocation 矩形备路；每条 COM 路套 L1 同构
   runspace 天花板，stage= 新值尾追既有超时码）；
3. E2 考古结论钉在注释里（git show 309fbb4：E2 版无列表读取，三台名字是
   Windows 方现场探测——'同法成功 vs 必崩'矛盾不存在）。

⚠ 无 pwsh：MSAA/UIA/WM_GETTEXT 三通道全部只能真机首验（第十五枪），
本文件为静态契约（形态/顺序/字段/禁令），不冒充行为验证。
"""
from __future__ import annotations

from pathlib import Path

REPORT_PS1 = Path(__file__).resolve().parent.parent / "src" / "executor" / "uia" / "report.ps1"


def _src() -> str:
    return REPORT_PS1.read_text(encoding="utf-8")


def test_no_raw_pointer_messages_anywhere():
    """组1：跨进程裸指针消息零命中（派单件2/件3 零容忍清单）＋整数型安全
    消息保留面。十六进制字面=真实调用形态（本仓 ps1 的消息全用字面+尾注
    符号名），宿主方法名=结构级。"""
    t = _src()
    forbidden = {
        "0x1073": "LVM_GETITEMTEXTW",
        "0x102D": "LVM_GETITEMTEXTA",
        "0x102A": "LVM_SETITEMSTATE",
        "0x100E": "LVM_GETITEMRECT",
        "0x0148": "CB_GETLBTEXT",
        "0x0189": "LB_GETTEXT",
    }
    for lit, name in forbidden.items():
        assert lit not in t, f"{name}（{lit}）必须零命中——跨进程裸指针，第十四枪崩因"
    # 载体宿主与结构（注释也不得复活）
    for sym in ("LVITEMW", "ListItemByChannel", "ListReadInfo", "ListSelText",
                "ListRectClick", "ClickItemRect", "AnsiFrom"):
        assert sym not in t, f"裸读取/选择宿主 {sym} 应已随崩因删除"
    # 整数型安全消息（counts / cur-sel / next-item / ensure-visible / BM_CLICK）
    # 与系统封送的 WM_GETTEXT 必须在场——删除面只许落在指针消息上
    for safe in ("0x1004", "0x100C", "0x0146", "0x018B", "0x00F5", "0x100F", "0x000D"):
        assert safe in t, f"整数型/系统封送消息 {safe} 应保留"


def test_three_read_channels_and_their_timeouts():
    """组2-读：MSAA 主读（oleacc、COM 封送）＋UIA 单锚深读＋WM_GETTEXT
    Edit 扫；两条 COM 读通道各套 L1 同构 runspace 天花板（超时仍产
    printer-step-hang-timeout，stage= 新值尾追）；edit 通道靠 WndText 的
    3s SafeSend 界不套 runspace（声明在场）。"""
    t = _src()
    for fn in ("Read-MsaaList", "Read-UiaList", "Read-EditTexts",
               "ConvertFrom-ChanLine", "Get-FnDef"):
        assert f"function {fn}" in t, f"通道函数 {fn} 不在"
    # oleacc 入口与 OBJID_CLIENT/IID_IDispatch 组合
    assert "AccessibleObjectFromWindow" in t, "oleacc 入口"
    assert "0xFFFFFFFC" in t, "OBJID_CLIENT（-4）"
    assert 'new Guid("00020400-0000-0000-C000-000000000046")' in t, "IID_IDispatch（PS 晚绑定）"
    # 每通道 stage 名与超时参数
    for stage in ("'msaa-list-read'", "'uia-list-read'", "'msaa-select'",
                  "'uia-select'", "'msaa-rect'"):
        assert stage in t, f"通道超时 stage {stage} 不在"
    # 读取循环内 msaa/uia 均经 Invoke-StageTimeout（10s），且 WMark 标在前
    i_ms = t.index("Invoke-StageTimeout 'msaa-list-read'")
    assert t.index("WMark('msaa-list-read')") < i_ms, "WMark 先于 msaa 调用"
    assert t.index("Invoke-StageTimeout 'uia-list-read'") > i_ms, "uia 读在其后"
    assert "10000" in t, "COM 读通道 10s 天花板"
    # edit 通道的封送声明（不套 runspace 的理由写在注释里）
    assert "user32 marshals\n    # WM_GETTEXT" in t or "user32 marshals across processes by design" in t, (
        "WM_GETTEXT 系统封送的取舍说明在场")


def test_selection_channels_and_rect_backup():
    """组2-选：lv 主路 COM 双路由（read=msaa→accDoDefaultAction，
    read=uia→SelectionItem.Select），交替备路，矩形备路＝accLocation
    屏幕坐标＋物理点击（前台仍只夹在备路标记与备路点击之间）；回读＝
    整数索引 ListSelIndex（0x100C 安全消息）。cb/lb 整数消息路保留。"""
    t = _src()
    for fn in ("Select-MsaaItem", "Select-UiaItem", "Get-MsaaItemRect",
               "ConvertFrom-RectLine"):
        assert f"function {fn}" in t, f"选择/矩形函数 {fn} 不在"
    assert "accDoDefaultAction" in t, "MSAA 默认动作＝选择"
    assert "SelectionItemPattern" in t, "UIA SelectionItem.Select 路"
    assert "accLocation" in t, "矩形来源＝COM（替代 LVM_GETITEMRECT）"
    # 主路分流与整数回读（十八批：回读集中到双确认 helper，直调移入其中）
    assert "$listInfo.read -eq 'msaa'" in t and "$listInfo.read -eq 'uia'" in t, "按 read 通道分流"
    assert "[RP.U]::ListSelIndex($ctrl, $ch)" in t, "回读走整数索引（helper 内）"
    assert "Get-SelectReadBack" in t, "回读经双确认 helper"
    assert "never a precondition of the COM routes" in t, "主路无前台声明"
    # cb/lb 整数消息选择仍在（lv 分流声明）
    assert 'return "lv-via-com"' in t
    assert "0x014E" in t and "0x0186" in t, "CB/LB_SETCURSEL 整数路保留"
    # 备路前台序（组2 既有断言之外的结构点：EnsureVisible 在点击前）
    assert "ListEnsureVisible" in t
    i_fg = t.index("WMark('rect-backup-foreground')")
    i_ev = t.index("ListEnsureVisible($listInfo.ctrl", i_fg)
    i_ps = t.index("SetCursorPos", i_ev)
    assert i_fg < i_ev < i_ps, "前台→ensure-visible→物理点击的序"


def test_e2_archaeology_and_crash_attribution_in_comments():
    """组3：E2 考古与崩因归属钉在注释——防后人再拿"E2 同法成功"当矛盾材料，
    也防把崩因记回 wParam（wParam 修复随裸读取退役，e10 悬案归崩溃连带）。"""
    t = _src()
    assert "E2 ARCHAEOLOGY" in t, "E2 考古注释段在场"
    assert "E2 build had NO printer-list reading" in t, "E2 无列表读取的结论"
    assert "Windows-side operator's own probe" in t, "三台名字归因＝Windows 方现场探测"
    assert "crashed DIALux 3/3" in t, "崩因 3/3 归因注释在场"
    assert "cross-process SendMessage does NOT marshal lParam" in t, "机制句在场"
    # 新读取通道的 wire 形态（runspace 只回字符串——hashtable 过不了通道）
    assert "ok~cnt~err~name1|name2" in t, "通道 wire 形态文档在场"
