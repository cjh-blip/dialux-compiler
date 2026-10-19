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
import subprocess
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

    logger.info("报表打印驱动启动：%s", out)

    events: List[StepEvent] = []
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as exc:
        raise RuntimeError(f"起不了 PowerShell：{exc}") from exc

    assert proc.stdout is not None
    cancelled = False
    for line in proc.stdout:
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
    stderr = (proc.stderr.read() if proc.stderr else "") or ""
    if stderr.strip():
        logger.warning("报表 stderr：%s", stderr.strip()[:300])
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
