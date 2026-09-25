"""TR-1.1/1.2/1.3：scripts 层脚本测试（scan_dxf / dwg_to_dxf）。"""
from pathlib import Path

import pytest

from scripts.scan_dxf import scan_dxf
from scripts.dwg_to_dxf import resolve_oda_path


FIXTURE_ROOM = Path(__file__).parent / "fixtures" / "sample_room.dxf"
FIXTURE_LIGHT = Path(__file__).parent / "fixtures" / "sample_lighting.dxf"


def test_scan_lighting_30_circles():
    assert FIXTURE_LIGHT.exists()
    s = scan_dxf(FIXTURE_LIGHT)
    assert s["circle_radius_buckets"].get("8.3") == 30, s["circle_radius_buckets"]


def test_scan_room_bbox():
    s = scan_dxf(FIXTURE_ROOM)
    b = s["bbox_from_model_vertices"]
    assert b is not None
    assert abs(b["x_delta"] - 981.0) <= 50, b
    assert abs(b["y_delta"] - 1321.1) <= 50, b


def test_scan_room_line_and_arc_count():
    s = scan_dxf(FIXTURE_ROOM)
    layer0 = s["layer_entity_counts"].get("0", {})
    assert layer0.get("LINE", 0) + layer0.get("ARC", 0) >= 128, layer0


def test_resolve_oda_raises_helpful_on_missing(tmp_path, monkeypatch):
    # 若实际装了，就不能断言；所以只测试 override 指向不存在路径
    monkeypatch.delenv("ODA_PATH", raising=False)
    with pytest.raises(RuntimeError) as exc:
        resolve_oda_path(override=str(tmp_path / "nope" / "x.exe"))
    assert "ODA File Converter" in str(exc.value)
