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


# ------------------------------------------------------- 5) 2026-10-20 复核轮回执改点
# 真机首验 0 过，主病灶＝上一批自己的剪贴板双发；以下把七条改点钉成不回退闸。

def test_driver_ps1_pastes_exactly_one_target():
    """① WM_PASTE 只发一次：双发→同一编辑区写两遍→path×2→文件名无效。"""
    t = _src(DRIVER_PS1)
    assert t.count("0x0302") == 1, (
        f"driver 的 WM_PASTE 必须只发一个目标，实测 {t.count('0x0302')} 处")
    assert "$pasteTarget" in t, "目标选择（内层 Edit 优先）必须显式写出来"
    lum = _src(LUMINAIRE_PS1)
    assert lum.count("0x0302") == 1, (
        f"luminaire 的 WM_PASTE 必须只发一个目标，实测 {lum.count('0x0302')} 处")


def test_driver_ps1_readback_gate_needs_the_real_path():
    """①＋③ 读回双闸（轮询 Win32 ＋ UIA Name），且只认带 $full 的值；
    via=clipboard 必须是代码真会走到的取值（回执抓到过『代码里不存在』）。"""
    t = _src(DRIVER_PS1)
    assert "Field-Has" in t, "读回只认带路径的值，非空不算"
    assert "Read-FieldUiA" in t, "第二闸（UIA Name）缺失＝Win32 读空就误判降级"
    assert "for ($gi = 0" in t, "单次读回（250ms）就是 2026-10-20 误判降级的成因"
    assert "$via = 'clipboard'" in t, "via=clipboard 要有真实取值路径支撑"
    assert "filename-duplicated" in t, "重复路径必须点键前拦下"
    lum = _src(LUMINAIRE_PS1)
    assert "Count-LumPath" in lum and "Read-LumFieldUiA" in lum


def test_driver_ps1_click_is_bounded_and_modal_checked():
    """② BM_CLICK 必须有超时（无超时就是 300/240/240s 三轮挂死的成因），
    超时后扫错误模态框、人话失败并把它收掉。"""
    t = _src(DRIVER_PS1)
    assert "SendMessageTimeout" in t, "点击无超时＝遇模态框整动作不返回"
    assert "out IntPtr" in t, "P/Invoke 声明必须完整（否则 Add-Type 编不过）"
    assert "bm-click-timeout-or-hung" in t
    assert "error-modal-after-open" in t, "错误模态框要能被认出来并报成人话"
    assert "Find-ErrorModal" in t
    assert "[void][Win.U]::SendMessage($hOpen, $BM_CLICK" not in t, "旧的无超时点键必须已移除"


def test_report_ps1_matches_result_mode_tab_name():
    """④ 报表入口：实测 20 个 TabItem 无一含 Report，模式页签 Name＝
    `…InteractionModes.Results.ResultMode`（序位 19 随工具页签漂）。
    两趟匹配：Report 优先、再 InteractionModes.*Result，工具页签不许赢。"""
    t = _src(REPORT_PS1)
    assert "'Report|report'" in t, "第一趟（原判据）不许删"
    assert "'InteractionModes.*Result'" in t, "第二趟（实测 Name）必须在"
    assert "tab-name-resultmode" in t, "走哪一趟要能从 detail 里看出来"


def test_ugr_ps1_checks_enabled_before_invoke():
    """⑤ 计算按钮先判 IsEnabled 再 Invoke（实测 enabled=False 甩裸
    calculation-invoke-failed）；场景缺计算点的定性写在注释里、待真机定，
    不在这里改语义。"""
    t = _src(UGR_PS1)
    assert "IsEnabled" in t, "Invoke 前缺 IsEnabled 判定"
    assert "calc-button-disabled" in t, "禁用态要报成人话码"
    assert "calculation-invoke-failed" in t, "原异常兜底仍在（IsEnabled 读不到时）"
    assert "pending the next real-machine round" in t, "场景定性挂待定，不武断当 bug 改"


# ------------------------------------------- 6) 第三批（2026-10-20 第二枪回执 → 五棒落码）
# 仍是静态契约：本机无 pwsh，能否真跑通归 Windows 第三枪。

def test_report_ps1_select_confirm_gate_precedes_ok():
    """项5 Select 确认闸：Select 报 ok 但模式没落报表页（本枪两败根，
    print-entry-not-found-use-PrintMenuId）。读回选中页签名含 ResultMode
    才 Emit ok；假阳性带现场人话失败，且不预设「回切」结论。"""
    t = _src(REPORT_PS1)
    assert "IsSelected" in t, "缺读回选中页签"
    assert "$selName -notmatch 'ResultMode'" in t, "选中页签名不含 ResultMode 不放行"
    assert "report-mode-not-confirmed" in t, "假阳性缺专属人话码"
    assert t.index("report-mode-not-confirmed") < t.index("Emit 'report-mode' 'ok'"), (
        "确认闸必须在 report-mode ok 之前")
    assert "selected=" in t and "readback=" in t, "失败要带现场（选中名＋读回路径＋命中趟次）"
    assert "function Esc(" in t, "现场含中文，必须有 ASCII 转义"
    fail_line = [ln for ln in t.splitlines() if "report-mode-not-confirmed" in ln][0]
    for word in ("bounce", "revert", "switched-back"):
        assert word not in fail_line.lower(), f"失败码预设了回切结论：{word}"


def test_ugr_ps1_recalc_completion_waits_for_value_emergence():
    """重算假完成沿（4d 附带发现，via=result sec=12 返回时面板全 '-'）：
    res_before 有值时，完成必须先观察到清场（dashSeen＝行在值没了的读，
    空读不算），再等值真从 '-' 变出；旧的『一变即完成』判据必须已删。"""
    t = _src(UGR_PS1)
    assert "$hadValue" in t and "$dashSeen" in t, "两段新状态位缺失"
    assert r"\d+(?:\.\d+)?\s*lx" in t, "值判据（数字紧邻 lx）必须显式写出来"
    assert "resNow -ne $resBefore -and $sw.Elapsed" not in t, "旧的一变即完成判据还在"
    assert "dash_seen=" in t, "超时现场要带清场观察位"
    assert "second-gun receipt (4d" in t, "重算场景的来龙去脉要写在注释里"


def test_ugr_ps1_places_point_switching_bottombar_type():
    """动作内放点路第一层（回执活A 4b/4c 钉死）：aid_NewPointCalculationObject
    是通用『置入计算元件』——底栏类型不切，点击永远建面、
    PositionVectorControl 永不出现；切型同样要读回确认。"""
    t = _src(UGR_PS1)
    assert "ControlType]::ListItem" in t, "底栏条目在 ListItem 层找"
    assert "SelectionItemPattern" in t, "类型切换走 SelectionItem"
    assert "bottombar-point-item-not-found" in t, "找不到要带候选现场"
    assert "bottombar-point-not-selected" in t, "切型也要读回（Select 假阳性同病）"
    assert "0x8BA1" in t and "0x7B97" in t and "0x70B9" in t, (
        "『计算点』指纹必须 char 码运行时拼（纯 ASCII 契约）")


def test_ugr_ps1_handles_results_invalid_modal():
    """《结果将无效，是否继续操作？》模态（4b 截住视口点击）：置入后与
    落点后各收一次；指纹 char 码构建、IDYES(6) 确认、收没收到要复读、
    不认识的模态带原文失败不猜。"""
    t = _src(UGR_PS1)
    assert "function Find-ResultInvalidModal" in t
    assert "0x7ED3" in t and "0x679C" in t and "0x5C06" in t, (
        "模态指纹（结果将无效）必须 char 码运行时拼")
    assert "GetDlgItem($h, 6)" in t, "IDYES(6) 才是确认钮"
    assert "unexpected-modal" in t, "不认识的模态不猜、带原文失败"
    assert "result-invalid-modal-not-dismissed" in t, "确认后要复读确认真收了"
    assert t.count("Confirm-ResultInvalidModal") >= 3, "定义＋置入后＋落点后两处调用"


def test_ugr_ps1_expands_position_section():
    """动作内放点路第二因（4b/4c）：属性面板『定位』栏默认折叠，
    字段不展开不暴露；展开失败仍有 position-controls 闸兑底带现场。"""
    t = _src(UGR_PS1)
    assert "0x5B9A" in t and "0x4F4D" in t, "『定位』指纹必须 char 码运行时拼"
    assert "$locName" in t
    assert "ExpandCollapsePattern" in t
    assert "position-controls-missing-after-point" in t, "兑底失败码不许删（信号权威在用）"
