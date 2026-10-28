"""TR-2a: ParseConfig roundtrip + header_insunits_to_units。"""
from pathlib import Path

from src.parser.dxf import ParseConfig, header_insunits_to_units, parse_dxf


def test_parse_config_roundtrip(tmp_path: Path):
    d = {
        "units": "mm",
        "join_tolerance_mm": 0.2,
        "luminaire_circle_radius_range": [7.0, 8.5],
        "room_edge_layers": ["0", "WALL"],
        "default_ceil_h": 2.8,
        "origin": [10.0, 20.0],
    }
    cfg = ParseConfig.from_dict(d)
    assert cfg.units == "mm"
    assert cfg.join_tolerance_mm == 0.2
    assert cfg.luminaire_circle_radius_range == (7.0, 8.5)
    assert cfg.default_ceil_h == 2.8
    assert cfg.origin == (10.0, 20.0)
    # 来回转换
    back = ParseConfig.from_dict(cfg.to_dict())
    assert back.luminaire_circle_radius_range == (7.0, 8.5)
    assert back.origin == (10.0, 20.0)
    # to_json/from_json
    f = tmp_path / "cfg.json"
    cfg.to_json(f)
    cfg2 = ParseConfig.from_json(f)
    assert cfg2.room_edge_layers == ["0", "WALL"]
    assert cfg2.luminaire_circle_radius_range == (7.0, 8.5)
    # 读取真实 fixture
    fix = Path(__file__).parent / "fixtures" / "sample_parse_config.json"
    real = ParseConfig.from_json(str(fix))
    assert real.units == "cm"
    assert real.units_from_header is False
    assert real.default_ceil_h == 2.8
    assert real.luminaire_circle_radius_range == (7.0, 8.5)
    assert real.join_tolerance_mm == 2.0
    assert real.auto_close_tolerance_mm == 4.0
    assert real.room_layers == ["0"]
    assert real.room_edge_layers == ["0"]


def test_header_insunits_mapping():
    assert header_insunits_to_units(4) == "mm"
    assert header_insunits_to_units(6) == "m"
    assert header_insunits_to_units(1) == "inch"
    assert header_insunits_to_units(5) == "cm"
    assert header_insunits_to_units(None) is None
    assert header_insunits_to_units(999) is None


# ── bulge 弧段采样（2026-10-28）：LWPOLYLINE 的弧原先被当成弦，圆形/弧形房间形状与面积全错 ──

def _area(poly):
    return abs(sum(poly[i][0] * poly[(i + 1) % len(poly)][1]
                   - poly[(i + 1) % len(poly)][0] * poly[i][1]
                   for i in range(len(poly))) / 2.0)


def _write_dxf(tmp_path: Path, rings, name="t.dxf"):
    """rings: list[list[(x, y, bulge)]]，每环一条闭合 LWPOLYLINE，画在图层 0。"""
    import ezdxf

    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4  # mm
    msp = doc.modelspace()
    for ring in rings:
        msp.add_lwpolyline([(x, y, 0, 0, b) for (x, y, b) in ring],
                           format="xyseb", close=True, dxfattribs={"layer": "0"})
    path = tmp_path / name
    doc.saveas(path)
    return path


def test_bulge_arc_room_area_is_真实面积(tmp_path: Path):
    """8m×4m + 顶边半圆（半径 4m）：真实面积 32 + π·4²/2 = 57.13 m²；按顶点当弦只有 32.00 m²。"""
    import math

    path = _write_dxf(tmp_path, [[(0, 0, 0), (8000, 0, 0), (8000, 4000, 1.0), (0, 4000, 0)]])
    ir = parse_dxf(str(path), ParseConfig())
    rooms = [s for s in ir["storeys"][0]["spaces"]
             if not str(s.get("name", "")).startswith("家具_")]
    assert len(rooms) == 1
    poly = rooms[0]["polygon"]
    assert len(poly) > 50, "弧段没被采样成折线"
    assert abs(_area(poly) - (32.0 + math.pi * 4.0 ** 2 / 2)) < 0.2


def test_bulge_full_circle_room(tmp_path: Path):
    """4 段 bulge 拼成正圆（半径 4m）：面积 π·4² = 50.27 m²；当弦只有 32.00 m²。"""
    import math

    b = math.tan(math.radians(90) / 4)
    ring = [(5000 + 4000 * math.cos(math.radians(a)),
             5000 + 4000 * math.sin(math.radians(a)), b) for a in (0, 90, 180, 270)]
    path = _write_dxf(tmp_path, [ring], name="circle.dxf")
    ir = parse_dxf(str(path), ParseConfig())
    rooms = [s for s in ir["storeys"][0]["spaces"]
             if not str(s.get("name", "")).startswith("家具_")]
    assert len(rooms) == 1
    assert abs(_area(rooms[0]["polygon"]) - math.pi * 4.0 ** 2) < 0.3


def test_no_bulge_polyline_unchanged(tmp_path: Path):
    """无 bulge 时必须与旧行为逐点一致：矩形仍是 4 个顶点、面积不变（回归保护）。"""
    path = _write_dxf(tmp_path, [[(0, 0, 0), (8000, 0, 0), (8000, 4000, 0), (0, 4000, 0)]],
                      name="rect.dxf")
    ir = parse_dxf(str(path), ParseConfig())
    rooms = [s for s in ir["storeys"][0]["spaces"]
             if not str(s.get("name", "")).startswith("家具_")]
    assert len(rooms) == 1
    poly = rooms[0]["polygon"]
    assert len(poly) == 4
    assert abs(_area(poly) - 32.0) < 1e-6


def test_bulge_circle_with_furniture_keeps_room(tmp_path: Path):
    """弧形房间与家具同存：家具端点不得把弧形房间环吃掉（评委原话「圆形含家具识别为零」）。"""
    import math

    import ezdxf

    b = math.tan(math.radians(90) / 4)
    ring = [(5000 + 4000 * math.cos(math.radians(a)),
             5000 + 4000 * math.sin(math.radians(a)), b) for a in (0, 90, 180, 270)]
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    msp.add_lwpolyline([(x, y, 0, 0, bb) for (x, y, bb) in ring], format="xyseb",
                       close=True, dxfattribs={"layer": "0"})
    msp.add_lwpolyline([(4000, 4300), (6000, 4300), (6000, 5700), (4000, 5700)],
                       close=True, dxfattribs={"layer": "家具"})
    path = tmp_path / "c.dxf"
    doc.saveas(path)
    ir = parse_dxf(str(path), ParseConfig())
    rooms = [s for s in ir["storeys"][0]["spaces"]
             if not str(s.get("name", "")).startswith("家具_")]
    assert len(rooms) == 1, f"弧形房间被吃掉：rooms={len(rooms)}"
    assert abs(_area(rooms[0]["polygon"]) - math.pi * 4.0 ** 2) < 0.3


def test_closed_lwpolyline_counts_as_closed(tmp_path: Path):
    """close=True 的 LWPOLYLINE 是隐式闭合（多边形不重复首点），闭合检查不能判它没闭合。"""
    path = _write_dxf(tmp_path, [[(0, 0, 0), (8000, 0, 0), (8000, 4000, 0), (0, 4000, 0)]],
                      name="closed.dxf")
    ir = parse_dxf(str(path), ParseConfig())
    assert ir["_meta"]["rooms_closed"] == 1


def test_meta_units_reflect_header_not_config_fallback(tmp_path: Path):
    """_meta.dxf_units 要写实际用的单位（header=mm），不是配置兜底的 cm。"""
    path = _write_dxf(tmp_path, [[(0, 0, 0), (8000, 0, 0), (8000, 4000, 0), (0, 4000, 0)]],
                      name="units.dxf")
    ir = parse_dxf(str(path), ParseConfig(units="cm"))
    assert ir["_meta"]["dxf_units"] == "mm"


def test_circle_entity_room(tmp_path: Path):
    """CAD 里直接用 CIRCLE 画圆墙的图纸：分支 A 要收（历史缺口，rooms 曾记 0）。"""
    import ezdxf
    import math

    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 4
    msp = doc.modelspace()
    msp.add_circle((4000, 4000), 3000, dxfattribs={"layer": "0"})
    msp.add_lwpolyline([(3800, 3800), (4600, 3800), (4600, 4600), (3800, 4600)],
                       close=True, dxfattribs={"layer": "0"})
    p = tmp_path / "circle_entity.dxf"
    doc.saveas(p)
    ir = parse_dxf(str(p), ParseConfig())
    rooms = [s for s in ir["storeys"][0]["spaces"]
             if not str(s.get("name", "")).startswith("家具_")]
    assert len(rooms) == 1, f"rooms={len(rooms)}"
    assert abs(_area(rooms[0]["polygon"]) - math.pi * 3.0 ** 2) < 0.2
