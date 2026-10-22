"""报表导出通道：DIALux 报表 → 打印到 PDF → 提取文本层。

分两段，边界清楚：

1. **打印段**（UIA，需 DIALux 在场）：``report.ps1`` 驱动「报表模式 → 打印 →
   Microsoft Print to PDF → 保存」，产出 PDF。
2. **文本层段**（纯 Python，可离线）：PyMuPDF 从 PDF 提取文本层——这是结果包
   抽取器的输入（2026-10-08 用 2 页版 / 29 页版双样本验证过可行）。

用法::

    from src.executor.uia.report import export_report, extract_text_layer
    events = export_report("build/reports/run.pdf")     # 需要 DIALux
    text = extract_text_layer("build/reports/run.pdf")  # 不需要

⚠️ 打印段（UIA）截至 2026-10-09 **未做真机验证**——脚本结构按 ``ugr.ps1``
同款契约写成，控件识别走 $Id 逃生舱 + 名称扫描兜底，首次真机跑时需校准。
文本层段已由既有样本验证。
"""
from __future__ import annotations

import logging
import queue as _queue
import subprocess
import threading
import time
from pathlib import Path
from typing import List, Optional

from .driver import StepEvent, _parse
from src.core.env import resource_path

logger = logging.getLogger(__name__)

REPORT_PS1 = resource_path("src/executor/uia/report.ps1")

_REPORT_STEPS = {
    "report-mode": "切到报表模式",
    "report-open": "打开报表预览",
    "report-print": "触发打印",
    "report-printer": "确认 PDF 打印机",
    "report-save": "写入输出路径",
    "report-wait": "等待 PDF 落盘",
    "report-done": "完成",
}

DEFAULT_REPORT_DIR = "build/reports"

# Thirteenth batch (twelfth shot: all three inner timeouts silent 4/4 -- the
# watcher inside ps1 could not testify why it never fired). External observer's
# judgment line: STAGE breadcrumb lines are appended by the ps1 MAIN thread at
# every transition; if the newest one is older than this while stdout is
# silent, python -- the only observer living outside the suspected component --
# emits printer-step-hang-timeout itself and kills the child. 45s is three
# times the longest single bounded wait inside the step (Wait-Dialog 15s), so
# a healthy run can never trip it; it is still 13x before the 600s shell
# watchdog. Contract-pinned in tests.
HB_STALE_S = 45


def _read_crumb(crumb_path: str | Path) -> dict:
    """解析面包屑文件：取最后一条 ``STAGE``（主线程心跳）与 ``TARGET`` 行。

    行格式（ps1 侧 C# 追加，UTF-8）：``KIND <epoch-ms> payload``。
    文件缺失/行损坏返回全 ``None``——调用方按“无可观察”处理，不误判。
    """
    info: dict = {"stage": None, "stage_ms": None, "target": None}
    try:
        text = Path(crumb_path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return info
    for ln in text.splitlines():
        parts = ln.split(" ", 2)  # kind epoch-ms payload
        if len(parts) != 3:
            continue
        kind, ms_s, payload = parts
        try:
            ms = int(ms_s)
        except ValueError:
            continue
        if kind == "STAGE":
            info["stage_ms"] = ms
            info["stage"] = payload[6:] if payload.startswith("stage=") else payload
        elif kind == "TARGET":
            info["target"] = payload[7:] if payload.startswith("target=") else payload
    return info


def _external_hang_detail(
    crumb_path: str | Path,
    started: float,
    now: Optional[float] = None,
) -> Optional[str]:
    """心跳陈旧判定：返回 ``printer-step-hang-timeout`` 失败 detail，None=继续等。

    两种“停”都是信号：有 STAGE 行但超龄 = 主线程卡在 ``stage=`` 那一步；
    完全没有 STAGE 行且过了预算 = 面包屑未布防（H1 的运行实证位）。
    ``watchdog-source=python-external`` 是产码方标识，ps1 自产码无此尾追字段。
    """
    now = time.time() if now is None else now
    elapsed_ms = max(0, int((now - started) * 1000))
    info = _read_crumb(crumb_path)
    if info["stage_ms"] is not None:
        age_ms = max(0, int(now * 1000) - info["stage_ms"])
        if age_ms < HB_STALE_S * 1000:
            return None
        stage = info["stage"] or "unknown"
        last_hb = str(info["stage_ms"])
        crumb_state = "exists"
    else:
        if elapsed_ms < HB_STALE_S * 1000:
            return None
        stage = "no-stage-line"
        last_hb = "none"
        crumb_state = "missing" if not Path(crumb_path).exists() else "empty"
    return (
        f"printer-step-hang-timeout stage={stage} "
        f"elapsed={elapsed_ms} "
        f"last-heartbeat-ms={last_hb} heartbeat-age-ms="
        f"{max(0, int(now * 1000) - (info['stage_ms'] or int(started * 1000)))} "
        f"fg=external-unreadable target={info['target'] or 'unknown-external'} "
        f"crumb={crumb_state} watchdog-source=python-external"
    )


def _decode_pipe(raw: bytes) -> str:
    """解码 PowerShell 管道字节行（stdout STEP 与 stderr 日志同口径）。

    根因（2026-10-22 第十批最小复现钉死，非猜测）：PowerShell 5.1 向重定向
    管道写的非 ASCII 字节按**机器 OEM 码表**（中文 Windows＝GBK/cp936），
    而本文件原来以文本模式按 utf-8 + errors='replace' 盲读（text 模式开管道）
    ——第九枪 `ui=` 中文现场因此在读入瞬间变成 U+FFFD 序列（回执文件本体
    EF BF BD，`title` 是 python 自产所以完好；损耗发生在 python 读子进程
    流的解码环节，通道是 stdout，不在 stderr）。

    两路都要会读：ps1 侧头部已声明 ``[Console]::OutputEncoding = UTF8``
    （生效则走 utf-8 快路）；不生效时字节是 GBK——先 utf-8 严格、失败回退
    gbk + replace，两条路都逐字可读、都不抛。见
    tests/test_report_pipe_encoding.py 的往返与复现断言。
    """
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("gbk", errors="replace")


def extract_text_layer(pdf_path: str | Path, *, page_marker: bool = True) -> str:
    """用 PyMuPDF 提取 PDF 文本层；``===== PAGE n =====`` 为页分隔。

    抛 FileNotFoundError 当 PDF 不存在；RuntimeError 当 PyMuPDF 未安装。
    """
    p = Path(pdf_path)
    if not p.exists():
        raise FileNotFoundError(f"PDF 不存在：{p}")
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - 本机已装
        raise RuntimeError("未安装 PyMuPDF（pip install pymupdf）") from exc

    chunks: List[str] = []
    with fitz.open(p) as doc:
        for i, page in enumerate(doc, start=1):
            if page_marker:
                chunks.append(f"===== PAGE {i} =====")
            chunks.append(page.get_text().strip())
    return "\n".join(chunks).strip() + "\n"


def export_report(
    pdf_path: str | Path,
    *,
    process_name: str = "DIALux_x64",
    timeout_s: int = 180,
    wait_timeout_s: int = 60,
    cancel_check: Optional[callable] = None,
    on_step: Optional[callable] = None,
    **id_overrides: str,
) -> List[StepEvent]:
    """驱动 DIALux 报表打印链，产出 PDF（真机段，未验证）。

    参数:
        pdf_path: 目标 PDF 路径（绝对路径；中间目录会自动创建）。
        id_overrides: 逃生舱——``report_menu_id`` / ``report_tab_index`` /
            ``print_menu_id`` / ``printer_combo_id`` / ``save_button_id`` /
            ``file_name_id``，用于钉死控件（键名一律 **snake_case**，与
            ``real_action.py`` 把 ``ids`` 摊成 kwargs 的口径一致；
            2026-10-19 开跑信曾误写成“同 ps1 参数”的 PascalCase，勘误已发）。
        cancel_check: 每读一行调用，返回 True 时中止。

    返回: StepEvent 列表；``succeeded(events)``（末步 report-done）判断跑完。
    """
    if not REPORT_PS1.exists():
        raise FileNotFoundError(f"报表驱动脚本缺失：{REPORT_PS1}")

    out = Path(pdf_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(REPORT_PS1),
        "-PdfPath", str(out),
        "-ProcessName", process_name,
        "-WaitTimeoutMs", str(int(wait_timeout_s * 1000)),
    ]
    for key, flag in (
        ("report_menu_id", "-ReportMenuId"),
        ("report_tab_index", "-ReportTabIndex"),
        ("print_menu_id", "-PrintMenuId"),
        ("printer_combo_id", "-PrinterComboId"),
        ("save_button_id", "-SaveButtonId"),
        ("file_name_id", "-FileNameId"),
    ):
        val = id_overrides.get(key)
        if val:
            cmd += [flag, str(val)]

    crumb = out.parent / (out.stem + "_printer_crumb.txt")
    stderr_path = out.parent / (out.stem + "_ps1_stderr.log")
    try:
        crumb.unlink()          # 上一跑的旧心跳会直接误导判定，先清
    except FileNotFoundError:
        pass
    cmd += ["-BreadCrumbPath", str(crumb)]

    logger.info("报表打印驱动启动：%s（面包屑 %s，stderr %s）", out, crumb.name, stderr_path.name)

    events: List[StepEvent] = []
    started = time.time()
    try:
        sf = open(stderr_path, "wb")
    except OSError as exc:
        raise RuntimeError(f"开不了 ps1 stderr 落盘文件：{exc}") from exc
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=sf,
        )
    except OSError as exc:
        sf.close()
        raise RuntimeError(f"起不了 PowerShell：{exc}") from exc
    # stderr 直接沉到文件（子进程持有自己的句柄，父侧即关）：第十/十一枪的
    # 结构性盲区（只在 stdout EOF 后才读 + 壳层超时直接丢弃）不复存在——
    # ps1 挂死时它最后报的任何 PowerShell 错误已经在磁盘上。
    sf.close()

    assert proc.stdout is not None
    # 泵线程：stdout 行进队列，主循环才能在“没有行到达”时轮询面包屑——
    # 一个阻塞的读者自己观察不到任何东西（第十二枪的教训）。
    line_q: "_queue.Queue[Optional[bytes]]" = _queue.Queue()

    def _pump() -> None:
        try:
            for raw in proc.stdout:
                line_q.put(raw)
        finally:
            line_q.put(None)

    threading.Thread(target=_pump, daemon=True, name="report-ps1-stdout").start()

    cancelled = False
    while True:
        try:
            raw_line = line_q.get(timeout=1.0)
        except _queue.Empty:
            # 无 stdout 进展：外部观察者看主线程心跳（HB_STALE_S 契约阈值）
            if cancel_check is not None and cancel_check():
                proc.kill()
                cancelled = True
                logger.warning("收到停止请求，报表导出中止")
                break
            detail = _external_hang_detail(crumb, started)
            if detail is not None and proc.poll() is None:
                ev = StepEvent(
                    name="report-printer",
                    title=_REPORT_STEPS.get("report-printer", "report-printer"),
                    ok=False,
                    detail=detail,
                    progress=min(100.0, len(events) / len(_REPORT_STEPS) * 100.0),
                )
                events.append(ev)
                logger.error("[%5.1f%%] %s 失败（%s）", ev.progress, ev.title, detail)
                if on_step is not None:
                    on_step(ev)
                proc.kill()
                logger.error("外部观察者判挂并杀进程（watchdog-source=python-external）；"
                             "面包屑 %s，stderr 落盘 %s", crumb, stderr_path)
                break
            continue
        if raw_line is None:
            break
        line = _decode_pipe(raw_line)
        if cancel_check is not None and cancel_check():
            proc.kill()
            cancelled = True
            logger.warning("收到停止请求，报表导出中止")
            break
        parsed = _parse(line)
        if parsed is None:
            if line.strip():
                logger.debug("报表输出（非 STEP）：%s", line.rstrip())
            continue
        name, ok, detail = parsed
        ev = StepEvent(
            name=name,
            title=_REPORT_STEPS.get(name, name),
            ok=ok,
            detail=detail,
            progress=min(100.0, len(events) / len(_REPORT_STEPS) * 100.0),
        )
        events.append(ev)
        logger.info(
            "[%5.1f%%] %s %s%s",
            ev.progress,
            ev.title,
            "OK" if ok else "失败",
            f"（{detail}）" if detail else "",
        )
        if on_step is not None:
            on_step(ev)
        if not ok:
            break

    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        logger.error("报表驱动超时 %ds，已杀掉", timeout_s)
    if stderr_path.exists():
        try:
            logger.warning("ps1 stderr 已落盘 %s（%d bytes）",
                           stderr_path, stderr_path.stat().st_size)
        except OSError:
            pass
    if cancelled:
        events.append(
            StepEvent(
                "cancelled",
                "已停止",
                False,
                "停在报表导出中途",
                events[-1].progress if events else 0.0,
            )
        )
    return events


def exported_ok(events: List[StepEvent]) -> bool:
    """跑到 report-done 且全 ok 才算导出成功。"""
    return bool(events) and all(e.ok for e in events) and events[-1].name == "report-done"
