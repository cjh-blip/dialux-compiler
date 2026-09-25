"""灯具分类（kind）与挂载高度（z）回填测试。

背景：2026-09-05 的 evo 14.0 真机验证暴露两个洞 ——
1. 解析出的 28 盏灯 z 全是 0（趴在楼面），validator 规则 4 只查上溢，z=0 静默通过；
2. 16 盏筒灯与 12 盏线性灯混在一个未区分的列表里，下游只能靠 symbol 前缀猜类型。
本文件把这两条钉住，并覆盖顺手修掉的 radius_mm 单位错误。
"""
from __future__ import annotations

import pytest

from src.parser.dxf import LINEAR_ASPECT_MIN, Luminaire, classify_rect_luminaire
from src.planner.join import join_luminaires
from src.planner.mount import (
    DEFAULT_PENDANT_DROP_M,
    assign_mount_heights,
    count_unset_z,
)
from src.validator import validate_ir


def _room(luminaires, ceil_h=2.8, sid="R1"):
    """造一个 6×6 m 单房间 IR；polygon 闭合、面积 36 m² 落在 validator 的合法区间。"""
    return {
        "schema_version": "1.0",
        "project": {"name": "t"},
        "storeys": [{
            "level": 1,
            "spaces": [{
                "id": sid,
                "polygon": [[0, 0], [6, 0], [6, 6], [0, 6], [0, 0]],
                "ceil_h": ceil_h,
                "luminaires": luminaires,
            }],
        }],
    }


# --------------------------------------------------------------------------
# classify_rect_luminaire：长宽比分类
# --------------------------------------------------------------------------

@pytest.mark.parametrize("w,h,expected", [
    (1555.0, 300.0, "linear"),   # 实测图纸的线性灯具，5.18:1
    (300.0, 1555.0, "linear"),   # 与摆放方向无关
    (1200.0, 300.0, "linear"),   # 4:1，DIALux 目录里也算线性灯具
    (600.0, 600.0, "area"),      # 正方形面板灯
    (600.0, 300.0, "area"),      # 2:1，仍算面板
    (900.0, 300.0, "linear"),    # 恰好 3:1，等于阈值 → 归 linear
    (0.0, 300.0, "unknown"),     # 退化尺寸
    (-1.0, 300.0, "unknown"),
])
def test_classify_rect(w, h, expected):
    assert classify_rect_luminaire(w, h) == expected


def test_linear_aspect_threshold_is_inclusive():
    """阈值边界：恰好等于 LINEAR_ASPECT_MIN 判 linear，略小于则判 area。"""
    short = 100.0
    assert classify_rect_luminaire(short * LINEAR_ASPECT_MIN, short) == "linear"
    assert classify_rect_luminaire(short * (LINEAR_ASPECT_MIN - 0.01), short) == "area"


# --------------------------------------------------------------------------
# join：kind 与 dims 必须带进 IR（此前 attrs 被整个丢掉）
# --------------------------------------------------------------------------

def test_join_carries_kind_and_dims():
    ir = _room([])
    lumis = [
        Luminaire("CIRCLE-r7.6-0", x=2.0, y=2.0, kind="point",
                  attrs={"radius_mm": 76.0, "layer": "LIGHT"}),
        Luminaire("RECT-1555.0x300.0-0", x=4.0, y=4.0, kind="linear",
                  attrs={"rect_w_mm": 1555.0, "rect_h_mm": 300.0}),
    ]
    join_luminaires(ir, lumis)
    got = ir["storeys"][0]["spaces"][0]["luminaires"]
    assert [x["kind"] for x in got] == ["point", "linear"]
    assert got[0]["dims"] == {"radius_mm": 76.0}
    assert got[1]["dims"] == {"w_mm": 1555.0, "h_mm": 300.0}
    # layer 不是选型尺寸，不应混进 dims
    assert "layer" not in got[0]["dims"]


def test_join_rounds_float_noise_in_dims():
    """浮点换算噪声要圆掉，否则同型号灯具的 dims 不相等，无法分组。"""
    ir = _room([])
    lumis = [
        Luminaire("A", x=1.0, y=1.0, kind="linear",
                  attrs={"rect_w_mm": 1555.0000000000014, "rect_h_mm": 300.0000000000006}),
        Luminaire("B", x=2.0, y=2.0, kind="linear",
                  attrs={"rect_w_mm": 1555.0, "rect_h_mm": 300.0}),
    ]
    join_luminaires(ir, lumis)
    a, b = ir["storeys"][0]["spaces"][0]["luminaires"]
    assert a["dims"] == b["dims"] == {"w_mm": 1555.0, "h_mm": 300.0}


def test_join_omits_dims_when_no_size_known():
    """INSERT 块引用没有尺寸 → 不写 dims 字段，而不是写个空 dict。"""
    ir = _room([])
    join_luminaires(ir, [Luminaire("BLOCK_A", x=3.0, y=3.0, kind="unknown", attrs={"tag": "x"})])
    lum = ir["storeys"][0]["spaces"][0]["luminaires"][0]
    assert lum["kind"] == "unknown"
    assert "dims" not in lum


def test_join_defaults_kind_when_parser_left_it_empty():
    """老 Luminaire 对象（无 kind 或 kind=None）不得让 join 崩，落到 unknown。"""
    ir = _room([])
    lum = Luminaire("L", x=3.0, y=3.0)
    lum.kind = None  # 模拟上游写了 None
    join_luminaires(ir, [lum])
    assert ir["storeys"][0]["spaces"][0]["luminaires"][0]["kind"] == "unknown"


# --------------------------------------------------------------------------
# assign_mount_heights：挂载高度回填
# --------------------------------------------------------------------------

@pytest.mark.parametrize("mount,expected_z", [
    ("recessed", 2.8),                             # 嵌入吊顶 → 天花高
    ("surface", 2.8),                              # 明装吸顶 → 天花高
    ("pendant", 2.8 - DEFAULT_PENDANT_DROP_M),     # 吊装 → 天花减吊杆
    ("wall", 2.2),                                 # 壁装 → 默认壁装高
    ("floor", 0.0),                                # 落地 → 楼面
])
def test_mount_height_by_mount_type(mount, expected_z):
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 0.0,
                 "catalog_match": True, "mount": mount}])
    warnings = assign_mount_heights(ir)
    assert warnings == []
    assert ir["storeys"][0]["spaces"][0]["luminaires"][0]["z"] == pytest.approx(expected_z)


def test_mount_default_is_recessed_matching_validator():
    """不写 mount 时按 recessed 处理，且把 mount 显式写回，避免下游各自默认一次。"""
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 0.0, "catalog_match": True}])
    assign_mount_heights(ir)
    lum = ir["storeys"][0]["spaces"][0]["luminaires"][0]
    assert lum["z"] == pytest.approx(2.8)
    assert lum["mount"] == "recessed"


def test_mount_respects_existing_nonzero_z():
    """图纸已给非零高度时默认不覆盖。"""
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 1.5, "catalog_match": True}])
    assign_mount_heights(ir)
    assert ir["storeys"][0]["spaces"][0]["luminaires"][0]["z"] == pytest.approx(1.5)


def test_mount_overwrite_forces_recompute():
    """--overwrite-z 场景：图纸 z 不可信时强制按 mount 重算。"""
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 1.5, "catalog_match": True}])
    assign_mount_heights(ir, overwrite=True)
    assert ir["storeys"][0]["spaces"][0]["luminaires"][0]["z"] == pytest.approx(2.8)


def test_mount_pendant_drop_configurable():
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 0.0,
                 "catalog_match": True, "mount": "pendant"}])
    assign_mount_heights(ir, pendant_drop=1.2)
    assert ir["storeys"][0]["spaces"][0]["luminaires"][0]["z"] == pytest.approx(1.6)


def test_mount_pendant_drop_cannot_go_below_floor():
    """吊杆比层高还长时不得算出负高度。"""
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 0.0,
                 "catalog_match": True, "mount": "pendant"}], ceil_h=2.0)
    assign_mount_heights(ir, pendant_drop=5.0)
    assert ir["storeys"][0]["spaces"][0]["luminaires"][0]["z"] == pytest.approx(0.0)


def test_mount_wall_height_clamped_to_ceiling():
    """壁装高度不得超过天花。"""
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 0.0,
                 "catalog_match": True, "mount": "wall"}], ceil_h=2.0)
    assign_mount_heights(ir, wall_mount_h=2.6)
    assert ir["storeys"][0]["spaces"][0]["luminaires"][0]["z"] == pytest.approx(2.0)


def test_mount_missing_ceil_h_warns_and_skips():
    """没有净高就无从推挂载高度：整个 space 跳过并告警，z 保持原值。"""
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 0.0, "catalog_match": True}])
    del ir["storeys"][0]["spaces"][0]["ceil_h"]
    warnings = assign_mount_heights(ir)
    assert len(warnings) == 1 and "ceil_h" in warnings[0]
    assert ir["storeys"][0]["spaces"][0]["luminaires"][0]["z"] == pytest.approx(0.0)


@pytest.mark.parametrize("bad_ceil", [0, -1.0, "abc", None])
def test_mount_invalid_ceil_h_warns(bad_ceil):
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 0.0, "catalog_match": True}],
               ceil_h=bad_ceil)
    warnings = assign_mount_heights(ir)
    assert len(warnings) == 1
    assert ir["storeys"][0]["spaces"][0]["luminaires"][0]["z"] == pytest.approx(0.0)


def test_mount_other_warns_and_leaves_z():
    """mount=other 无对应规则 → 告警交人工，不瞎填。"""
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 0.0,
                 "catalog_match": True, "mount": "other"}])
    warnings = assign_mount_heights(ir)
    assert len(warnings) == 1 and "other" in warnings[0]
    assert ir["storeys"][0]["spaces"][0]["luminaires"][0]["z"] == pytest.approx(0.0)


def test_mount_empty_space_is_noop():
    ir = _room([])
    assert assign_mount_heights(ir) == []


def test_count_unset_z():
    ir = _room([
        {"symbol": "A", "x": 1, "y": 1, "z": 0.0, "catalog_match": True},
        {"symbol": "B", "x": 2, "y": 2, "z": 2.8, "catalog_match": True},
        {"symbol": "C", "x": 3, "y": 3, "z": 0.0, "catalog_match": True},
    ])
    assert count_unset_z(ir) == 2
    assign_mount_heights(ir)
    assert count_unset_z(ir) == 0


# --------------------------------------------------------------------------
# validator 规则 7 / 8
# --------------------------------------------------------------------------

def _codes(ir):
    return [v["code"] for v in validate_ir(ir)]


def test_rule7_flags_luminaire_lying_on_floor():
    """回归 2026-09-05 的洞：28 盏灯 z=0 曾静默通过所有校验。"""
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 0.0,
                 "catalog_match": True, "mount": "recessed", "kind": "point",
                 "dims": {"radius_mm": 76.0}}])
    assert "LUM_MOUNT_Z_UNSET" in _codes(ir)


def test_rule7_clears_after_mount_backfill():
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 0.0,
                 "catalog_match": True, "mount": "recessed", "kind": "point",
                 "dims": {"radius_mm": 76.0}}])
    assign_mount_heights(ir)
    assert "LUM_MOUNT_Z_UNSET" not in _codes(ir)


def test_rule7_ignores_floor_mount():
    """落地灯 z=0 是正常的，不该报。"""
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 0.0,
                 "catalog_match": True, "mount": "floor"}])
    assert "LUM_MOUNT_Z_UNSET" not in _codes(ir)


def test_rule8_flags_point_without_radius():
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 2.8,
                 "catalog_match": True, "kind": "point", "dims": {"w_mm": 100.0}}])
    assert "LUM_KIND_DIMS_MISMATCH" in _codes(ir)


def test_rule8_flags_linear_without_wh():
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 2.8,
                 "catalog_match": True, "kind": "linear", "dims": {"radius_mm": 76.0}}])
    assert "LUM_KIND_DIMS_MISMATCH" in _codes(ir)


def test_rule8_silent_when_kind_absent():
    """kind 是可选字段，老 IR 没有它时不该被报。"""
    ir = _room([{"symbol": "L", "x": 3, "y": 3, "z": 2.8, "catalog_match": True}])
    assert "LUM_KIND_DIMS_MISMATCH" not in _codes(ir)


def test_rule8_passes_consistent_pairs():
    ir = _room([
        {"symbol": "P", "x": 2, "y": 2, "z": 2.8, "catalog_match": True,
         "kind": "point", "dims": {"radius_mm": 76.0}},
        {"symbol": "L", "x": 4, "y": 4, "z": 2.8, "catalog_match": True,
         "kind": "linear", "dims": {"w_mm": 1555.0, "h_mm": 300.0}},
        {"symbol": "U", "x": 5, "y": 5, "z": 2.8, "catalog_match": True,
         "kind": "unknown"},
    ])
    assert "LUM_KIND_DIMS_MISMATCH" not in _codes(ir)


# --------------------------------------------------------------------------
# 单位正确性回归：radius_mm 曾把 DXF 原始单位（本图为 cm）当 mm 写出去
# --------------------------------------------------------------------------

def test_circle_radius_mm_is_real_millimetres(tmp_path):
    """CIRCLE 灯具的 radius_mm 必须经单位换算。

    修前 parser 直接把 ``entity.dxf.radius`` 塞进 ``radius_mm``；本图 $INSUNITS 是 cm，
    于是 7.6 cm 被写成 "7.6 mm"（直径 15.2 mm，筒灯不可能这么小），差 10 倍。
    这条用 cm 图纸钉住换算：半径 7.6 cm → 76 mm。
    """
    ezdxf = pytest.importorskip("ezdxf")
    from src.parser.dxf import ParseConfig, extract_luminaires

    doc = ezdxf.new(setup=True)
    doc.header["$INSUNITS"] = 5  # 5 = 厘米
    doc.modelspace().add_circle(center=(100.0, 100.0), radius=7.6)

    cfg = ParseConfig()
    cfg.units_from_header = True
    cfg.luminaire_circle_radius_range = (5.0, 10.0)  # 阈值按 DXF 原始单位
    cfg.luminaire_block_names = []

    lumis = extract_luminaires(doc, cfg)
    assert len(lumis) == 1, lumis
    lum = lumis[0]
    assert lum.kind == "point"
    assert lum.attrs["radius_mm"] == pytest.approx(76.0), "radius_mm 未换算成真毫米"
    assert lum.attrs["radius_raw"] == pytest.approx(7.6), "应保留 DXF 原始单位值供复核"
    assert lum.attrs["raw_units"] == "cm"
