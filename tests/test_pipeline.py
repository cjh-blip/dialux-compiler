"""端到端测试：构造内存 DXF → 解析 → 归属 → 校验 → ActionPlan。

保留原骨架测试并补 TR-5.1/5.2：test_action_plan_shape / test_human_confirm_inserted / test_cli_plan_output_jsonl（作为库内断言）。"""
from pathlib import Path

import ezdxf
import pytest

from src.parser.dxf import ParseConfig, extract_rooms, extract_luminaires
from src.planner.core import (
    assign_luminaires_to_spaces, build_action_plan, point_in_polygon,
)
from src.executor.actions import dump_plan, load_plan


@pytest.fixture
def dxf_doc():
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    msp.add_lwpolyline(
        [(0, 0), (10000, 0), (10000, 8000), (0, 8000), (0, 0)],
        dxfattribs={"layer": "ROOM"},
    )
    msp.add_blockref("LED-PNL-600", (5000, 4000, 2790), dxfattribs={"layer": "LUM"})
    return doc


def test_extract_room_and_luminaire(dxf_doc):
    # 明确 units_from_header=False：避免 ezdxf.new() 默认 $INSUNITS=6（m）覆盖我们的 cfg.units="mm"
    cfg = ParseConfig(room_layers=["ROOM"], luminaire_blocks=["LED"],
                      units="mm", units_from_header=False)
    rooms = extract_rooms(dxf_doc, cfg)
    assert len(rooms) == 1
    assert rooms[0].is_closed()

    lumis = extract_luminaires(dxf_doc, cfg)
    assert len(lumis) == 1
    assert lumis[0].x == pytest.approx(5.0)
    assert lumis[0].y == pytest.approx(4.0)
    assert lumis[0].z == pytest.approx(2.79)


def test_point_in_polygon():
    poly = [(0, 0), (10, 0), (10, 8), (0, 8)]
    assert point_in_polygon((5, 4), poly) is True
    assert point_in_polygon((11, 4), poly) is False
    # 边界点：也应返回 True
    assert point_in_polygon((0, 0), poly) is True
    assert point_in_polygon((5, 0), poly) is True


def test_assign_and_validate(dxf_doc):
    cfg = ParseConfig(room_layers=["ROOM"], luminaire_blocks=["LED"],
                      units="mm", units_from_header=False)
    ir = {
        "schema_version": "0.1",
        "project": {"name": "test", "source": {"dwg": "f"}, "units": "m"},
        "storeys": [{
            "level": 1,
            "spaces": [{
                "id": "R1", "name": "room1",
                "polygon": [[0, 0], [10, 0], [10, 8], [0, 8], [0, 0]],
                "ceil_h": 2.8, "luminaires": [],
            }],
        }],
    }
    lumis = extract_luminaires(dxf_doc, cfg)
    _warnings = assign_luminaires_to_spaces(ir, lumis)
    assert ir["storeys"][0]["spaces"][0]["luminaires"], "灯具应被归入房间"

    # 使用新 validator（避免 planner.core validate_ir DeprecationWarning 影响 pytest 输出）
    from src.validator import validate_ir as v2
    errors = [v for v in v2(ir) if v["severity"] in ("ERROR", "HALT")]
    assert errors == [], errors


def test_action_plan_shape():
    """TR-5.1：首条 action 5 字段齐全且 id 是 a0001；末两条是 run_calculation+export_report。"""
    ir = {
        "schema_version": "0.1",
        "project": {"name": "p", "source": {"dwg": "f"}, "units": "m"},
        "storeys": [{"level": 1, "spaces": [
            {"id": "R1", "polygon": [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]], "luminaires": []}
        ]}],
    }
    plan = build_action_plan(ir)
    assert plan[0]["id"] == "a0001"
    for fld in ("id", "type", "inputs", "preconditions", "postconditions"):
        assert fld in plan[0], f"缺失字段 {fld}"
    assert plan[-2]["type"] == "run_calculation"
    assert plan[-1]["type"] == "export_report"


def test_human_confirm_inserted():
    """TR-5.2：catalog_match=False → plan 至少有一条 human_confirm。"""
    ir = {
        "schema_version": "0.1",
        "project": {"name": "p", "source": {"dwg": "f"}, "units": "m"},
        "storeys": [{"level": 1, "spaces": [{
            "id": "R1", "polygon": [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]], "ceil_h": 2.8,
            "luminaires": [{
                "symbol": "BAD", "x": 0.5, "y": 0.5, "z": 2.79, "catalog_match": False,
            }]
        }]}],
    }
    plan = build_action_plan(ir)
    assert any(a["type"] == "human_confirm" for a in plan), plan


def test_cli_plan_output_jsonl(tmp_path: Path):
    """TR-5.5：JSONL 写出后按行 json.loads，条数 == len(plan)。"""
    ir = {
        "schema_version": "0.1",
        "project": {"name": "p", "source": {"dwg": "f"}, "units": "m"},
        "storeys": [{"level": 1, "spaces": [
            {"id": "R1", "polygon": [[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]], "luminaires": []}
        ]}],
    }
    plan = build_action_plan(ir)
    out = tmp_path / "plan.jsonl"
    dump_plan(plan, str(out))
    loaded = load_plan(str(out))
    assert len(loaded) == len(plan)
    for a in loaded:
        assert "id" in a and "type" in a
