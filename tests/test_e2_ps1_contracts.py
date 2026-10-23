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
SAVEAS_PROBE = UIA / "saveas_probe.ps1"
E2_PS1 = (DRIVER_PS1, LUMINAIRE_PS1, UGR_PS1, REPORT_PS1, SAVEAS_PROBE)


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
    第十一批新增的 saveas_probe 同为新代码，同样零容忍；
    luminaire.ps1 带 **150 字节历史中文注释**（266-267 行，非本批引入、
    且它在真机上跑通过），本批不许再涨——新注释一律英文。
    """
    for p in (DRIVER_PS1, UGR_PS1, REPORT_PS1, SAVEAS_PROBE):
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
        "-BreadCrumbPath",
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
      不盲点不绕闸。
    十五批换血（第十四枪崩溃 3/3 后崩因坐实）：读取/选中从裸 LVM 消息换
    MSAA/UIA/WM_GETTEXT 三通道（COM 与系统封送跨进程安全），回读改整数
    索引；分类/失败码/双闸/ui 字段与本测试的结构断言全部保留。"""
    t = _src(REPORT_PS1)
    i0 = t.index("# ------------------------------------- 3) print dialog")
    i1 = t.index("# ------------------------------------------------------- 4) save dialog")
    block = t[i0:i1]
    # 分类：实测加速键（'&P' 打印 / '&S' 保存 / '.pdf' 保存窗兜底）
    assert "'&P'" in block, "打印对话框分类＝按钮 1 加速键 &P（实测 打印(&P)）"
    assert "'&S'" in block, "保存窗分类＝&S（实测 保存(&S)）"
    assert r"'\.pdf'" in block, "保存窗 .pdf 信号仍在（按钮文本读不到时的兜底）"
    # 选择：读取换三通道（MSAA 主/UIA 深/WM_GETTEXT Edit）＋回读整数索引
    assert "function Read-W32PrinterList" in t, "列表读取函数在场"
    for fn in ("ChildScene", "Get-KidClassSummary", "ListChannel",
               "Read-MsaaList", "Read-UiaList", "Read-EditTexts"):
        assert fn in t, f"Win32 助手/通道函数 {fn} 不在"
    assert "Read-W32PrinterList" in block
    assert "ListSelIndex" in block and "ListSelect" in block, "选中后必须回读（整数索引，消息安全）"
    assert "GetDefaultPrinterName" in t, "辅路：默认打印机只读查询"
    assert "Set-DefaultPrinter" not in t and "SetDefaultPrinter" not in t, (
        "系统设置不许碰（只读查询有，写入无）")
    # 点打印前必须完成回读确认（回读在 BM_CLICK 之前）
    assert block.index("ListSelIndex") < block.index("0x00F5"), "先回读后点打印"
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


def test_report_ps1_list_text_read_and_probe():
    r"""第十五批（第十四枪崩溃 3/3 坐实崩因）：裸 LVM 读取＝崩因，文本读取
    换靶 MSAA/UIA/WM_GETTEXT 三通道；判据与过闸一行不动：
    - 机制：跨进程 SendMessage 不封送 lParam——LVM_GETITEMTEXT 的 LVITEM*
      到达目标进程是它自己地址空间的同值地址 → 解引用 AV（Comctl32
      0x70cc6）或垃圾，我方 3s 超时回空——e10 的 n=3+三空串与 3/3 崩溃
      在此闭环；裸指针消息零命中（全文件负断言见 test_report_msaa_channels）；
    - 通道 A MSAA（oleacc，COM 封送）主读、B UIA 单锚深读（第九枪的零
      子项是主树走法所致，单锚是未验形状）、C WM_GETTEXT（系统封送）Edit
      扫，三通道现场全进 probe（cnt/err/first）；
    - E2 考古（git show 309fbb4）：E2 版无列表读取（其 id 表写明 'ps1 缺
      整步'），三台名字是 Windows 方现场探测——'同法成功 vs 必崩'的矛盾
      不存在，注释已更正；
    - 容器定位不按类型猜（Static 标题 char 码＋几何只排序不排除、pin 优先）
      与读类消息 SafeSend 防挂、BM_CLICK 动作保持原样；
    - 失败码现场字段按实际（btn1/probe/ch）照旧。"""
    t = _src(REPORT_PS1)
    # 三通道构件在场（读与选）
    for tok in ("MsaaAccessible", "AccessibleObjectFromWindow", "accChildCount",
                "accDoDefaultAction", "accLocation", "WndText", "0x000D"):
        assert tok in t, f"三通道构件 {tok} 不在"
    for fn in ("Read-MsaaList", "Read-UiaList", "Read-EditTexts",
               "Select-MsaaItem", "Select-UiaItem", "Get-MsaaItemRect"):
        assert f"function {fn}" in t, f"通道函数 {fn} 不在"
    # 旧裸读取载体全删（消息级零命中在 test_report_msaa_channels）
    for gone in ("ListReadInfo", "ListItemByChannel", "LVITEMW", "ListSelText"):
        assert gone not in t, f"裸读取载体 {gone} 应已删除"
    # 取证字段
    assert "probe='" in t, "probe 字段进现场"
    for ln in ([x for x in t.splitlines() if "printer-not-in-win32-list" in x]
               + [x for x in t.splitlines() if "via=win32-list ch=" in x]):
        assert "btn1=" in ln and "probe=" in ln, f"字段补齐漏码：{ln[:60]}"
        assert "ch=" in ln, f"ch 字段漏：{ln[:60]}"
    # caption 锚（char 码拼，文件保 ASCII）＋几何只排序不排除
    for code in ("0x9009", "0x62E9", "0x673A"):
        assert code in t, f"选择打印机标题 char 码 {code} 不在"
    assert "Test-ListAdjToCaption" in t
    assert "NEVER excludes" in t or "never excludes" in t, "几何只排序不排除"
    assert "GetWindowRect" in t, "rect 进 ChildScene 供几何锚"
    # 读消息防挂；动作消息不换
    assert "SendMessageTimeout" in t and "SafeSend" in t
    assert "[void][RP.U]::SendMessage($hPrint, 0x00F5" in t, (
        "BM_CLICK 动作消息保持原样（只读消息才超时）")
    # 判据不动：选中→回读→双闸由第十批既有断言守（回读在点击前、过闸序）


def test_saveas_probe_is_readonly():
    r"""件2（第十一批点名，不实施换线）：另存为候选路线的只读属性 dump。
    只取材不换线——换线是方案级、归统筹挂卡；本测试把“只读”钉成负断言：
    脚本里不许出现任何点击/调用/选中动作，输出必须是 UTF-8 声明后的属性行。"""
    src = _src(SAVEAS_PROBE)
    raw = SAVEAS_PROBE.read_bytes()
    bad = [b for b in raw if b >= 128]
    assert not bad, f"saveas_probe.ps1 含 {len(bad)} 个非 ASCII 字节"
    assert "ButtonPrintDocument" in src, "锚＝实测报表工具栏打印按钮 id"
    assert "BoundingRectangle" in src and "AutomationId" in src, "属性字段齐全"
    assert "OutputEncoding" in src, "输出编码声明（Name 为本地化中文）"
    assert "BTN name=" in src and "ANCHOR aid=" in src, "输出行格式在场"
    # 只读铁证：零动作
    for tok in (".Invoke(", "Invoke()", "mouse_event", "SetCursorPos",
                "0x00F5", "BM_CLICK", "PostMessage", "SendKeys",
                "LVM_SETITEMSTATE"):
        assert tok not in src, f"只读探针不得出现 {tok}"


def test_report_ps1_step_watchdog_and_stage_timeouts():
    r"""第十二批组1（第十一枪挂死 2/2、600s 看门狗前无码面）：死区必须换成码
    面——阻塞场景必须 Fail 在内层超时码 printer-step-hang-timeout，绝不允许
    再还一片 600s 死区。双层结构：L2 步级 watchdog（120s 纯 .NET timer 线程
    直写 STEP 行 + Environment.Exit，回调不跑 PS 代码）；L1 runspace 天花板
    盖住无界跨进程调用（UIA 树/spooler）；列表探测循环 15s 总预算；根因三嫌
    疑不预设，哪条挂都要出码。"""
    t = _src(REPORT_PS1)
    # L2 watchdog：布防在步入口（Wait-Dialog 之前）、预算 120s << 600s
    assert "[RP.U]::WArm(120000, 'report-printer')" in t, "步入口布防与预算值"
    assert t.index("[RP.U]::WArm(") < t.index("$hDlg1 = Wait-Dialog $DialogTimeoutMs ([IntPtr]::Zero)"), (
        "watchdog 必须在 printer 步入口（含 Wait-Dialog）之前布防")
    assert "600000" not in t, "不许把 shell 预算当自己的上限"
    # 回调纯 .NET：码面模板 + 强退（回调里禁止 PS 代码——不合法线程）
    assert "printer-step-hang-timeout stage=watchdog last=" in t, "watchdog 码面字段"
    for fld in ("elapsed=", "fg='", "target=0x", "budget="):
        assert fld in t, f"超时码定位字段 {fld} 不在"
    assert "Environment.Exit(1)" in t, "回调强退（不靠 PS exit）"
    assert "Console.Out.Flush" in t, "码面 flush 后才退"
    # 每个成功出口前 disarm（两处 ok：.pdf 直达支 + 双闸支）
    assert t.count("[RP.U]::WDisarm()") == 2, "两处 ok 前各一次 Disarm"
    assert t.index("[RP.U]::WDisarm()") < t.index("Emit 'report-printer' 'ok'"), "首个 Disarm 先于首个 ok"
    assert t.rindex("[RP.U]::WDisarm()") < t.rindex("Emit 'report-printer' 'ok'"), "双闸支 Disarm 先于其 ok"
    # L1：无界跨进程调用的 runspace 天花板 + 超时出同名码
    assert t.count("Invoke-StageTimeout") >= 3, "定义 + UIA + spooler 两个调用点"
    assert "AsyncWaitHandle.WaitOne" in t, "天花板本体"
    assert "'uia-dialog-text'" in t and "'default-printer'" in t, "L1 两个 stage 名"
    assert "stage=win32-list elapsed=" in t, "列表探测总预算超限先于看门狗出码"
    assert "15000" in t, "单次列表探测预算 15s（settle 重读各自有界）"
    assert "$ps.Stop()" not in t, "超时路径禁 Stop（停一个卡住的调用本身会卡）"
    # stage 标记：watchdog 的 last= 分诊靠它们（十五批：printer 步新增通道
    # 细分标记，msaa-list-read 为首代表）
    for mk in ("WMark('wait-dialog')", "WMark('uia-dialog-text')", "WMark('win32-list-read')",
               "WMark('printer-select-main')", "WMark('msaa-list-read')",
               "WMark('print-click')", "WMark('gate-save-appear')"):
        assert mk in t, f"stage 标记 {mk} 不在"


def test_report_ps1_message_first_foreground_backup_only():
    r"""第十二批组2（打嫌疑①），第十五批换轨：lv 主路从 LVM_SETITEMSTATE
    消息换成 COM（MSAA accDoDefaultAction / UIA SelectionItem）——因为消息
    本身就是崩因（LVITEM* lParam 跨进程不封送，与读取同机制）；C# ListSelect
    只剩 cb/lb 整数分支，矩形备路的 RECT 指针消息（LVM_GETITEMRECT）同灭，
    换 accLocation 屏幕坐标＋物理点击。前台纪律不变：主路零前台，前台只夹在
    备路标记与备路点击之间；AttachThreadInput 开头组合保留（时间线已证非本
    挂点、删共享代码波及 mode/print——红灯不碰）。"""
    t = _src(REPORT_PS1)
    # C# 分工：ListSelect=cb/lb 整数消息 + lv 分流声明（lv 走 COM）
    sel_blk = t[t.index("public static string ListSelect"):t.index("public static string ListEnsureVisible")]
    assert "0x102A" not in sel_blk, "lv 消息选中已灭（LVITEM*＝崩因同款）"
    assert 'return "lv-via-com"' in sel_blk, "lv 分流声明（caller 走 MSAA/UIA）"
    assert "SetCursorPos" not in sel_blk, "主路选中不得动鼠标"
    assert "ListRectClick" not in t and "ClickItemRect" not in t, "RECT 指针备路已灭"
    # PS 主路：前台零依赖——标记锁死前台只夹在备路标记与备路点击之间
    assert t.index("[RP.U]::WMark('printer-select-main')") < t.index("SetForegroundWindow($hDlg1)"), (
        "主路选中标记必须先于任何前台操作")
    i_fg = t.index("[RP.U]::WMark('rect-backup-foreground')")
    i_set = t.index("SetForegroundWindow($hDlg1)", i_fg)
    i_click = t.index("SetCursorPos", t.index("[RP.U]::WMark('rect-backup-click')"))
    assert i_fg < i_set < i_click, "前台只出现在备路标记与备路点击之间"
    assert "never a precondition of the COM routes" in t, "主路无前台的声明在场"
    # gate 块（BM_CLICK 所在）零前台：打印按钮走消息投递
    g0 = t.index("if ($printerOk) {")
    g1 = t.index("Emit 'report-printer' 'ok'", g0)
    gate = t[g0:g1]
    assert "0x00F5" in gate, "BM_CLICK 在 gate 块"
    assert "SetForegroundWindow" not in gate, "gate 块不得依赖前台"
    # 开头组合保留（共享代码不删——时间线论证见记账）
    assert "AttachThreadInput" in t, "开头前台组合保留，不波及 mode/print"
    assert t.count("SetForegroundWindow") == 3, "声明1＋开头1＋备路1，主路已移除"


def test_report_ps1_no_regression_of_batch_10_11_primitives():
    r"""第十二批组3，十五批数字换血：SafeSend 实数随裸读取删除降为 16
    （22 时代含 6 处裸消息发送——它们正是崩因，删除合法）；wParam/rc 断言
    换 COM 与整数索引原语；其余（settle/pinned/&P/+320/双闸/回读先于点击）
    照旧，既有测试同时全绿即为交叉验证。"""
    t = _src(REPORT_PS1)
    assert t.count("SafeSend(") >= 16, "SafeSend 封存（十五批删 6 裸发送后实数 16）"
    assert "Start-Sleep -Milliseconds 800" in t, "settle 只读重读保留"
    assert "printer-combo-id-not-found" in t, "pinned 有值即硬停保留"
    assert "'&P'" in t and "'&S'" in t, "实测加速键分类保留"
    assert "MsaaAccessible" in t and "ListSelIndex" in t, "读取/回读原语换 COM＋整数索引后仍在"
    assert "probe='" in t and "msaa=" in t, "probe 取证换三通道现场"
    assert "+ 320" in t, "+320 余量未碰（边界）"
    # 双闸时序（第十批断言的同一语义，本批插入 WMark/WDisarm 不得破序）
    i_wait = t.index("$hSave = Wait-Dialog $DialogTimeoutMs $hDlg1")
    i_fail_save = t.index("Fail 'report-save' 'save-dialog-not-found'")
    assert i_wait < i_fail_save < t.rindex("Emit 'report-printer' 'ok'"), "双闸时序不回归"
    # 回读在 BM_CLICK 之前（第十批原断言语义，块级断言在 printer_step 测）
    assert t.index("ListSelIndex") < t.index("0x00F5"), "先回读后点打印不回归"


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
