"""FurnitureTask 离线契约：验证任务编排，不启动 DIALux。"""
from __future__ import annotations

from src.tasks.dialux.furniture_task import FurnitureTask
from src.workbench.task import TaskContext


def _ir():
    return {
        "storeys": [{
            "level": 1,
            "spaces": [{
                "id": "ROOM-1",
                "name": "会议室",
                "polygon": [[0, 0], [10, 0], [10, 8], [0, 8]],
                "ceil_h": 2.8,
                "luminaires": [],
                "furniture": [
                    {
                        "id": "TABLE-1",
                        "room_id": "ROOM-1",
                        "polygon": [[1, 1], [3, 1], [3, 2], [1, 2]],
                        "bbox": [1, 1, 3, 2],
                        "area_m2": 2.0,
                        "kind": "unknown",
                        "height_m": 0.75,
                        "rotation": 0.0,
                        "confidence": 1.0,
                    },
                    {
                        "id": "TABLE-2",
                        "room_id": "ROOM-1",
                        "polygon": [[4, 1], [6, 1], [6, 2], [4, 2]],
                        "bbox": [4, 1, 6, 2],
                        "area_m2": 2.0,
                        "kind": "unknown",
                        "height_m": 0.75,
                        "rotation": 0.0,
                        "confidence": 1.0,
                    },
                ],
            }],
        }],
    }


def test_task_places_one_furniture_and_returns_id_metrics():
    placed = []

    def place_fn(furniture):
        placed.append(furniture["id"])
        return True, "ok"

    result = FurnitureTask(ir=_ir(), limit=1, place_fn=place_fn).run(TaskContext())

    assert result.ok
    assert placed == ["TABLE-1"]
    assert result.metrics["placed_ids"] == ["TABLE-1"]


def test_task_fails_with_actionable_error_for_invalid_record():
    ir = _ir()
    del ir["storeys"][0]["spaces"][0]["furniture"][0]["room_id"]

    result = FurnitureTask(ir=ir, limit=1, place_fn=lambda _f: (True, "ok")).run(TaskContext())

    assert not result.ok
    assert "TABLE-1" in result.detail
    assert "room_id" in result.detail


def test_task_stops_on_cancel_before_placing():
    placed = []
    ctx = TaskContext(cancel_check=lambda: True)

    result = FurnitureTask(
        ir=_ir(),
        limit=1,
        place_fn=lambda furniture: placed.append(furniture["id"]) or (True, "ok"),
    ).run(ctx)

    assert not result.ok
    assert "停止" in result.detail
    assert placed == []


def test_task_stops_on_first_place_failure():
    placed = []

    def place_fn(furniture):
        placed.append(furniture["id"])
        return False, "UIA 坐标失败"

    result = FurnitureTask(ir=_ir(), limit=2, place_fn=place_fn).run(TaskContext())

    assert not result.ok
    assert placed == ["TABLE-1"]
    assert "TABLE-1" in result.detail
    assert "UIA 坐标失败" in result.detail
