# -*- coding: utf-8 -*-
"""第十三批（2026-10-23 · 第十二枪四方同哈希与内层零响）：外部观察者主判据。

第十二枪的教训：三层内层超时 4 跑全部静默，**故障方自证的通道整体不可信**。
本文件钉住两条新链：

1. **面包屑（件2①）**：ps1 每次状态迁移（ARMED/STAGE/TARGET/HEART/DISARMED/
   FACE）落盘，**不依赖 stdout**；主线程写 STAGE（停更=主线程卡），timer 线程
   写 HEART（停更=进程级冻结）——三分法切 H1/H2/H4。
2. **外部观察者（件3，本批主判据）**：python 侧在无 stdout 进展时轮询面包屑，
   心跳陈旧（HB_STALE_S=45s，契约值）即由 **python 自己**产出
   `printer-step-hang-timeout … watchdog-source=python-external` 并杀子进程——
   码面不再依赖 ps1 存活。ps1 内部 WArm 保留为双保险，但判据以这里为主。
"""
from __future__ import annotations

from pathlib import Path

from src.executor.uia.report import (
    HB_STALE_S,
    _external_hang_detail,
    _read_crumb,
)

REPORT_PY = Path(__file__).resolve().parent.parent / "src" / "executor" / "uia" / "report.py"
REPORT_PS1 = Path(__file__).resolve().parent.parent / "src" / "executor" / "uia" / "report.ps1"


def test_hb_stale_contract_is_well_before_shell_watchdog(tmp_path):
    """阈值契约：45s > 最长单阶段有界等待（Wait-Dialog 15s）三倍，不误杀健康跑；
    且 13 倍早于 600s 壳层看门狗——心跳停更必先出码面，绝不回到 600s 死区。"""
    assert HB_STALE_S == 45
    assert HB_STALE_S >= 15 * 3         # 单阶段最长有界等待 15s 的三倍
    assert HB_STALE_S * 4 < 600         # 远早于壳层 600s


def test_read_crumb_takes_last_stage_and_target(tmp_path):
    """面包屑解析：STAGE 取最后一条（主线程推进口径）、TARGET 取值、坏行/缺失不抛。"""
    p = tmp_path / "crumb.txt"
    p.write_text(
        "ARMED 1700000000000 budget=120000 step=report-printer\n"
        "STAGE 1700000001000 stage=wait-dialog\n"
        "TARGET 1700000002000 target=0x7bf1e8\n"
        "HEART 1700000006000 stage=wait-dialog elapsed=5000\n"
        "STAGE 1700000007000 stage=uia-dialog-text\n"
        "not-a-crumb-line\n"
        "STAGE garbage stage=nope\n",
        encoding="utf-8",
    )
    info = _read_crumb(p)
    assert info["stage"] == "uia-dialog-text"
    assert info["stage_ms"] == 1700000007000
    assert info["target"] == "0x7bf1e8"
    # 文件缺失全 None（不误判）
    miss = _read_crumb(tmp_path / "absent.txt")
    assert miss == {"stage": None, "stage_ms": None, "target": None}


def test_external_hang_detail_on_stale_stage(tmp_path):
    """核心行为：主线程心跳陈旧 >45s → 产出含全部定位字段的失败 detail；
    心跳新鲜 → None（继续等）。这就是“停更必 Fail 在码面”的单测形态。"""
    p = tmp_path / "crumb.txt"
    now = 1_700_000_100.0
    started = now - 100.0
    p.write_text(
        f"STAGE {int((now - 90) * 1000)} stage=printer-select-msg\n"
        f"TARGET {int((now - 95) * 1000)} target=0x7bf1e8\n",
        encoding="utf-8",
    )
    detail = _external_hang_detail(p, started, now=now)
    assert detail is not None
    assert detail.startswith("printer-step-hang-timeout stage=printer-select-msg")
    assert "elapsed=" in detail and "last-heartbeat-ms=" in detail
    assert "heartbeat-age-ms=" in detail
    assert "fg=external-unreadable" in detail
    assert "target=0x7bf1e8" in detail
    assert "crumb=exists" in detail
    assert detail.rstrip().endswith("watchdog-source=python-external")
    # 心跳新鲜（5s < 45s）→ 不判挂
    fresh = tmp_path / "fresh.txt"
    fresh.write_text(f"STAGE {int((now - 5) * 1000)} stage=wait-dialog\n", encoding="utf-8")
    assert _external_hang_detail(fresh, started, now=now) is None


def test_external_hang_detail_no_stage_line_is_h1_evidence(tmp_path):
    """面包屑无任何 STAGE 行且过预算 → 同样出码面，stage=no-stage-line 即 H1
    的运行实证位（布防未执行/未落盘）；crumb=missing|empty 区分两种缺。"""
    now = 1_700_000_100.0
    started = now - 100.0
    detail = _external_hang_detail(tmp_path / "absent.txt", started, now=now)
    assert detail is not None
    assert "stage=no-stage-line" in detail
    assert "crumb=missing" in detail
    assert "watchdog-source=python-external" in detail
    # 空文件 → crumb=empty
    empty = tmp_path / "empty.txt"
    empty.write_text("", encoding="utf-8")
    detail2 = _external_hang_detail(empty, started, now=now)
    assert detail2 is not None and "crumb=empty" in detail2
    # 预算未过 → 不判
    assert _external_hang_detail(tmp_path / "absent.txt", now - 10.0, now=now) is None


def test_report_py_external_observer_structure():
    """结构：泵线程＋队列轮询＋判挂即杀＋面包屑清旧＋传参＋stderr 文件沉降；
    负断言锁死旧盲区不复活（stderr 禁回 PIPE、stdout 禁回单线程阻塞 for）。"""
    src = REPORT_PY.read_text(encoding="utf-8")
    assert "watchdog-source=python-external" in src, "外部产码方标识"
    assert "-BreadCrumbPath" in src, "面包屑路径传给 ps1"
    assert 'crumb.unlink()' in src, "开跑前清旧心跳（旧 STAGE 会直接误判）"
    assert "_pump" in src and "line_q.get(timeout=1.0)" in src, "泵线程＋可轮询读"
    assert "stderr=subprocess.PIPE" not in src, "stderr 禁回旧盲区"
    i_judge = src.index("_external_hang_detail(crumb, started)")
    assert src.index("proc.kill()", i_judge) > i_judge, "判挂分支必须杀子进程"
    assert src.index("queue.Empty") < i_judge, "先无进展再判心跳"
    assert "time.time()" in src, "外部自己的计时基准"


def test_report_ps1_breadcrumb_writes_and_face_order():
    """ps1 侧面包屑与码面顺序：ARMED 先于布防、STAGE 随主线程推进、FACE 先文件
    后 Console 再 Exit（Console 被卡也吞不掉文件里的码面）；Timer 静态字段持有
    （第十二批件1 的 H2-GC 静态排除锚，正断言防回退）。"""
    t = REPORT_PS1.read_text(encoding="utf-8")
    assert 'private static System.Threading.Timer wTimer' in t, "Timer 静态根持有（GC 候选排除）"
    for lit in ('ARMED ', 'DISARMED ', 'STAGE ', 'HEART ', 'FACE ', 'TARGET '):
        assert lit in t, f"面包屑行 {lit} 不在"
    assert "File.AppendAllText" in t, "落盘不依赖 stdout 通道"
    assert "5000, 5000" in t, "心跳周期 5s（回调内判 budget）"
    assert "WSetCrumb" in t and "BreadCrumbPath" in t
    # 调用序：WSetCrumb → WArm →（步内）
    assert t.index("[RP.U]::WSetCrumb($crumb)") < t.index("[RP.U]::WArm("), "先设路径再布防"
    # FACE → Console → Exit 顺序（写码面不许排在退出之后、文件不许排在 Console 之后）
    i_face = t.index('Crumb("FACE "')
    i_console = t.index("Console.WriteLine(face)")
    i_exit = t.index("Environment.Exit(1)")
    assert i_face < i_console < i_exit, "码面顺序：文件 → stdout → 退出"
