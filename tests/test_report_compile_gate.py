# -*- coding: utf-8 -*-
"""第十四批（2026-10-23 · 第十三枪元凶链坐实）：编译修复＋硬 Fail 门＋spin 逃逸。

元凶链（第十三枪 stderr 逐字坐实）：cs `(UIntPtr)w` 直转被 PS5.1 CodeDom 拒
（0.cs(50) IntPtr→UIntPtr）→ Add-Type 失败、[RP.U] 未加载 → WSetCrumb/WArm
执行即抛 TypeNotFound（ARMED 永不落盘）→ Wait-Dialog 内层死循环 33,667 条。

三刀对应三断言组：
1. 禁直转：`(UIntPtr)w` 形态零命中、链式 `(UIntPtr)(long)w` 在场、
   SafeSend 语义（3000/SMTO/判零）原样。
2. 硬门：Add-Type 失败必产 `report-init fail add-type-compile-failed line=…
   errors='…'` 后立即 exit——绝不带病继续（元凶链的闸门）。
3. spin：Wait-Dialog 内层圈数上限＋`wait-dialog-spin-timeout` 码面，
   调用点步名参数化。

⚠ 无 pwsh：cs 型别正确性与三刀行为只能真机 Add-Type 验证（第十四枪），
本文件为静态契约（形态/顺序/字段），不冒充编译验证。
"""
from __future__ import annotations

import re
from pathlib import Path

REPORT_PS1 = Path(__file__).resolve().parent.parent / "src" / "executor" / "uia" / "report.ps1"


def _src() -> str:
    return REPORT_PS1.read_text(encoding="utf-8")


def test_cs_block_has_no_direct_uintptr_cast():
    """组1：`(UIntPtr)w` 直转零命中（元凶形态）；全部 (UIntPtr) 强转只能是
    (long) 链式或类型字面（[UIntPtr]::Zero），反向直转同样禁止。"""
    src = _src()
    assert "(UIntPtr)w" not in src, "直转形态必须清零（CodeDom 拒 IntPtr->UIntPtr）"
    # 所有 (UIntPtr) 后必须是 (long) 链式或 [（类型成员访问），不允许接变量
    bad = re.findall(r"\(UIntPtr\)(?!\(long\)|\[)", src)
    assert bad == [], f"残留非链式 UIntPtr 强转: {bad}"
    assert "(UIntPtr)(long)w" in src, "链式强转必须在场"
    # 反向：IntPtr 形参不得从 UIntPtr 直转
    assert not re.search(r"\(IntPtr\)\s*w\b", src), "反向直转同禁"


def test_safe_send_semantics_unchanged():
    """组1 附：只修型别——3s 超时、SMTO_ABORTIFHUNG、判零返回语义原样。"""
    src = _src()
    assert 'SendMessageTimeout(IntPtr h, int m, UIntPtr w, IntPtr l' in src, "声明签名不动"
    assert "0x0002 /*SMTO_ABORTIFHUNG*/, 3000, out res" in src, "超时与 flag 原样"
    assert "if (ok == IntPtr.Zero) return IntPtr.Zero;" in src, "判零返回原样"
    assert "return (IntPtr)((long)res);" in src, "res 链式返回原样（本就过编译）"


def test_add_type_hard_fail_gate():
    """组2：硬门在场且形态正确——here-string 落 $csSource、-ErrorAction Stop、
    catch 产码（report-init + line/errors 字段）后 exit 先于任何 RP.U 调用；
    旧的裸 Add-Type @\"...\"@ 形态必须已消失（那条路编译失败只进 stderr）。"""
    src = _src()
    assert '$csSource = @"' in src, "cs 源先落变量（才能 -ErrorAction Stop 捕获）"
    assert 'Add-Type @"' not in src, "裸 Add-Type here-string 必须已移除"
    i_assign = src.index('$csSource = @"')
    i_try = src.index("try { Add-Type -TypeDefinition $csSource -ErrorAction Stop }")
    assert i_assign < i_try, "赋值先于调用"
    i_catch = src.index("} catch { $addErr = $_ }")
    i_code = src.index("report-init fail add-type-compile-failed", i_catch)
    assert i_try < i_catch < i_code, "catch 内才产码"
    # 字段与截断
    assert "add-type-compile-failed line=" in src
    assert "errors='" in src
    assert r"\.cs\((\d+)\)" in src, "从编译错误抽 cs 行号"
    assert "Substring(0, 300)" in src, "错误文本截断防爆"
    assert "-replace '\\s+', ' '" in src, "多行错误压单行（STEP 单行契约）"
    # 产码后立即退出，绝不带病继续
    i_exit = src.index("exit 1", i_code)
    assert i_exit > i_code and i_exit < src.index("function Emit("), "码面后、Emit 定义前即退出"


def test_wait_dialog_spin_escape():
    """组3：内层圈数上限＋码面＋调用点步名参数化；三序（上限→Fail→外层 return）。"""
    src = _src()
    assert "function Wait-Dialog([int]$ms, [IntPtr]$skipHwnd, [string]$step" in src, "步名参数化"
    assert "$spin -gt 2000" in src, "内层圈数上限（正常枚举个位数圈，仅异常触发）"
    assert "wait-dialog-spin-timeout spin=" in src, "带圈数的码面"
    assert "last='" in src, "带最后错误摘要"
    assert "Fail $step ('wait-dialog-spin-timeout" in src, "挂在调用方步名上"
    i_fn = src.index("function Wait-Dialog")
    i_spin = src.index("$spin -gt 2000", i_fn)
    i_fail = src.index("Fail $step", i_spin)
    i_ret = src.index("return [IntPtr]::Zero", i_fn)
    assert i_fn < i_spin < i_fail < i_ret, "上限与 Fail 在内层、return 语义不变"
    # 两处调用点各自传步名
    assert "Wait-Dialog $DialogTimeoutMs ([IntPtr]::Zero) 'report-printer'" in src
    assert "Wait-Dialog $DialogTimeoutMs $hDlg1 'report-save'" in src
    # spin 判定不依赖 RP.U（TypeNotFound 场景也要能出码）：$Error 取文本是 PS 原生
    assert '$Error.Count -gt 0' in src and '$Error[0]' in src
