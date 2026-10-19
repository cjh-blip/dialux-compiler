# -*- coding: utf-8 -*-
"""E 阶段2 改码清单的静态契约（2026-10-19 回执 §三 五条落码后钉住）。

为什么是静态断言：**本机没有 pwsh**，PowerShell 的语法与真机行为在这里跑不了。
这些断言证明「改了什么还在、两边参数还对得上」；**能不能真跑通归 Windows 真机复核**
（回执 §一 的 5 个 ✗ 项就是下一轮复核清单）。
"""
from __future__ import annotations

import re
from pathlib import Path

UIA = Path(__file__).resolve().parent.parent / "src" / "executor" / "uia"
DRIVER_PS1 = UIA / "dialux_driver.ps1"
LUMINAIRE_PS1 = UIA / "luminaire.ps1"
UGR_PS1 = UIA / "ugr.ps1"
UGR_PY = UIA / "ugr.py"
REPORT_PS1 = UIA / "report.ps1"
REPORT_PY = UIA / "report.py"
E2_PS1 = (DRIVER_PS1, LUMINAIRE_PS1, UGR_PS1, REPORT_PS1)


def _src(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _param_block(p: Path) -> str:
    t = _src(p)
    m = re.search(r"param\((.*?)\n\)", t, re.S)
    assert m, f"{p.name} 没有 param 块"
    return m.group(1)


# ---------------------------------------------------------------- 0) 通用约束
def test_all_e2_ps1_are_pure_ascii():
    """PS 5.1 按 GBK 读无 BOM 的 .ps1：中文字在注释行外的任何位置都可能炸括号。

    本批判据分两档：driver/ugr/report 在 HEAD 就是纯 ASCII，必须继续为 0；
    luminaire.ps1 带 **150 字节历史中文注释**（266-267 行，非本批引入、
    且它在真机上跑通过），本批不许再涨——新注释一律英文。
    """
    for p in (DRIVER_PS1, UGR_PS1, REPORT_PS1):
        bad = [(i, b) for i, b in enumerate(p.read_bytes()) if b >= 128]
        assert not bad, f"{p.name} 含 {len(bad)} 个非 ASCII 字节，首个在偏移 {bad[0][0]}"
    lum_bad = sum(1 for b in LUMINAIRE_PS1.read_bytes() if b >= 128)
    assert lum_bad <= 150, f"luminaire.ps1 非 ASCII 从历史 150 涨到 {lum_bad}（新注释必须英文）"


# ---------------------------------------------------------------- 1) report.py ↔ report.ps1
def test_report_py_flags_are_all_declared_as_ps1_params():
    """回执抓到的实伤：`-PrinterComboId` 从动作层传进 ps1 会参数绑定错误。

    这条把「report.py 能发的每个 -Flag」与「report.ps1 声明的参数」双向钉死。
    """
    py = _src(REPORT_PY)
    expected = {
        "-PdfPath", "-ProcessName", "-WaitTimeoutMs",
        "-ReportMenuId", "-ReportTabIndex", "-PrintMenuId",
        "-PrinterComboId", "-SaveButtonId", "-FileNameId",
    }
    for flag in expected:
        assert f'"{flag}"' in py, f"report.py 不再发送 {flag}"
    params = set(re.findall(r"\[(?:string|int)\]\$(\w+)", _param_block(REPORT_PS1)))
    missing = {f for f in expected if f[1:] not in params}
    assert not missing, f"report.ps1 缺参数声明：{sorted(missing)}"


def test_report_ps1_printer_step_uses_measured_ids():
    """④ 打印步：实测 id 优先、打印机窗内选 PDF、报表入口 SelectionItem/序位。"""
    t = _src(REPORT_PS1)
    assert "ButtonPrintDocument" in t          # 实测打印入口 id（Print pattern 会歧义命中 ReportModePrint）
    assert "Microsoft Print to PDF" in t       # 窗内选打印机（系统默认打印机离机，边界内不动系统设置）
    assert "ModeSelectionTabControl" in t      # 报表入口所在容器
    assert "ReportTabIndex" in t               # 序位逃生舱（-1＝未测不用，不猜下标）
    assert "SelectionItemPattern" in t         # 入口只有 SelectionItem，Invoke 单打独斗必挂
    assert "unclassified-dialog" in t          # 分不清就不猜：带原文失败，逼下一轮标定


def test_report_ps1_wait_dialog_nullstring_and_pid_filter():
    """`Wait-Dialog` 的三处修：NullString、按 pid 过滤、能等第二个窗。"""
    t = _src(REPORT_PS1)
    body = t.split("function Wait-Dialog", 1)[1].split("\nfunction ", 1)[0]
    assert "[NullString]::Value" in body
    assert "'#32770', $null" not in t, "$null 会被编组程空串（同 dialux_driver 记过的坑）"
    assert "skipHwnd" in body and "$proc.Id" in body


def test_report_ps1_save_pastes_via_clipboard():
    """④ 保存窗：剪贴板粘贴（SetWindowText 读回不渲染）＋最上宽框定位＋读回闸。"""
    t = _src(REPORT_PS1)
    assert "0x0302" in t and "WM_PASTE" in t
    assert "Get-Clipboard" in t                # 用完还回用户的剪贴板
    assert "bestY" in t                        # 宽 ComboBox 中 T 最小者（实测 519 vs 546）
    assert "filename-fill-had-no-effect" in t  # 读回闸：空就不点保存


# ---------------------------------------------------------------- 2) ugr.ps1
def test_ugr_py_flags_are_all_declared_as_ps1_params():
    """③ 逃生舱双向：`-CalcButtonId` 这类键只在 py 侧有、ps1 没参数＝形同虚设。

    回执抓到过同型病（report 的 `-PrinterComboId`）；ugr 这次自己补的
    `-CalcButtonId` 不许再犯同一错。
    """
    py = _src(UGR_PY)
    expected = {"-UgrCheckId", "-StepId", "-RangeFromId", "-RangeToId",
                "-ResultId", "-CalcButtonId"}
    for flag in expected:
        assert f'"{flag}"' in py, f"ugr.py 不再发送 {flag}"
    params = set(re.findall(r"\[(?:string|int)\]\$(\w+)", _param_block(UGR_PS1)))
    missing = {f for f in expected if f[1:] not in params}
    assert not missing, f"ugr.ps1 缺参数声明：{sorted(missing)}"


def test_ugr_ps1_measured_ids_and_calc_escape():
    """③ 参数控件实测 id 先试、calc 按钮逃生舱、完成检测有兜底与现场。"""
    t = _src(UGR_PS1)
    for mid in ("StepSize_Ugr", "AngleRangeBegin_Ugr", "AngleRangeEnd_Ugr"):
        assert mid in t, f"实测参数控件 id {mid} 未进默认链"
    assert "CalcButtonId" in _param_block(UGR_PS1), "-CalcButtonId 逃生舱未声明"
    assert "$CalcButtonId" in t, "声明了却没用（键形同虚设）"
    assert "via=" in t                          # 完成信号走了 label 还是 result，回执里要看得见
    assert "res_before=" in t                   # 超时必须带现场，不甩裸 'calculation-timeout'


# ---------------------------------------------------------------- 3) dialux_driver.ps1
def test_driver_ps1_settled_requires_an_observable_change():
    """① settled 轮询：同名工程首拍即过的假通过要被堵死。"""
    t = _src(DRIVER_PS1)
    assert "titleBefore" in t and "treeBefore" in t
    assert "-ne $titleBefore" in t
    assert "title-unchanged-and-tree-unchanged" in t
    assert "Fail 'import-settled' 'title-unchanged'" not in t, "旧裸 Contains 判定必须已移除"
    assert "via=" in t                          # settledVia：title / tree 走的哪条要报出来


def test_driver_ps1_fill_pastes_and_fail_cleans():
    """① 填充换剪贴板（绕中文 IME）＋ Fail 路径补关对话框。"""
    t = _src(DRIVER_PS1)
    assert "0x0302" in t and "WM_PASTE" in t
    assert "filename-fill-had-no-effect" in t
    assert "settext-fallback" in t              # 读回为空才降级，不裸奔
    fail_body = t.split("function Fail(", 1)[1].split("\nfunction ", 1)[0]
    assert "Find-FileDialog" in fail_body, "Fail 路径不关对话框＝下一轮盲跑（回执根因③）"


# ---------------------------------------------------------------- 4) luminaire.ps1
def test_luminaire_ps1_pastes_absolute_path():
    """② 全路径粘贴导航（绕共享最近目录）＋开载后清窗＋轮询窗加宽。"""
    t = _src(LUMINAIRE_PS1)
    assert "Set-Clipboard" in t and "0x0302" in t
    assert "Cancel-FileDialogs }" in t, "BM_CLICK 开窗后要清残留（与 driver 同病）"
    assert "[int]$TimeoutMs = 30000" in t, "12s 轮询窗太窄（回执原话），已加宽"
    assert "target-not-in-dialog" in t          # 兜底路仍在：粘贴失败退回列表选择
