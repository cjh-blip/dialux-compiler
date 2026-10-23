# -*- coding: utf-8 -*-
"""第十六批（2026-10-23 · 第十五枪零崩溃铁证与三通道半通）：诊断可见性四件。

第十五枪事实：零崩溃（6 条 3 对 → 0）；MSAA/UIA 双通道 err='empty' 空手
（<100ms，非超时）＝ Invoke-StageTimeout 的 catch 把内层错吞成零输出——
自十二批 L1 存在起所有带 fnBody 的调用零输出（E14 ui='' 同病），这是诊断
盲点；通道C WM_GETTEXT 活着（edit=5 first='脱机'）＝跨进程封送可通。

四组断言：
1. 错误浮现（钥匙）：Streams.Error 首条/HadErrors/InitializationFailed/EndInvoke
   rethrow 四源并回，且以 4 段 wire（0~-1~msg~）返回；'empty' 只在真无错。
2. 嫌疑a：runspace 显式 STA（Open 前、Supports 守卫）。
3. 嫌疑b：HRESULT 进 err（MsaaAccessibleH＋hr=0x 形态三调用点）。
4. 件3：ListBox 整数身份探针（count/cur/双方言 lens）＋ lv 整数面进 probe。

⚠ 无 pwsh：错误浮现行为、STA 下 COM 行为、LB 消息方言只能真机首验
（第十六枪）；本文件为静态契约。
"""
from __future__ import annotations

from pathlib import Path

REPORT_PS1 = Path(__file__).resolve().parent.parent / "src" / "executor" / "uia" / "report.ps1"


def _src() -> str:
    return REPORT_PS1.read_text(encoding="utf-8")


def _stage_block(t: str) -> str:
    i0 = t.index("function Invoke-StageTimeout")
    i1 = t.index("function Get-KidClassSummary")
    return t[i0:i1]


def test_error_surface_in_invoke_stage_timeout():
    """组1（钥匙）：内层错误必须浮现——四个错误源全部判到、4 段 wire 返回、
    'empty'（裸 return ''）只在四源全空时可达；超时码面路径原样。"""
    t = _src()
    blk = _stage_block(t)
    # 四个错误源
    assert "$ps.EndInvoke($ih) } catch { $endErr" in blk, "EndInvoke rethrow 进 $endErr"
    assert "$ps.Streams.Error.Count -gt 0" in blk, "Streams.Error 首条必须查"
    assert ".Exception.Message" in blk, "取异常 Message 文本"
    assert "$ps.HadErrors" in blk, "HadErrors 兜底判"
    assert "$rs.InitializationFailed" in blk, "runspace 初始化失败判"
    # 优先级序：EndInvoke > stream > HadErrors > init
    i_end = blk.index("$endErr = \"$($_.Exception.Message)\"")
    i_stream = blk.index("$ps.Streams.Error.Count -gt 0")
    i_had = blk.index("$ps.HadErrors")
    i_init = blk.index("$rs.InitializationFailed")
    assert i_end < i_stream < i_had < i_init, "四源优先级序"
    # 4 段 wire 错误形态（读者可直接解析）
    assert "return ('0~-1~{0}~' -f $errTxt)" in blk, "错误以 4 段 wire 返回"
    assert "errTxt.Substring(0, 160)" in blk, "截断防爆"
    assert ".Replace('~', ' ').Replace('|', ' ')" in blk, "wire 分隔符清洗"
    # 裸 return '' 只在无错分支（结构序：errTxt 空判在 return '' 前）
    i_empty_check = blk.index("if ($errTxt -eq '') { return '' }")
    i_wire = blk.index("return ('0~-1~{0}~' -f $errTxt)")
    assert i_empty_check < i_wire, "无错才空；有错必带文本"
    assert blk.count("return ''") == 1, "裸空返回只有一处且在无错分支"
    # 超时码面路径原样（既有资产零改动）
    assert "printer-step-hang-timeout stage={0}" in blk, "超时码面原样"
    assert "AsyncWaitHandle.WaitOne" in blk, "天花板本体原样"
    # 有输出时保输出（wire 可解析优先，注释在场）
    assert "return [string]$out[0]" in blk, "正常路原样"


def test_runspace_apartment_sta_optin():
    """组2（嫌疑a）：COM 公寓亲和——Open 前显式 STA、Supports 守卫、异常吞；
    且布防位置在 CreateRunspace 与 Open 之间。"""
    t = _src()
    blk = _stage_block(t)
    assert "SupportsRunspaceApartmentState" in blk, "支持性守卫"
    assert "$rs.ApartmentState = [System.Threading.ApartmentState]::STA" in blk, "显式 STA"
    i_create = blk.index("[runspacefactory]::CreateRunspace()")
    i_sta = blk.index("$rs.ApartmentState =")
    i_open = blk.index("$rs.Open()")
    assert i_create < i_sta < i_open, "STA 必须在 Open 之前"
    assert blk[i_sta:i_open].count("try {") >= 1 or blk[i_create:i_sta].count("try {") >= 1, "opt-in 包 try 守卫"


def test_hresult_travels_to_err_field():
    """组3（嫌疑b）：HRESULT 不再被 null 包装吞——C# 暴露 H 版、PS 三调用点
    都把 hr=0x 带进返回串；hr!=0 拒绝空对象。"""
    t = _src()
    # C#：H 版签名与判定
    assert "public static int MsaaAccessibleH(IntPtr h, out object o)" in t, "H 版暴露 HRESULT"
    assert "if (hr != 0) { o = null; return hr; }" in t, "FAILED 拒绝"
    assert "return unchecked((int)0x80004005);" in t, "S_OK 空对象也算错"
    # PS：四调用点（read/select/rect/回读读名）都走 H 版且 hr 进串
    assert t.count("[RP.U]::MsaaAccessibleH($h, [ref]$o)") == 4, "read/select/rect/回读读名四调用点全走 H 版"
    assert "'0~-1~hr=0x{0:x}~'" in t, "读通道 wire 带 hr"
    assert "'msaa-null hr=0x{0:x}'" in t, "select/rect 标签带 hr"
    # 旧零信息 wrapper 不再被 PS 层直调
    assert "[RP.U]::MsaaAccessible($h)" not in t, "PS 不再走丢失 hr 的老包装"


def test_listbox_identity_probe_and_lv_int_face():
    """组4（件3）：只读整数身份探针——LB count/cur/双方言 lens 全整数与返回值
    型；no-channel 的 ListBox 也探；lv 整数面进 probe；零新裸指针。"""
    t = _src()
    # C# LbInfo：三消息全整数/返回值
    assert "public static string LbInfo(IntPtr h)" in t, "LB 身份探针在场"
    assert "0x018B" in t and "0x0188" in t, "count/cur 消息"
    assert "0x0191" in t and "0x018A" in t, "lens 双方言（W/A）"
    assert "count=" in t and "cur=" in t and "lensW=[" in t and "lensA=[" in t, "探针字段形态"
    # PS：no-channel 的 ListBox 照探 + lv 整数面
    assert "$cd.cls -eq 'ListBox'" in t and "[RP.U]::LbInfo($cd.hw)" in t, "no-channel ListBox 仍探"
    assert "lvint=count:" in t, "lv 整数面进 trace"
    assert "[RP.U]::ListCount($cd.hw, 'lv')" in t and "[RP.U]::ListSelIndex($cd.hw, 'lv')" in t, "lv 整数面数据源"
    # ListCount 已开公（PS 可调）
    assert "public static int ListCount(IntPtr h, string ch)" in t, "ListCount public"
    # 零新裸指针（本批消息清单全部整数型）
    for lit in ("0x1073", "0x102D", "0x102A", "0x100E", "0x0148", "0x0189"):
        assert lit not in t, f"整数探针批不得引入裸指针消息 {lit}"
