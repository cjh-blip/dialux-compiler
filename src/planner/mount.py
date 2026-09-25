"""挂载高度回填：给灯具补 z 坐标。

**为什么需要这一步**：2D DWG 只有平面坐标，没有任何高度信息，解析器一律把灯具的 ``z`` 写成 0
（即趴在楼面上）。2026-09-05 的 evo 真机验证暴露了这个洞：导出的 28 盏灯 ``z`` 全是 0，
而房间净高 2.8 m —— 若真布进 DIALux，照度计算会完全错。高度必须由规则引擎按房间几何补齐，
这是解析器无法承担的职责。

**单位与基准**：全部为米，与 ``space.elevation`` 同基准（楼面 = 0），Z 轴向上。
不接受毫米，不做隐式换算 —— 见 AGENTS.md「单位/坐标必须显式」。

**mount 与 z 的关系**（与 ``src/validator`` 规则 4 的判据保持一致）：

===========  =====================================  ==================================
mount        含义                                   回填后的 z
===========  =====================================  ==================================
``recessed`` 嵌入式（筒灯埋在吊顶里）               ``ceil_h``
``surface``  明装/吸顶                              ``ceil_h``
``pendant``  吊装                                   ``ceil_h - pendant_drop``（默认降 0.5）
``wall``     壁装                                   壁装高度常量（默认 2.2）
``floor``    落地                                   0（本就在楼面）
``other``    其它                                   不动，交人工
===========  =====================================  ==================================
"""
from __future__ import annotations

from typing import Any, Dict, List

# 吊装灯具默认吊杆长度（米）。真实项目应由灯具规格给出，这里只做兜底默认值。
DEFAULT_PENDANT_DROP_M = 0.5
# 壁装灯具默认安装高度（米，距楼面）。
DEFAULT_WALL_MOUNT_H_M = 2.2
# 解析器未回填时 z 的哨兵值：0 表示「趴在楼面」，视为待回填。
UNSET_Z = 0.0
# 浮点比较容差（米）。
EPS = 1e-6

# mount 缺省值必须与 validator 规则 4 的 ``lum.get("mount", "recessed")`` 一致，
# 否则同一盏灯在回填与校验两侧会按不同类型处理。
DEFAULT_MOUNT = "recessed"


def _target_z(mount: str, ceil_h: float, pendant_drop: float, wall_h: float):
    """按 mount 算目标 z；返回 None 表示这类灯具不由本规则决定高度。"""
    if mount in ("recessed", "surface"):
        return ceil_h
    if mount == "pendant":
        # 吊杆不允许把灯具压到楼面以下
        return max(ceil_h - pendant_drop, 0.0)
    if mount == "wall":
        # 壁装高度不得超过天花
        return min(wall_h, ceil_h)
    if mount == "floor":
        return 0.0
    return None


def assign_mount_heights(
    ir: Dict[str, Any],
    *,
    pendant_drop: float = DEFAULT_PENDANT_DROP_M,
    wall_mount_h: float = DEFAULT_WALL_MOUNT_H_M,
    overwrite: bool = False,
) -> List[str]:
    """就地给 ``ir`` 里所有灯具回填 ``z``，返回 warnings 列表。

    参数
    ----
    pendant_drop
        吊装灯具的吊杆长度（米）。
    wall_mount_h
        壁装灯具的安装高度（米，距楼面）。
    overwrite
        False（默认）只回填 ``z`` 仍是 0 的灯具，尊重解析器/人工已给的非零高度；
        True 则无条件按 mount 重算，用于「图纸 z 不可信、强制按规则重排」的场合。

    行为约定
    --------
    - ``space.ceil_h`` 缺失或非正 → 该 space 整体跳过并告警（没有天花高度就无从推挂载高度）。
    - ``mount="other"`` → 跳过并告警，交人工。
    - ``mount="floor"`` → 目标就是 0，与哨兵值同值，不算回填。
    """
    warnings: List[str] = []

    for storey in ir.get("storeys", []):
        for space in storey.get("spaces", []):
            lums = space.get("luminaires") or []
            if not lums:
                continue

            sid = space.get("name") or space.get("id") or "?"
            raw_ceil = space.get("ceil_h")
            try:
                ceil_h = float(raw_ceil) if raw_ceil is not None else None
            except (TypeError, ValueError):
                ceil_h = None

            if ceil_h is None or ceil_h <= 0:
                warnings.append(
                    f"空间 {sid}：ceil_h={raw_ceil!r} 不可用，{len(lums)} 盏灯具的挂载高度未回填"
                    f"（z 仍为解析值），请先给该空间设净高"
                )
                continue

            for i, lum in enumerate(lums):
                mount = lum.get("mount") or DEFAULT_MOUNT
                lid = lum.get("symbol") or f"#{i}"

                try:
                    cur_z = float(lum.get("z", UNSET_Z))
                except (TypeError, ValueError):
                    cur_z = UNSET_Z

                if not overwrite and abs(cur_z - UNSET_Z) > EPS:
                    continue  # 已有非零高度，尊重它

                target = _target_z(mount, ceil_h, pendant_drop, wall_mount_h)
                if target is None:
                    warnings.append(
                        f"空间 {sid} 灯具 {lid}：mount={mount!r} 无对应挂载高度规则，z 未回填"
                    )
                    continue

                lum["z"] = target
                # 把 mount 显式写回，避免下游再各自默认一次（默认值漂移是隐患）
                lum.setdefault("mount", mount)

    return warnings


def count_unset_z(ir: Dict[str, Any]) -> int:
    """统计 z 仍为 0 的灯具数量，供 CLI 与测试断言回填效果。"""
    n = 0
    for storey in ir.get("storeys", []):
        for space in storey.get("spaces", []):
            for lum in space.get("luminaires") or []:
                try:
                    if abs(float(lum.get("z", UNSET_Z)) - UNSET_Z) <= EPS:
                        n += 1
                except (TypeError, ValueError):
                    n += 1
    return n
