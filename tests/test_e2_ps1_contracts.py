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
    via=clipboard 必须是代码真会走到的取值（回执抓到过『代码里不存在』）。

    注（2026-10-21 第三枪点4④）：`filename-duplicated` 现码**不可达**——
    attach 在 dialux_driver.ps1:173 的存在性检查先拦，:386 的闸只认旧版
    双 paste，而现行码已是单目标 paste；要样本需回归双 paste 版的测试
    夹具。记在这里免得后人以为漏验。
    """
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

def test_report_ps1_fourth_way_scan_gate():
    """第八批（第七枪 modebar 根因）：主路换第四路——模式栏同行
    ElementFromPoint 横扫（「报表」词优先、「导出」次之，char 码运行时拼）
    → 点击（Invoke/中心/像素三级）→ **过闸唯一判据＝print_btn**（只在报表
    页存在，四枪证据）；旧 tab-name 路降为 legacy 记录不再动作（根因＝
    ResultMode TabItem 视觉标签就是计算元件页，选它=切错页）；点后读回
    双路四态保留为现场；扫描找不到则带命中清单人话失败，不盲点。
    第九批（第八枪行级根因）：聚合先按 centerY 聚类成行、行选双层判据、
    几何只取选中行，两层都空→modebar-row-empty 不退全量；+320 余量保留。"""
    t = _src(REPORT_PS1)
    # 第四路四要素
    assert "FromPoint" in t, "命中测试横扫（信任像素不信任 id/名字）"
    assert "0x62A5" in t and "0x8868" in t, "『报表』词 char 码运行时拼"
    assert "0x5BFC" in t and "0x51FA" in t, "『导出』次选词 char 码"
    assert "modebar-scan" in t, "via 标识（含 scan-miss 变体）"
    assert "hits=" in t, "扫描命中清单进现场（miss 也带回看见了什么）"
    assert "legacy=" in t, "旧 tab-name 路降级为记录性字段"
    assert "$printBtn -ne 1" in t, "过闸唯一判据＝print_btn"
    assert "tab-name-resultmode" in t, "legacy 记录仍标命中趟次"
    # 旧主路必须不再动作（入口 acted 链与重选重试整体移除）
    assert "report-entry-neither-invoke-nor-select" not in t, "入口 Select 动作链已移除"
    assert "report-entry-not-found" not in t, "legacy 匹配失败不再硬停（非致命记录）"
    assert "ScrollItemIntoView" not in t, "对 ResultMode 的重选/重试已随根因移除"
    assert "$selIsTarget" not in t, "旧名字过闸变量已退役（谓词只有 print_btn）"
    # 证据字段延续（现场不丢）
    assert "IsSelected" in t
    assert "report-mode-not-confirmed" in t
    assert t.index("report-mode-not-confirmed") < t.index("Emit 'report-mode' 'ok'"), (
        "失败必须在 report-mode ok 之前")
    assert "selected=" in t and "readback=" in t
    assert "function Esc(" in t, "现场含中文，必须有 ASCII 转义"
    assert "TreeScope]::Ancestors" in t, "容器仍从 $mode 祖先解析（no-entry/err 进现场）"
    assert "target_selected=" in t and "target_pat=" in t
    assert "crect=" in t and "coff=" in t and "read_err=" in t
    assert "print_btn=" in t and "anc=" in t and "tfind=" in t
    assert "'null'" in t and "'na'" in t
    assert "= '?'" not in t, "四态闭集不许 ? 哨兵"
    assert "'?unreadable'" not in t, "名字字段同口径"
    assert "$targetNow" in t, "target 重定位保留为只读证据"
    # ---- 第九批（第八枪行级根因）：行聚类 + 行选双层判据 ----
    # 探针铁证：ModeSelectionTabControl 盖整个工作区，23 TabItem＝左16＋右3
    # ＋模式栏4；旧码 22 项求均值 midY=381 扫错行。修＝先按 centerY 聚类
    # 成行，再选一行、几何只取该行；行选两层都空→人话失败，不退全量扫描。
    block = t[t.index("ROW PICK"):t.index("for ($sx = $scanX0")]
    # 行聚类段存在（认代码结构不认行号）
    assert "Sort-Object -Property Cy" in block, "先按 centerY 排序再分组"
    assert "-le 8.0" in block, "centerY 聚类容差 +-8"
    # 行选双层判据段存在
    assert "-match 'ResultMode'" in block, "判据①：Name 命中 ResultMode 的那一行"
    assert "'InteractionModes" not in block, (
        "行选过滤不许用前缀匹配——四栏项只有一项带前缀，纯前缀匹配会只剩一行")
    assert "Count -lt 2" in block, "判据②：TabItem 数 >=2 过滤"
    assert "Descending = $true" in block, "判据②：横向跨度作次序"
    # 新失败码在场 + rows= 诊断（AGG 降为行集合摘要）
    assert "modebar-row-empty" in block, "两层都空的人话失败码在"
    assert "rows=" in block and "n={0}" in block, "失败带 n= 与每行 centerY:条数"
    # +320 结构余量过滤后必须保留（导出/报表/品牌库 UIA 无元素）
    assert "+ 320" in block, "+320 结构余量在选中行的几何里"
    # 负断言：空行集合必须 Fail 在扫描之前，绝不退回全量扫描
    assert t.index("modebar-row-empty") < t.index("for ($sx = $scanX0"), (
        "行选失败必须先于扫描 Fail")
    assert "$midY += $r4.Y" not in t, "全量聚合求 midY 的旧码不许复活"
    assert "$pick4 = $tabRow" not in t, "空行不许回退全量行集合（认 $pick4 几何）"
    assert "foreach ($itC in $pick4)" in block, "过滤后行内几何取自选中行"
    # 既有字段与失败码前缀照旧（跨枪可比性）
    assert "modebar-scan-miss hits='" in t
    assert "legacy={1} print_btn={2} rows=" in t, "scan-miss 尾追 rows= 不破旧字段"
    assert "print_btn=1 legacy={4} tfind={5} rows=" in t, "ok 场景带回 rows=/行几何"
    # 失败码不预设结论（三种 Fail 都查）
    fail_lines = [ln for ln in t.splitlines()
                  if ("report-mode-not-confirmed" in ln or "modebar-scan-miss" in ln
                      or "modebar-row-empty" in ln)]
    assert fail_lines, "至少一种人话失败码"
    for fl in fail_lines:
        for word in ("bounce", "revert", "switched-back"):
            assert word not in fl.lower(), f"失败码预设了回切结论：{word}"


def test_report_ps1_printer_step_win32_channel():
    r"""第十批（第九枪 printer 死因，两采闭环）：打印对话框 UIA 树 30 Pane、
    打印机列表 FolderView 零子项 → 旧 `$txt1 -match 打印机名` 结构上必不命中、
    UIA combo 选择路不可达，全部死在 unclassified-dialog。改法：
    - 分类走实测加速键（按钮 1 '&P'=打印对话框；'&S'/'\.pdf'=保存窗，先于
      任何打印机话术排除保存窗——它自己的文件列表也是 FolderView）；
    - 选择走 Win32 列表消息（E2 同型对话框 Win32 读到过列表内容），UIA 30 Pane
      文本保留为 ui= 证据字段；-PrinterComboId 仍是有值即硬停的逃生舱；
    - 辅路＝只读默认打印机恰为 PDF 直接点打印（GetDefaultPrinter，永不写系统设置）；
    - 过闸＝打印框消失＋保存窗出现才 Emit ok（点了不算）；
    - 失败码：unclassified-dialog 旧码保留（无信号 else 支），新码带 Win32 现场，
      不盲点不绕闸。"""
    t = _src(REPORT_PS1)
    i0 = t.index("# ------------------------------------- 3) print dialog")
    i1 = t.index("# ------------------------------------------------------- 4) save dialog")
    block = t[i0:i1]
    # 分类：实测加速键（'&P' 打印 / '&S' 保存 / '.pdf' 保存窗兜底）
    assert "'&P'" in block, "打印对话框分类＝按钮 1 加速键 &P（实测 打印(&P)）"
    assert "'&S'" in block, "保存窗分类＝&S（实测 保存(&S)）"
    assert r"'\.pdf'" in block, "保存窗 .pdf 信号仍在（按钮文本读不到时的兜底）"
    # 选择：Win32 列表通道（读/选/回读）＋现场
    assert "function Read-W32PrinterList" in t, "列表读取函数在场"
    for fn in ("ChildScene", "Get-KidClassSummary", "ListChannel", "ListRead"):
        assert fn in t, f"Win32 助手 {fn} 不在"
    assert "Read-W32PrinterList" in block
    assert "ListSelect" in block and "ListSelText" in block, "选中后必须回读"
    assert "GetDefaultPrinterName" in t, "辅路：默认打印机只读查询"
    assert "Set-DefaultPrinter" not in t and "SetDefaultPrinter" not in t, (
        "系统设置不许碰（只读查询有，写入无）")
    # 点打印前必须完成回读确认（回读在 BM_CLICK 之前）
    assert block.index("ListSelText") < block.index("0x00F5"), "先回读后点打印"
    # 过闸：打印框消失 + 保存窗出现，才 Emit ok（点了不算）
    assert "print-dialog-still-open" in block, "打印框消失是闸的一半"
    i_wait = block.index("$hSave = Wait-Dialog $DialogTimeoutMs $hDlg1")
    i_fail_save = block.index("Fail 'report-save' 'save-dialog-not-found'")
    i_ok = block.rindex("Emit 'report-printer' 'ok'")
    assert i_wait < i_fail_save < i_ok, "保存窗出现必须先于 printer ok"
    # 失败码与证据（新码带现场，旧码保留可回溯）
    for code in ("printer-list-win32-unreadable", "printer-not-in-win32-list",
                 "printer-not-selectable-use-PrinterComboId",
                 "unclassified-dialog", "print-dialog-not-found",
                 "print-button-not-found"):
        assert code in block, f"失败码 {code} 不在打印步块内"
    assert "printer-combo-id-not-found" in t, "-PrinterComboId 有值即硬停的旧码保留"
    assert "win32='" in block and "default='" in block, "失败带 Win32 现场＋默认打印机"
    assert "ui='" in block, "UIA 30 Pane 文本仍是证据字段"
    # 旧 UIA combo 选择路必须已删（第九枪已证结构上不可达的死路）
    assert "$comboEl" not in block, "旧 UIA combo 路已随根因移除"
    assert "ExpandCollapsePattern" not in block, "combo 展开选择同删"


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
    """动作内放点路第一层（回执活A 4b/4c 钉死；第六批换轨记档）：
    第五枪结构普查证实底栏区无同名 ListItem、全窗唯一同名元素＝左栏
    72×72 图块（rect=123,478，Select 生效、点4/5 经此路建成）——代码
    路径正确、旧『底栏』措辞已改，**FAIL 码名保留 bottombar 一词**保
    跨枪信号连续，断言与注释按图块口径。"""
    t = _src(UGR_PS1)
    assert "ControlType]::ListItem" in t, "元素在 ListItem 层找（实测＝左栏图块）"
    assert "SelectionItemPattern" in t, "类型切换走 SelectionItem"
    assert "bottombar-point-item-not-found" in t, "找不到要带候选现场"
    assert "bottombar-point-not-selected" in t, "切型也要读回（Select 假阳性同病）"
    assert "0x8BA1" in t and "0x7B97" in t and "0x70B9" in t, (
        "『计算点』指纹必须 char 码运行时拼（纯 ASCII 契约）")
    # 第三枪两败的根因修：子串匹配命中结果摘要行「计算点 1」＋缓存句柄 stale
    assert "-eq $ptName" in t, "必须等值匹配（子串会命中带序号的结果摘要行）"
    assert "RuntimeId" in t, "复读按 RuntimeId 重定位（Select 重建树，旧 RCW 读抛异常被吞＝恒 false）"
    assert "nameHit" in t, "树重建后按等值名回退重定位"
    assert "rect=" in t and "err=" in t, "失败带位置与读异常计数现场"
    # 第五批（第四枪证据：源头读出 rid='' read='' err=0，null 被 [string] 转成空）
    assert "GetCurrentPattern([System.Windows.Automation.SelectionItemPattern]::Pattern).Current.IsSelected" in t, (
        "pattern 路并联读：属性路与 pattern 路任一 True 才过闸")
    assert "'null'" in t, "四态记法：空值不得再伪装成 False"


def test_ugr_ps1_handles_results_invalid_modal():
    """《结果将无效》模态（第三枪推翻 #32770 假设）：WPF 覆盖层无独立
    HWND、拿不到 IDYES(6)——按钮＝UIA AutomationId Yes/No 成对（同排），
    Invoke Yes 后复读必须消失；孤立 Yes＝不认识的结构不点、带现场失败；
    置入后与落点后各收一次。"""
    t = _src(UGR_PS1)
    assert "function Find-ResultInvalidModal" in t
    assert "'Yes'" in t and "'No'" in t, "按钮指纹＝AutomationId（ASCII，不再 char 码）"
    assert "0x7ED3" not in t, "CJK 字符码指纹已随 #32770 假设废弃"
    assert "'#32770'" not in t, "无 HWND：Win32 窗口枚举路必须已删"
    assert "GetDlgItem($h, 6)" not in t, "IDYES(6)+BM_CLICK 实测走不通，必须已删"
    assert "InvokePattern" in t, "确认走 UIA Invoke"
    assert "unexpected-modal" in t, "孤立 Yes/结构不符不猜，带原文现场失败"
    assert "result-invalid-modal-not-dismissed" in t, "收后要复读确认真收了"
    assert t.count("Confirm-ResultInvalidModal") >= 3, "定义＋置入后＋落点后两处调用"


def test_ugr_ps1_expands_position_section():
    """动作内放点路第二因（4b/4c）＋第六批时序修（第五枪反差：码报
    missing 而跑后现场『定位』栏三字段在场）：展开+读取改带 attempts 的
    重试循环，失败带 attempts/loc/逐字段现场；选中态不作闸（四/五枪已证
    不可靠），时序靠 attempts 盖。"""
    t = _src(UGR_PS1)
    assert "0x5B9A" in t and "0x4F4D" in t, "『定位』指纹必须 char 码运行时拼"
    assert "$locName" in t
    assert "ExpandCollapsePattern" in t
    assert "position-controls-missing-after-point" in t, "兑底失败码不许删（信号权威在用）"
    assert "attempts=" in t, "时序重试必须带次数进现场（分辨时序 vs 结构）"
    assert "loc=" in t and "x=" in t, "逐字段与展开状态进现场"
    # 第七批（第六枪 pos_probe 铁证）：真身 id 改名
    assert "ById 'Positioning_X'" in t, "定位字段真身 id＝Positioning_X/Y/Z（vecAid_hits=0）"
    assert "ById 'PositionVectorControl_X'" not in t, "旧 id 必须已从代码路径移除"
