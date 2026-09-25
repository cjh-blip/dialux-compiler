"""真实图端到端测试（spec FR-8 / AC-2 / TR-2b.3/2b.4）。"""
from __future__ import annotations

import json
import math
from pathlib import Path

import ezdxf
import pytest

from src.parser.dxf import ParseConfig, extract_rooms, extract_luminaires, parse_dxf
from src.parser._chain import polygon_area, count_short_edges
from src.planner.join import join_luminaires
from src.validator import validate_ir


CFG_PATH = Path(__file__).parent / "fixtures" / "sample_parse_config.json"
ROOM_DXF = Path(__file__).parent / "fixtures" / "sample_room.dxf"
LIGHT_DXF = Path(__file__).parent / "fixtures" / "sample_lighting.dxf"

#: 「锯齿边」阈值（米）：房间墙上短于此值的边只可能来自贴墙家具轮廓
SAW_EDGE_M = 0.2
#: 主房间北墙 y 坐标与真实墙线区间（米），来自 build/room_layout.json 数据诊断
NORTH_WALL_Y = 8.05
NORTH_WALL_X = (2.55, 9.74)


def _ring(poly):
    """去掉闭合重复点，返回 [(x, y), ...]。"""
    r = [(float(p[0]), float(p[1])) for p in poly]
    if len(r) > 2 and math.hypot(r[0][0] - r[-1][0], r[0][1] - r[-1][1]) < 1e-9:
        r.pop()
    return r


def _edges(ring):
    return [math.hypot(ring[(i + 1) % len(ring)][0] - ring[i][0],
                       ring[(i + 1) % len(ring)][1] - ring[i][1])
            for i in range(len(ring))]


def _main_room(ir):
    spaces = [s for s in ir["storeys"][0]["spaces"]
              if not s["name"].startswith("家具_")]
    assert spaces, "IR 里没有房间 space"
    return max(spaces, key=lambda s: polygon_area(s["polygon"]))


@pytest.fixture(scope="module")
def cfg():
    return ParseConfig.from_json(str(CFG_PATH))


def test_lighting_circles_30(cfg):
    """TR-2b.3：sample_lighting.dxf 的 CAD 层含 CIRCLE r=7.6 共 30 个实体，
    但真实图纸中多个 CIRCLE 被重复绘制在同一坐标（共 16 个唯一坐标）。
    extract_luminaires 同时抽取 16 个 CIRCLE + 12 个 LINE-矩形闭合环（共 28 盏唯一坐标灯具）。
    末尾 1mm 精度去重 → CIRCLE 去重 + RECT 自然唯一（LINE 环不会重复绘制）→ 返回 28。
    本测试保留"原始 DXF 含 ≥30 CIRCLE 实体"兜底断言，防止 fixture 退化。"""
    import ezdxf.entities
    doc = ezdxf.readfile(str(LIGHT_DXF))
    # 兜底：原始 DXF 中 r=7.6±0.1 的 CIRCLE 实体数应 ≥ 30
    raw_circles = [e for e in doc.modelspace().query("CIRCLE")
                   if isinstance(e, ezdxf.entities.Circle)
                   and 7.0 <= float(getattr(e.dxf, "radius", 0)) <= 8.5]
    assert len(raw_circles) >= 30, f"DXF CIRCLE 实体数 {len(raw_circles)} < 30"
    # 去重后的灯具数：唯一坐标 28（16 CIRCLE + 12 RECT）
    lumis = extract_luminaires(doc, cfg)
    assert 28 <= len(lumis) <= 42, f"去重后灯具数 {len(lumis)} 不在 [28,42]（30 CIRCLE 原始 + 12 RECT 原始 = 42）"
    coords = {(round(lum.x, 3), round(lum.y, 3)) for lum in lumis}
    assert len(coords) == len(lumis), "extract_luminaires 返回后内部仍有重复坐标"
    assert len(coords) == 28, f"唯一坐标数 {len(coords)}，期望 28（16 CIRCLE + 12 RECT）"
    # 类型分布断言：CIRCLE 16 + RECT 12
    from collections import Counter
    types = Counter(lum.symbol.split("-")[0] for lum in lumis)
    assert types.get("CIRCLE", 0) == 16, f"CIRCLE 灯数 {types.get('CIRCLE')} ≠ 16"
    assert types.get("RECT", 0) == 12, f"RECT 灯数 {types.get('RECT')} ≠ 12（LINE-矩形环分支未生效？）"
    # 4 行 × 7 列 矩阵验证（截图 4 行，列数 = 3 RECT col + 4 CIRCLE col = 7）
    xs = sorted({round(lum.x, 3) for lum in lumis})
    ys = sorted({round(lum.y, 3) for lum in lumis})
    assert len(xs) == 7, f"X 列数 {len(xs)} ≠ 7"
    assert len(ys) == 4, f"Y 行数 {len(ys)} ≠ 4"


def test_main_room_area_tolerance_30pct(cfg):
    """TR-2b.4 + AC-2：主房间面积 ∈ [73,136] m²（SOP 104.48 × ±30%）。"""
    doc = ezdxf.readfile(str(ROOM_DXF))
    rooms = extract_rooms(doc, cfg)
    assert len(rooms) >= 1, "抽房间数为 0（LINE+ARC 拼接失败）"
    areas = [(r, polygon_area(r.polygon)) for r in rooms]
    areas.sort(key=lambda x: x[1], reverse=True)
    main_room, main_area = areas[0]
    # AC-2：73~136 m²
    assert 73.0 <= main_area <= 136.0, f"主房间面积 {main_area:.2f} m² 不在 [73,136] 内；全部房间面积:{[f'{a:.2f}' for _,a in areas]}"
    # 所有房间闭合（gap ≤ 1mm 米制）
    for r, _ in areas:
        assert r.is_closed(), f"房间 {r.id} 未闭合"
    # bbox 长宽相对 SOP 11.9×8.78m 差 ≤0.5m
    xs = [p[0] for p in main_room.polygon]
    ys = [p[1] for p in main_room.polygon]
    W = max(xs) - min(xs)
    H = max(ys) - min(ys)
    assert abs(W - 11.9) <= 0.5, f"主房间宽度 {W:.2f} vs SOP 11.9"
    assert abs(H - 8.78) <= 0.5, f"主房间深度 {H:.2f} vs SOP 8.78"


def test_validator_no_halt_on_sample_room(cfg):
    """AC-3：sample_room 解析后 validator 无 HALT（允许 WARNING 小面积退化环）。"""
    ir = parse_dxf(str(ROOM_DXF), cfg)
    # 另外把灯具也挂入（从灯具图抽）
    ldoc = ezdxf.readfile(str(LIGHT_DXF))
    lumis = extract_luminaires(ldoc, cfg)
    join_luminaires(ir, lumis)
    viols = validate_ir(ir)
    halts = [v for v in viols if v.get("severity") == "HALT"]
    assert halts == [], f"HALT: {halts}"


def test_luminaire_extract_from_room_dxf_ge25(cfg):
    """AC-8 集成：灯具图去重后灯具数 = 28（16 CIRCLE 唯一 + 12 RECT），原始 DXF CIRCLE 实体 ≥25 防退化。"""
    doc = ezdxf.readfile(str(LIGHT_DXF))
    raw_circles = sum(1 for e in doc.modelspace().query("CIRCLE")
                      if 7.0 <= float(getattr(e.dxf, "radius", 0)) <= 8.5)
    assert raw_circles >= 25, f"原始 DXF CIRCLE 实体 {raw_circles} < 25（fixture 退化？）"
    n = len(extract_luminaires(doc, cfg))
    # 16 CIRCLE 唯一 + 12 RECT = 28；留 ± 2 容差给底层拼接容差微调
    assert 26 <= n <= 30, f"去重后灯具数 {n} 异常（期望 ~28）"


def test_end2end_builds_room_layout(tmp_path: Path, cfg):
    """TR-6.1 集成：对 sample_room.dxf 单独 parse，输出 JSON _meta.rooms >= 1。"""
    ir = parse_dxf(str(ROOM_DXF), cfg)
    assert ir["_meta"]["rooms"] >= 1
    (tmp_path / "room_layout.json").write_text(
        json.dumps(ir, ensure_ascii=False, indent=2), encoding="utf-8"
    )


# ---------- 房间环不得混入家具边（柜子变墙修复，t_0deee369）----------

def test_room_ring_has_no_sawtooth(cfg):
    """AC-1：真实图主房间环上不得有 < 0.2m 的锯齿边。

    贴墙柜的进深只有 6.5~15cm，混进房间环就一定留下这种短边；墙线本身是
    0.5m 以上的整段。所以「最小边长 > 0.2m」等价于「柜子轮廓没被当成墙」。
    """
    ir = parse_dxf(str(ROOM_DXF), cfg)
    room = _main_room(ir)
    ring = _ring(room["polygon"])
    edges = _edges(ring)
    short = [(i, round(e, 3)) for i, e in enumerate(edges) if e < SAW_EDGE_M]
    assert not short, (
        f"房间 {room['id']} 环上有 {len(short)} 条锯齿边 {short[:8]}；"
        f"顶点={len(ring)} 面积={polygon_area(ring):.2f} m²"
    )
    assert count_short_edges(room["polygon"], SAW_EDGE_M) == 0


def test_north_wall_is_one_straight_run(cfg):
    """AC-2：北墙 y=8.05 从 x=2.55 到 9.74 必须是一条边（中间无凸台/凹槽顶点）。

    修复前这一段被 5 组柜子锯齿切成 20+ 顶点（见任务书数据诊断）。
    """
    ir = parse_dxf(str(ROOM_DXF), cfg)
    ring = _ring(_main_room(ir)["polygon"])
    x_lo, x_hi = NORTH_WALL_X
    runs = []
    for i in range(len(ring)):
        p, q = ring[i], ring[(i + 1) % len(ring)]
        if abs(p[1] - NORTH_WALL_Y) < 0.02 and abs(q[1] - NORTH_WALL_Y) < 0.02:
            lo, hi = sorted((p[0], q[0]))
            runs.append((round(lo, 3), round(hi, 3)))
    covering = [r for r in runs if r[0] <= x_lo + 0.01 and r[1] >= x_hi - 0.01]
    assert covering, f"北墙 y={NORTH_WALL_Y} 没有覆盖 [{x_lo},{x_hi}] 的单边；实际分段={runs}"
    # 北墙线上不该再有中间顶点
    mids = [p for p in ring
            if abs(p[1] - NORTH_WALL_Y) < 0.02 and x_lo + 0.01 < p[0] < x_hi - 0.01]
    assert not mids, f"北墙上仍有中间顶点 {[(round(x, 3), round(y, 3)) for x, y in mids]}"


def test_all_walls_free_of_furniture_notches(cfg):
    """AC-3：任务书点名的四面墙锯齿全部消失（不只修北墙）。

    - 东墙 x=11.9：柜列 LINEARC_001/002/003 造出的 11.45/11.9 锯齿
    - 西墙 x=0：LINEARC_012 造出的 0.34 凸台 + 0.075 台阶
    - 南墙 y=0 的 7.5→8.3 凸台是**房间自身形状**（0.77m 深、0.8m 宽，非家具），必须保留
    """
    ir = parse_dxf(str(ROOM_DXF), cfg)
    ring = _ring(_main_room(ir)["polygon"])

    east_mid = [p for p in ring if 11.3 < p[0] < 11.89 and 4.0 < p[1] < 7.5]
    assert not east_mid, f"东墙柜列锯齿仍在：{[(round(x, 3), round(y, 3)) for x, y in east_mid]}"

    west_mid = [p for p in ring if 0.02 < p[0] < 0.5 and 6.9 < p[1] < 8.3]
    assert not west_mid, f"西墙 0.34/0.075 凸台仍在：{[(round(x, 3), round(y, 3)) for x, y in west_mid]}"

    # 南墙真实凸台（0.77 m² > 0.5 m² 阈值）不能被误删
    step = [p for p in ring if abs(p[1] - 0.77) < 0.02 and 7.4 < p[0] < 8.4]
    assert len(step) == 2, f"南墙 0.77m 凸台被误删（应留 2 个顶点，实得 {len(step)}）"


def test_room_area_grew_after_notch_removal(cfg):
    """AC-4：补平柜子凹槽后房间面积必须增大（93.63 → 真实墙围面积）。"""
    ir_fixed = parse_dxf(str(ROOM_DXF), cfg)
    cfg_raw = ParseConfig.from_json(str(CFG_PATH))
    cfg_raw.wall_ring_pass = False
    cfg_raw.smooth_room_rings = False
    ir_raw = parse_dxf(str(ROOM_DXF), cfg_raw)

    a_fixed = polygon_area(_main_room(ir_fixed)["polygon"])
    a_raw = polygon_area(_main_room(ir_raw)["polygon"])
    assert a_fixed > a_raw, f"面积未增大：修复前 {a_raw:.2f} → 修复后 {a_fixed:.2f} m²"
    # 上限：不能超过 bbox 满铺（11.9 × 8.78 = 104.48 m²）
    assert a_fixed <= 104.5, f"面积 {a_fixed:.2f} m² 超过 bbox 满铺，凹槽剔除过头了"


def test_furniture_not_regressed(cfg):
    """AC-5：22 个家具仍被识别为 furniture，没有因为房间环换人而丢失。"""
    ir = parse_dxf(str(ROOM_DXF), cfg)
    assert ir["_meta"]["rooms"] == 1, f"房间数变了：{ir['_meta']}"
    assert ir["_meta"]["furniture"] == 22, f"家具数变了：{ir['_meta']}"
    assert ir["_meta"]["rooms_with_sawtooth"] == 0, f"仍有带锯齿的房间：{ir['_meta']}"
    room = _main_room(ir)
    assert len(room["furniture"]) == 22
    furn_spaces = [s for s in ir["storeys"][0]["spaces"]
                   if s["name"].startswith("家具_")]
    assert len(furn_spaces) == 22


def test_furniture_inside_room_and_not_crossing(cfg):
    """AC-6：每个家具环完整落在房间内，且房间边不与家具边真交叉。

    房间环若还在柜子处挖洞，柜子顶点就会落到房间外 / 两环会互相穿越。
    """
    ir = parse_dxf(str(ROOM_DXF), cfg)
    room = _main_room(ir)
    ring = _ring(room["polygon"])

    def inside(pt):
        x, y = pt
        n = len(ring)
        for i in range(n):
            x1, y1 = ring[i]
            x2, y2 = ring[(i + 1) % n]
            # 落在边上视为内部
            if abs((x2 - x1) * (y - y1) - (y2 - y1) * (x - x1)) < 1e-6 \
                    and min(x1, x2) - 1e-9 <= x <= max(x1, x2) + 1e-9 \
                    and min(y1, y2) - 1e-9 <= y <= max(y1, y2) + 1e-9:
                return True
        hit = False
        for i in range(n):
            x1, y1 = ring[i]
            x2, y2 = ring[(i + 1) % n]
            if (y1 > y) != (y2 > y):
                if x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                    hit = not hit
        return hit

    outside = [(f["id"], v) for f in room["furniture"]
               for v in _ring(f["polygon"]) if not inside(v)]
    assert not outside, f"{len(outside)} 个家具顶点落在房间外：{outside[:5]}"

    def crosses(a0, a1, b0, b1):
        dax, day = a1[0] - a0[0], a1[1] - a0[1]
        dbx, dby = b1[0] - b0[0], b1[1] - b0[1]
        den = dax * dby - dbx * day
        if abs(den) < 1e-12:
            return False
        t1 = ((b0[0] - a0[0]) * dby - (b0[1] - a0[1]) * dbx) / den
        t2 = ((b0[0] - a0[0]) * day - (b0[1] - a0[1]) * dax) / den
        return 1e-9 < t1 < 1 - 1e-9 and 1e-9 < t2 < 1 - 1e-9

    hits = []
    for i in range(len(ring)):
        a0, a1 = ring[i], ring[(i + 1) % len(ring)]
        for f in room["furniture"]:
            fr = _ring(f["polygon"])
            for j in range(len(fr)):
                if crosses(a0, a1, fr[j], fr[(j + 1) % len(fr)]):
                    hits.append((f["id"], i, j))
    assert not hits, f"房间边与家具边真交叉 {len(hits)} 处：{hits[:5]}"


def test_wall_ring_pass_can_be_disabled(cfg):
    """开关可关：wall_ring_pass=False 时不再产出 WALLRING_* 候选（回退到旧行为）。"""
    doc = ezdxf.readfile(str(ROOM_DXF))
    cfg_off = ParseConfig.from_json(str(CFG_PATH))
    cfg_off.wall_ring_pass = False
    ids_off = {r.id for r in extract_rooms(doc, cfg_off)}
    assert not any(i.startswith("WALLRING_") for i in ids_off)

    ids_on = {r.id for r in extract_rooms(doc, cfg)}
    assert any(i.startswith("WALLRING_") for i in ids_on), "墙线环 pass 没产出候选"


def test_smooth_alone_fixes_sawtooth(cfg):
    """兜底路径：即使拼不出墙线环候选，平滑也能独立把锯齿清干净。

    保证修复不是只靠「换一个更好的环」这一条路 —— 图纸把墙画成多段时仍然有效。
    """
    cfg_smooth_only = ParseConfig.from_json(str(CFG_PATH))
    cfg_smooth_only.wall_ring_pass = False
    cfg_smooth_only.smooth_room_rings = True
    ir = parse_dxf(str(ROOM_DXF), cfg_smooth_only)
    room = _main_room(ir)
    assert count_short_edges(room["polygon"], SAW_EDGE_M) == 0, \
        f"仅平滑时仍有锯齿：{room['id']} 顶点={len(room['polygon'])}"
    assert ir["_meta"]["room_notches_removed"] >= 1
    assert ir["_meta"]["furniture"] == 22
