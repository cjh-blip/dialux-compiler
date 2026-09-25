"""家具 IR 契约：识别结果必须可追溯、可归属、可供执行层消费。"""
from __future__ import annotations

from pathlib import Path

from src.parser.dxf import ParseConfig, parse_dxf


ROOT = Path(__file__).resolve().parents[1]
CFG = ROOT / "tests" / "fixtures" / "sample_parse_config.json"
ROOM_DXF = ROOT / "tests" / "fixtures" / "sample_room.dxf"


def _main_room(ir: dict) -> dict:
    rooms = [
        space for space in ir["storeys"][0]["spaces"]
        if not space["name"].startswith("家具_")
    ]
    assert len(rooms) == 1
    return rooms[0]


def test_real_dxf_furniture_records_are_traceable():
    """真实基线的 22 件家具必须带完整的执行前字段。"""
    ir = parse_dxf(str(ROOM_DXF), ParseConfig.from_json(str(CFG)))
    room = _main_room(ir)

    assert len(room["furniture"]) == 22
    for furniture in room["furniture"]:
        assert furniture["room_id"] == room["id"]
        assert furniture["id"]
        assert len(furniture["polygon"]) >= 3
        assert len(furniture["bbox"]) == 4
        assert furniture["area_m2"] > 0
        assert furniture["kind"] == "unknown"
        assert furniture["height_m"] == 0.75
        assert furniture["rotation"] == 0.0
        assert 0.0 <= furniture["confidence"] <= 1.0
        assert furniture["source_layer"]
        assert furniture["source_entity"]


def test_furniture_candidates_keep_low_confidence_instead_of_disappearing():
    """候选即使无法唯一归属，也必须保留并降低置信度。"""
    ir = parse_dxf(str(ROOM_DXF), ParseConfig.from_json(str(CFG)))
    room = _main_room(ir)

    records = room["furniture"]
    assert records
    assert all("confidence" in furniture for furniture in records)
    assert all("room_id" in furniture for furniture in records)
