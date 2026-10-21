"""UGR 任务与解析器离线测试（不需要 DIALux 在场）。

覆盖：
- ``\\uXXXX`` 转义还原、面板文本取值（中英文两种）
- ``ugr-read`` detail 的拆分（文本 + target/step/range）
- ``UgrResult.ok`` 语义（全 ok 且跑到 ugr-done）
- ``UgrTask`` 落 JSON 与失败如实返回（mock 掉真正的驱动入口）
"""
from __future__ import annotations

import json
from pathlib import Path

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


def test_extract_ugr_rejects_out_of_range():
    """第六批（第五枪 ugr_max=1.0 误锚）：区间 [5,50] 护栏。
    **原文 fixture 已在第七批落袋并锁死**（见下一条），本组构造样本
    继续保留作回归。"""
    # 区间外的「最大」单独出现 → None（旧 search 会直接返回 1.0）
    assert _extract_ugr("某标签 最大 1.0 其他 1/1") is None
    # finditer 跳过区间外候选、命中后面真值（不硬编码，只按区间筛）
    assert _extract_ugr("最大 1.0 …… 最大 29.2") == 29.2
    # 兜底一位小数被区间拒（1.0/均匀度 0.x 都出不来）
    assert _extract_ugr("值 1.0") is None
    assert _extract_ugr("均匀度 0.4 目标 19") is None
    # 摘要行形态（回执逐字片段）：一位小数首个区间内命中即 RUG 有限值
    assert _extract_ugr("点2 513 lx |- +29.2 |- 面1 308 lx |0.92 +> 30") == 29.2


def test_extract_ugr_fixture_e5_p5():
    """第七批主测：第六枪回传的原文 fixture（panel_text 可读版逐字，
    2,212B）锁死正向抽取——
    - **期望 29.3**（全部有限 RUG 29.2/29.3/28.9 取 max，统筹口径）；
    - 表头段（`最大 | 1/1` 与列名组）结构排除，旧实现在此得 1.0；
    - `> 30` 饱和、均匀度两位小数、`0.000 m` 参数均不得入候选。
    """
    fix = Path(__file__).parent / "fixtures" / "e5_p5_panel_text.txt"
    text = fix.read_text(encoding="utf-8").strip()
    assert _extract_ugr(text) == 29.3
    # 表头段单独出现 → None（结构排除：页码记号 1/1 邻域）
    header = "计算面 | (直角照度) | 实际 | 目标 | 平均 | 最小 | 1/1 | 最大 | 1/1"
    assert _extract_ugr(header) is None
    # 目标值排除（结构词紧邻）：旧形态 19.0 不得混入
    assert _extract_ugr("计算点 1 (RUG) 最大 16.2 目标 <= 19.0") == 16.2


def test_extract_ugr_fixture_e7_p3():
    """第八批：第七枪原文 fixture 第二例（2,524B）——跨样本 max 口径双保险：
    新增计算点 6/7 重算出 29.6/29.5 后 **期望 29.6**（max{29.2,29.3,
    29.6,29.5,28.9}）；本样本无表头段，`1/1` 不得出现（上枪误锚源）；
    两例 fixture 一并锁死结构排除与取 max 语义。"""
    fix = Path(__file__).parent / "fixtures" / "e7_p3_panel_text.txt"
    text = fix.read_text(encoding="utf-8").strip()
    assert "1/1" not in text, "本样本无表头污染（上枪误锚源）"
    assert _extract_ugr(text) == 29.6
    # 双样本同一函数同口径
    fix1 = Path(__file__).parent / "fixtures" / "e5_p5_panel_text.txt"
    assert _extract_ugr(fix1.read_text(encoding="utf-8").strip()) == 29.3


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
