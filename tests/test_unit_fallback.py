"""量纲兜底：header $INSUNITS 撒谎时，主解析读不出房间就先按大一档量级重试。

背景（2026-10-28 缺陷 5）：示例图纸的 header 写 `$INSUNITS=4`（mm），几何实际按 cm 画。
只信 header 的调用方（平台 `service.import_dxf` 不给 config）读到 0 房间、房间全被当家具；
而独立版链路钉死 `units=cm`，读出 97.66 m²。同一份字节两个结论，差的只有配置。
"""
from pathlib import Path

import ezdxf
import pytest

from src.parser.dxf import ParseConfig, parse_dxf

FIXTURES = Path(__file__).resolve().parent / "fixtures"
ROOM_DXF = FIXTURES / "sample_room.dxf"
CFG_PATH = FIXTURES / "sample_parse_config.json"


def _make_room_dxf(path: Path, *, insunits: int, w: float, h: float) -> Path:
    """造一张只有一圈矩形墙线的平面图，header 单位由调用方指定。"""
    doc = ezdxf.new("R2010")
    doc.header["$INSUNITS"] = insunits
    msp = doc.modelspace()
    corners = [(0.0, 0.0), (w, 0.0), (w, h), (0.0, h), (0.0, 0.0)]
    for start, end in zip(corners, corners[1:]):
        msp.add_line(start, end, dxfattribs={"layer": "0"})
    doc.saveas(str(path))
    return path


def _main_room(ir: dict) -> dict:
    for storey in ir["storeys"]:
        for space in storey["spaces"]:
            if not str(space["name"]).startswith("家具_"):
                return space
    raise AssertionError("IR 里没有房间")


def test_header_lies_about_mm_falls_back_to_cm():
    """真实样例：header 说 mm、几何是 cm。默认配置也要读出那间房，并标明兜底出处。"""
    ir = parse_dxf(str(ROOM_DXF))
    meta = ir["_meta"]

    assert meta["rooms"] == 1, meta
    assert meta["units_source"] == "geometry_fallback", meta
    assert meta["units_header"] == "mm", meta
    assert meta["dxf_units"] == "cm", meta
    assert "退化噪声" in meta["units_fallback_reason"], meta
    room = _main_room(ir)
    assert len(room["polygon"]) == 17
    assert meta["rooms_with_sawtooth"] == 0


def test_fallback_lands_on_same_room_as_pinned_config():
    """兜底算出的房间必须和「钉死 units=cm」那条路同一间房（几何逐点相同）。"""
    ir_auto = parse_dxf(str(ROOM_DXF))
    ir_pinned = parse_dxf(str(ROOM_DXF), ParseConfig.from_json(str(CFG_PATH)))

    assert ir_auto["_meta"]["units_source"] == "geometry_fallback"
    assert ir_pinned["_meta"]["units_source"] == "config"
    auto_room, pinned_room = _main_room(ir_auto), _main_room(ir_pinned)
    assert auto_room["id"] == pinned_room["id"]
    assert auto_room["polygon"] == pinned_room["polygon"]


def test_pinned_config_does_not_fall_back():
    """调用方钉死单位时不许兜底：配置是显式意图，改它就是篡改。"""
    ir = parse_dxf(str(ROOM_DXF), ParseConfig.from_json(str(CFG_PATH)))
    assert ir["_meta"]["units_source"] == "config"
    assert ir["_meta"]["dxf_units"] == "cm"
    assert "units_fallback_reason" not in ir["_meta"]


def test_genuine_mm_small_room_not_rescaled(tmp_path: Path):
    """真的是 mm 画的小房间（1.5×1.2 m = 1.8 m²，够不上 20 m² 门槛）不许被当 cm 放大。

    这张图的 header 是对的，只是房间小到被算成家具；兜底的守卫要挡住它。
    """
    path = _make_room_dxf(tmp_path / "small_mm.dxf", insunits=4, w=1500.0, h=1200.0)
    ir = parse_dxf(str(path))
    meta = ir["_meta"]

    assert meta["rooms"] == 0, meta
    assert meta["units_source"] == "header", meta
    assert meta["dxf_units"] == "mm", meta
    assert "units_fallback_reason" not in meta


def test_header_unit_is_what_gets_reported(tmp_path: Path):
    """`_meta.dxf_units` 报实际使用的单位，不报 cfg.units（header 说 cm、cfg 默认 mm 时不能报 mm）。"""
    path = _make_room_dxf(tmp_path / "cm_room.dxf", insunits=5, w=1200.0, h=900.0)
    ir = parse_dxf(str(path))
    meta = ir["_meta"]

    assert meta["rooms"] == 1, meta
    assert meta["dxf_units"] == "cm", meta
    assert meta["units_source"] == "header", meta


def test_no_header_unit_reports_config_fallback(tmp_path: Path):
    """header 没声明单位时退回 cfg.units，出处要标 config_fallback（不再假装识别成功）。"""
    path = _make_room_dxf(tmp_path / "no_insunits.dxf", insunits=0, w=12000.0, h=9000.0)
    ir = parse_dxf(str(path), ParseConfig())
    meta = ir["_meta"]
    assert meta["rooms"] == 1, meta
    assert meta["units_source"] == "config_fallback", meta
    assert meta["dxf_units"] == "mm", meta


@pytest.mark.parametrize("header_units,raw", [("mm", 4), ("cm", 5), ("m", 6)])
def test_implied_span_in_range_blocks_fallback(tmp_path: Path, header_units: str, raw: int):
    """量级本来就对、只是读不出房间的图，不许被换量级重跑。"""
    # 12 m × 9 m 的平面：按 header 说得通的量级画，跨度都在 2~500 m 带内
    factor = {"mm": 1000.0, "cm": 100.0, "m": 1.0}[header_units]
    path = _make_room_dxf(tmp_path / f"ok_{header_units}.dxf", insunits=raw,
                          w=12.0 * factor, h=9.0 * factor)
    ir = parse_dxf(str(path))
    assert ir["_meta"]["rooms"] == 1
    assert ir["_meta"]["units_source"] == "header"
