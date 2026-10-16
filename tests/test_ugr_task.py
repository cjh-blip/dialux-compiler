"""UGR 任务与解析器离线测试（不需要 DIALux 在场）。

覆盖：
- ``\\uXXXX`` 转义还原、面板文本取值（中英文两种）
- ``ugr-read`` detail 的拆分（文本 + target/step/range）
- ``UgrResult.ok`` 语义（全 ok 且跑到 ugr-done）
- ``UgrTask`` 落 JSON 与失败如实返回（mock 掉真正的驱动入口）
"""
from __future__ import annotations

import json

from src.executor.uia.driver import StepEvent
from src.executor.uia.ugr import UgrResult, _absorb_read, _extract_ugr, _unescape
from src.tasks.dialux.ugr_task import UgrTask
from src.workbench.task import TaskContext


def test_unescape_restores_cjk():
    assert _unescape(r"\u8ba1\u7b97\u70b9") == "计算点"
    assert _unescape("plain ASCII") == "plain ASCII"


def test_extract_ugr_chinese_and_english():
    assert _extract_ugr("计算点 1 (RUG) 最大 16.2 目标 <= 19.0") == 16.2
    assert _extract_ugr("Calculation point Maximum 12.7 target 19") == 12.7
    assert _extract_ugr("no number here") is None


def test_absorb_read_splits_text_and_params():
    r = UgrResult()
    detail = (
        r"text=\u8ba1\u7b97\u70b9 1 \u6700\u5927 16.2"
        r" target=19.0 step=15.0 from=0.0 to=360.0"
    )
    _absorb_read(r, detail)
    assert r.ugr_max == 16.2
    assert (r.target, r.step_deg, r.range_from, r.range_to) == (19.0, 15.0, 0.0, 360.0)
    assert "计算点" in r.panel_text and "最大" in r.panel_text


def test_result_ok_requires_all_ok_and_done():
    r = UgrResult()
    assert not r.ok  # 空
    r.events = [StepEvent("ugr-done", "完成", True, "", 100.0)]
    assert r.ok
    r.events = [
        StepEvent("ugr-calc", "计算", True, "sec=45", 70.0),
        StepEvent("ugr-read", "读回", False, "ugr-result-not-found", 85.0),
    ]
    assert not r.ok


def test_ugr_task_writes_json(monkeypatch, tmp_path):
    from src.executor.uia import ugr as ugr_mod

    ok = UgrResult(
        events=[StepEvent("ugr-done", "完成", True, "", 100.0)],
        ugr_max=16.2,
        target=19.0,
        step_deg=15.0,
        range_from=0.0,
        range_to=360.0,
        panel_text="计算点 1 (RUG) 最大 16.2",
    )
    monkeypatch.setattr(ugr_mod, "measure_ugr", lambda **kw: ok)

    out = tmp_path / "ugr_result.json"
    ctx = TaskContext(config={"out_json": str(out), "point": [4.785, 5.5, 1.2]})
    res = UgrTask().run(ctx)

    assert res.ok, res.detail
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["ugr_max"] == 16.2
    assert data["step_deg"] == 15.0


def test_ugr_task_reports_failure_without_writing(monkeypatch, tmp_path):
    from src.executor.uia import ugr as ugr_mod

    fail = UgrResult(
        events=[StepEvent("ugr-calc", "计算", False, "calculation-timeout", 70.0)]
    )
    monkeypatch.setattr(ugr_mod, "measure_ugr", lambda **kw: fail)

    out = tmp_path / "never.json"
    ctx = TaskContext(config={"out_json": str(out)})
    res = UgrTask().run(ctx)

    assert not res.ok
    assert "calculation-timeout" in res.detail
    assert not out.exists()
