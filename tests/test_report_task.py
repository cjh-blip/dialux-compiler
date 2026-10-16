"""报表任务与文本层提取的离线测试（不需要 DIALux 在场）。

覆盖：
- ``extract_text_layer`` 的页标记与文本提取、文件缺失报错
- ``exported_ok`` 语义（末步 report-done）
- ``ReportTask`` 的 text 模式 / export 成功路径 / 无 DIALux 时如实失败且不落盘
"""
from __future__ import annotations

import pytest

from src.executor.uia.driver import StepEvent
from src.executor.uia.report import exported_ok, extract_text_layer
from src.tasks.dialux.report_task import ReportTask
from src.workbench.task import TaskContext

fitz = pytest.importorskip("fitz")  # PyMuPDF；本机已装（缺失时跳过本组用例）


def _make_pdf(path, pages):
    doc = fitz.open()
    for text in pages:
        page = doc.new_page()
        page.insert_text((72, 72), text)
    doc.save(str(path))
    doc.close()


def test_extract_text_layer_with_page_markers(tmp_path):
    pdf = tmp_path / "r.pdf"
    _make_pdf(pdf, ["Hello 714 lx", "Compute point CP1 UGR 16.2"])
    text = extract_text_layer(pdf)
    assert "===== PAGE 1 =====" in text
    assert "===== PAGE 2 =====" in text
    assert "714 lx" in text
    assert "16.2" in text


def test_extract_text_layer_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        extract_text_layer(tmp_path / "nope.pdf")


def test_exported_ok_semantics():
    assert not exported_ok([])
    assert exported_ok([StepEvent("report-done", "完成", True, "", 100.0)])
    assert not exported_ok([StepEvent("report-save", "保存", False, "x", 60.0)])


def test_report_task_text_mode(tmp_path):
    pdf = tmp_path / "run.pdf"
    _make_pdf(pdf, ["Report body"])
    ctx = TaskContext(config={"mode": "text", "pdf_path": str(pdf)})

    res = ReportTask().run(ctx)

    assert res.ok, res.detail
    assert (tmp_path / "run.txt").exists()


def test_report_task_export_fails_when_dialux_absent(monkeypatch, tmp_path):
    from src.executor.uia import report as report_mod

    absent = [StepEvent("report-mode", "切到报表模式", False, "no-window-process", 0.0)]
    monkeypatch.setattr(report_mod, "export_report", lambda *a, **kw: absent)

    pdf = tmp_path / "never.pdf"
    ctx = TaskContext(config={"pdf_path": str(pdf)})
    res = ReportTask().run(ctx)

    assert not res.ok
    assert "DIALux 未运行" in res.detail
    assert not pdf.exists()  # 不造假：失败时不留半成品


def test_report_task_export_success_writes_txt(monkeypatch, tmp_path):
    from src.executor.uia import report as report_mod

    pdf = tmp_path / "ok.pdf"

    def fake_export(path, **kw):
        _make_pdf(pdf, ["Report body 714 lx"])
        return [StepEvent("report-done", "完成", True, "", 100.0)]

    monkeypatch.setattr(report_mod, "export_report", fake_export)

    ctx = TaskContext(config={"pdf_path": str(pdf)})
    res = ReportTask().run(ctx)

    assert res.ok, res.detail
    txt = tmp_path / "ok.txt"
    assert txt.exists()
    assert "714 lx" in txt.read_text(encoding="utf-8")
