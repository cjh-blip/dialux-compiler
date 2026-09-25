"""TR-5.3/5.4：执行器 dry-run / ProgramExecutor / KeyMouse 行为测试。"""
from __future__ import annotations


import pytest

from src.executor.key_mouse import (
    ProgramExecutor, KeyMouseExecutor, ExecutorHalted,
)
from src.planner.core import build_action_plan


def _ir_with_lum(catalog_match=True):
    return {
        "schema_version": "0.1",
        "project": {"name": "p", "source": {"dwg": "f.dxf"}, "units": "m"},
        "storeys": [{"level": 1, "spaces": [{
            "id": "R1", "polygon": [(0, 0), (10, 0), (10, 8), (0, 8), (0, 0)],
            "ceil_h": 2.8,
            "luminaires": [{
                "symbol": "L1", "x": 5, "y": 4, "z": 2.79,
                "catalog_match": catalog_match,
            }],
        }]}],
    }


def test_program_executor_runs_halt_with_input_yes(monkeypatch, caplog):
    ir = _ir_with_lum(catalog_match=False)  # 触发 HALT → human_confirm 插入
    plan = build_action_plan(ir)
    # 确保插入了 human_confirm
    assert any(a["type"] == "human_confirm" for a in plan)
    # 模拟用户输入 y
    monkeypatch.setattr("builtins.input", lambda prompt: "y")
    caplog.set_level("INFO")
    ProgramExecutor().execute(plan, dry_run=False)
    # 不应抛异常；完成后日志存在 DRY-RUN? No (dry_run=False 才到 execute)


def test_program_executor_halt_no(monkeypatch):
    ir = _ir_with_lum(catalog_match=False)
    plan = build_action_plan(ir)
    monkeypatch.setattr("builtins.input", lambda prompt: "n")
    with pytest.raises(ExecutorHalted):
        ProgramExecutor().execute(plan, dry_run=False)


def test_km_dump_on_fail(caplog):
    """TR-5.4：KeyMouseExecutor dry_run=False create_space 触发 RuntimeError，caplog 含 CONTEXT。"""
    # 构造一个最小 plan（只含一个 create_space 避免走其他分支）
    plan = [{
        "id": "a0001", "type": "create_space",
        "inputs": {"space_id": "R1", "level": 1,
                   "polygon": [(0, 0), (1, 0), (1, 1)],
                   "name": "x", "ceil_h": 2.8},
        "preconditions": [], "postconditions": [],
    }]
    with caplog.at_level("ERROR"):
        with pytest.raises(RuntimeError):
            KeyMouseExecutor().execute(plan, dry_run=False)
    logs = "\n".join(caplog.text.splitlines())
    assert "CONTEXT:" in logs or any(
        "CONTEXT:" in r.getMessage() for r in caplog.records
    ), f"日志：{logs[:500]}"
