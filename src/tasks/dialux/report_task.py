"""自动导出报告：DIALux 报表 → 打印到 PDF → 提取文本层（MVP4 实做）。

历史沿革：原占位版以「``DxPrintExport*`` 是 Pro 功能、2026-09-08 到期」为由
不实跑。**该假设已被推翻**——2026-10-08 两次实测证明「报表 → 打印 →
Microsoft Print to PDF」在免费版可用（2 页版 / 29 页版双样本），故改为实做。

参数（``params`` 或 ``config`` 任一通道）：
- ``mode``: ``export``（默认，打印并提文本层）| ``text``（只对已有 PDF 提文本层）
- ``pdf_path``: 目标/已有 PDF 路径（默认 ``<report_out>/report.pdf``）
- ``report_out``: 输出目录（默认 ``build/reports/``）

验收对应：无 DIALux 在场时必须**如实报失败**，不得产出自算结论冒充实测。
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from src.workbench.task import Task, TaskContext, TaskResult

logger = logging.getLogger(__name__)

DEFAULT_DIR = "build/reports"
DIALUX_ABSENT_HINTS = {"no-window-process", "main-window-not-found"}


class ReportTask(Task):
    """自动导出报告（报表 → PDF → 文本层）。"""

    name = "自动报告"
    priority = 30

    def run(self, ctx: TaskContext) -> TaskResult:
        # params/config 双通道（2026-10-17 起 TaskContext 声明 params、Flow 逐步下发）；
        # getattr 保留对旧 ctx 实现的兼容。
        params: Dict[str, Any] = getattr(ctx, "params", None) or (ctx.config or {})
        mode = params.get("mode", "export")
        report_out = params.get("report_out") or DEFAULT_DIR
        pdf_path = params.get("pdf_path")

        pdf = Path(pdf_path) if pdf_path else Path(report_out) / "report.pdf"

        from src.executor.uia.report import (
            export_report,
            exported_ok,
            extract_text_layer,
        )

        if mode == "text":
            if not pdf.exists():
                return TaskResult(False, f"PDF 不存在：{pdf}")
            text = extract_text_layer(pdf)
            txt = pdf.with_suffix(".txt")
            txt.write_text(text, encoding="utf-8")
            ctx.log(f"文本层已提取：{txt}（{len(text)} 字符）")
            return TaskResult(
                True,
                f"文本层 {len(text)} 字符 → {txt}",
                {"pdf": str(pdf), "txt": str(txt)},
            )

        events = export_report(pdf, cancel_check=ctx.cancelled)
        if not exported_ok(events):
            bad = [e for e in events if not e.ok]
            reason = bad[-1].detail if bad else "no-output"
            if reason in DIALUX_ABSENT_HINTS:
                reason = f"DIALux 未运行（{reason}）——报告导出需要真机"
            return TaskResult(False, f"报表导出失败：{reason}", {"pdf": str(pdf)})

        text = extract_text_layer(pdf)
        txt = pdf.with_suffix(".txt")
        txt.write_text(text, encoding="utf-8")
        ctx.log(f"报表导出完成：{pdf}（{pdf.stat().st_size} B）＋ 文本层 {txt}")
        return TaskResult(
            True,
            f"报表 {pdf.name} ＋ 文本层 {len(text)} 字符",
            {"pdf": str(pdf), "txt": str(txt)},
        )
