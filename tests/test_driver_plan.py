"""P2 UiaDriver 测试：ActionPlan 动作分发到 STF 批量通道 + place_luminaire 通道。

验收（计划文档 P2 step 2）：
- 55 条动作全部被派发（kernel + driver 串联）
- create_space 走 STF 批量通道：第一个触发 ir_to_stf + import，后续幂等
- place_luminaire：stub 收集坐标（离线安全）或 arrangement 真通道
  （2026-09-07 产品化：导入 IES + ArrangementFromSpace 排布；缺 IES 跳过不崩）
- 依赖注入：测试用假 import_fn / place_fn，不碰真机
"""
from pathlib import Path

import pytest

from src.executor.kernel import execute_plan
from src.executor.uia.driver import StepEvent
from src.executor.uia.driver_plan import UiaDriver
from src.planner.core import build_action_plan


def _ir(n_lums=2, n_spaces=1):
    return {
        "project": {"name": "T"},
        "storeys": [{
            "level": 1,
            "elevation": 0.0,
            "spaces": [{
                "id": f"S{i}",
                "name": f"房间{i}",
                "polygon": [[0, 0], [6, 0], [6, 6], [0, 6]],
                "ceil_h": 2.8,
                "luminaires": [
                    {"symbol": f"L{j}", "x": 1.0 + j, "y": 1.0, "z": 2.8,
                     "catalog_match": True, "kind": "point"}
                    for j in range(n_lums)
                ],
            } for i in range(n_spaces)],
        }],
    }


def _fake_import(stf_path):
    """假导入：什么都不干，返回一组成功的 StepEvent（模拟 run_import 契约）。"""
    return [
        StepEvent("attach", "挂上", True, "", 10.0),
        StepEvent("done", "完成", True, "", 100.0),
    ]


def test_full_plan_dispatched_via_kernel():
    """55 条量级 plan：kernel 派发到 UiaDriver，全部事件 ok。"""
    ir = _ir(n_lums=28, n_spaces=1)
    plan = build_action_plan(ir)
    driver = UiaDriver(ir, import_fn=_fake_import)
    events = execute_plan(plan, driver)
    assert len(events) == len(plan)
    assert all(e.ok for e in events), [e.detail for e in events if not e.ok]
    assert events[-1].progress == pytest.approx(100.0)
    # 28 盏灯全部被收集（stub 语义：记录了输入）
    assert len(driver.luminaires) == 28
    assert len(driver.created_spaces) == 1


def test_stf_import_happens_exactly_once():
    """多个 create_space：STF 整批只导入一次，后续幂等。"""
    ir = _ir(n_lums=1, n_spaces=3)
    plan = build_action_plan(ir)
    calls = []

    def spy_import(stf_path):
        calls.append(stf_path)
        return _fake_import(stf_path)

    driver = UiaDriver(ir, import_fn=spy_import)
    execute_plan(plan, driver)
    assert len(calls) == 1, "STF 必须整批导入一次，不能每个房间导一次"
    assert driver.stf_path.exists()
    assert driver.stf_path.read_text(encoding="gbk").strip()


def test_stf_text_contains_room_coords():
    """生成的 STF 文本含房间顶点（6x6 方房），证明走的是真实导出器。"""
    ir = _ir(n_lums=0)
    driver = UiaDriver(ir, import_fn=_fake_import)
    plan = build_action_plan(ir)
    execute_plan(plan, driver)
    text = driver.stf_path.read_text(encoding="gbk")
    assert "6" in text  # 房间边长 6 米的坐标会出现在 STF 里


def test_furniture_pseudo_spaces_not_exported():
    """家具伪 space（name 以 家具_ 开头）不导出 STF，但仍被幂等确认。"""
    ir = {
        "project": {"name": "T"},
        "storeys": [{"level": 1, "elevation": 0.0, "spaces": [
            {"id": "S1", "name": "房间1",
             "polygon": [[0, 0], [6, 0], [6, 6], [0, 6]], "ceil_h": 2.8},
            {"id": "F1", "name": "家具_柜子",
             "polygon": [[1, 1], [2, 1], [2, 2], [1, 2]], "ceil_h": 0},
        ]}],
    }
    plan = build_action_plan(ir)
    driver = UiaDriver(ir, import_fn=_fake_import)
    events = execute_plan(plan, driver)
    assert all(e.ok for e in events)
    # 两个 create_space 都被确认
    assert len(driver.created_spaces) == 2


def test_place_luminaire_stub_collects_inputs_not_claims_landed():
    """stub 通道：坐标进 luminaires，且事件 ok（语义=已派发，不是已落地）。"""
    ir = _ir(n_lums=2)
    plan = build_action_plan(ir)
    driver = UiaDriver(ir, import_fn=_fake_import)
    execute_plan(plan, driver)
    assert [li["luminaire_id"] for li in driver.luminaires] == ["L0", "L1"]
    assert all("x" in li and "y" in li and "z" in li for li in driver.luminaires)


def test_unknown_channel_raises():
    """luminaire_channel 非 stub/arrangement：明确报错，不静默。"""
    ir = _ir(n_lums=1)
    driver = UiaDriver(ir, import_fn=_fake_import, luminaire_channel="bogus")
    plan = build_action_plan(ir)
    with pytest.raises(NotImplementedError, match="bogus"):
        execute_plan(plan, driver)


def test_arrangement_channel_skips_missing_ies_not_raises():
    """arrangement 真通道：symbol 找不到 IES 文件时记告警跳过（返回 OK），
    不因单盏缺文件把整批计划带崩。2026-09-07 后 arrangement 不再是占位。"""
    ir = _ir(n_lums=2)  # symbol L0/L1，build/ies/ 下无精确匹配（短 id 不做子串）
    plan = build_action_plan(ir)

    def fake_place(ies, inputs):
        raise AssertionError("不应调用真机 place（symbol 无匹配 IES）")

    driver = UiaDriver(ir, import_fn=_fake_import, luminaire_channel="arrangement",
                       place_fn=fake_place)
    events = execute_plan(plan, driver)
    assert all(e.ok for e in events)
    assert len(driver.luminaires) == 2


@pytest.mark.skipif(
    not (Path(__file__).resolve().parents[1] / "build" / "ies" / "NPTLED351_NVC.IES").exists(),
    reason="build/ies/ 是运行产物（gitignore），缺少 IES 文件时跳过")
def test_arrangement_channel_uses_injected_place_fn(monkeypatch):
    """注入 place_fn 后 arrangement 走注入函数（测试不碰真机）。"""
    ir = _ir(n_lums=1)
    # 给 symbol 配一个确实存在的 IES（精确匹配 build/ies/ 根目录 NPTLED351_NVC.IES）
    ir["storeys"][0]["spaces"][0]["luminaires"][0]["symbol"] = "NPTLED351_NVC.IES"
    plan = build_action_plan(ir)
    calls = []

    def fake_place(ies, inputs):
        calls.append((str(ies), inputs))
        return True, "ok"

    driver = UiaDriver(ir, import_fn=_fake_import, luminaire_channel="arrangement",
                       place_fn=fake_place)
    events = execute_plan(plan, driver)
    assert all(e.ok for e in events)
    assert len(calls) == 1
    assert "NPTLED351" in calls[0][0]


def test_short_symbol_does_not_substring_match_linear():
    """短 id（如 L1）不做 linear/* 子串匹配，避免误中 LEDLima-L12 之类。"""
    from src.executor.uia.driver_plan import UiaDriver
    d = UiaDriver({}, luminaire_channel="stub")
    assert d._resolve_luminaire_ies("L1", {}) is None
    assert d._resolve_luminaire_ies("X1", {}) is None


def test_import_failure_returns_retry_then_kernel_raises():
    """STF 导入失败：driver 返回 RETRY，kernel 重试到上限后抛 RuntimeError。"""
    ir = _ir(n_lums=0)
    plan = build_action_plan(ir)

    def bad_import(stf_path):
        return [StepEvent("attach", "挂上", False, "no-window-process", 10.0)]

    driver = UiaDriver(ir, import_fn=bad_import)
    with pytest.raises(RuntimeError, match="aborted after 3 retries"):
        execute_plan(plan, driver)
