"""P2 执行器内核测试：execute_plan 派发 / 重试 / HALT / 未知 type / 进度契约。

计划文档 P2 验收：
- 55 条动作全部被派发（用真实 IR 生成的 plan + 计数 driver）
- 未知 type 报错不静默跳过
- 统一重试上提到内核（RETRY → 重试；HALT → ExecutorHalted；超次 → RuntimeError）
- on_step 回调携带 title/weight，进度从 0 到 100
"""
import pytest

from src.executor.actions import ActionResult
from src.executor.kernel import ExecutorHalted, execute_plan
from src.planner.core import build_action_plan


class CountingDriver:
    """记录被派发的 type 序列；可配置每次返回什么。"""

    def __init__(self, result: ActionResult = "OK"):
        self.calls: list = []
        self.result = result
        self.fail_on_type: str | None = None

    def execute(self, action: dict) -> ActionResult:
        self.calls.append(action.get("type"))
        if self.fail_on_type and action.get("type") == self.fail_on_type:
            return "RETRY"
        return self.result


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


def test_every_action_in_plan_is_dispatched():
    """55 条（真实图规模）或任意 plan：每条动作都被派发一次、按顺序。"""
    ir = _ir(n_lums=28, n_spaces=1)  # 近似真实图：28 盏灯 + 建壳动作
    plan = build_action_plan(ir)
    assert len(plan) >= 32  # 1 project + 1 storey + 1 space + 28 lum + calc + report
    driver = CountingDriver()
    execute_plan(plan, driver)
    got = [a["type"] for a in plan]
    assert driver.calls == got, "派发顺序必须与 ActionPlan 一致，不能丢动作"


def test_unknown_action_type_raises_not_implemented():
    """未知 type：默认上抛（不静默跳过）；halt_on_unknown=False 才跳过。"""
    plan = [{"id": "a1", "type": "totally_new_op", "title": "x", "weight": 1.0}]

    class BadDriver:
        def execute(self, action):
            raise NotImplementedError(action["type"])

    with pytest.raises(NotImplementedError):
        execute_plan(plan, BadDriver())

    # 显式允许跳过时：记一条 ok=False 的事件并继续
    events = execute_plan(plan, BadDriver(), halt_on_unknown=False)
    assert len(events) == 1
    assert not events[0].ok
    assert events[0].detail == "unknown-type:totally_new_op"


def test_retry_is_in_kernel_not_handler():
    """RETRY 由内核统一重试，handler 只返回结果。"""
    plan = [{"id": "a1", "type": "create_space", "title": "建房间", "weight": 1.0}]
    driver = CountingDriver("RETRY")
    with pytest.raises(RuntimeError, match="aborted after 3 retries"):
        execute_plan(plan, driver, retry=3)
    # 3 次尝试全部落到 driver
    assert driver.calls == ["create_space"] * 3


def test_retry_succeeds_on_second_attempt():
    class Flaky:
        def __init__(self):
            self.n = 0

        def execute(self, action):
            self.n += 1
            return "OK" if self.n >= 2 else "RETRY"

    flaky = Flaky()
    plan = [{"id": "a1", "type": "create_space", "title": "建房间", "weight": 1.0}]
    events = execute_plan(plan, flaky)
    assert events[0].ok
    assert flaky.n == 2  # 第 1 次 RETRY，第 2 次 OK


def test_halt_raises_executor_halted():
    class HaltDriver:
        def execute(self, action):
            return "HALT"

    plan = [{"id": "a1", "type": "human_confirm", "title": "等人确认", "weight": 0.0}]
    with pytest.raises(ExecutorHalted):
        execute_plan(plan, HaltDriver())


def test_halt_stops_immediately_not_retried():
    """HALT 不是 RETRY：一次就停，不重试。"""
    class HaltDriver:
        def __init__(self):
            self.n = 0

        def execute(self, action):
            self.n += 1
            return "HALT"

    d = HaltDriver()
    plan = [{"id": "a1", "type": "human_confirm", "title": "x", "weight": 0.0}]
    with pytest.raises(ExecutorHalted):
        execute_plan(plan, d)
    assert d.n == 1


def test_progress_goes_0_to_100_and_events_carry_title_weight():
    plan = build_action_plan(_ir(n_lums=2, n_spaces=1))
    events = execute_plan(plan, CountingDriver())
    assert len(events) == len(plan)
    assert events[0].progress == pytest.approx(
        events[0].weight / sum(a["weight"] for a in plan) * 100.0)
    assert events[-1].progress == pytest.approx(100.0)
    for ev in events:
        assert ev.title, "事件必须带显示名（不能是空）"
        assert ev.weight >= 0.0
        assert ev.index == ev.action["id"] or ev.index >= 1
        assert ev.total == len(plan)


def test_empty_plan_returns_empty():
    assert execute_plan([], CountingDriver()) == []


def test_weight_defaults_to_type_and_1():
    """无 title/weight 的动作退化：title=type、weight=1.0（与 _stamp_progress 一致）。"""
    plan = [{"id": "a1", "type": "brand_new", "inputs": {}}]
    events = execute_plan(plan, CountingDriver())
    assert events[0].title == "brand_new"
    assert events[0].weight == 1.0
