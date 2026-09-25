"""DXF 扫描审计工具：输出图层/实体/块/CIRCLE/$INSUNITS/bbox 统计。

用法：python scripts/scan_dxf.py <dxf> [--format json|markdown] [--out <path>]
"""
from __future__ import annotations

import argparse
import json
import logging
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict

import ezdxf

logger = logging.getLogger(__name__)


def _insunits_to_units(code: Any) -> Any:
    mapping = {1: "inch", 4: "mm", 5: "cm", 6: "m"}
    if code is None:
        return None
    return mapping.get(int(code)) if str(code).isdigit() else None


def scan_dxf(path: Path) -> Dict[str, Any]:
    doc = ezdxf.readfile(str(path))

    layers: Dict[str, Dict[str, int]] = defaultdict(lambda: Counter())
    inserts: Counter = Counter()
    circle_radii: Counter = Counter()  # 半径按 0.1 分桶
    xs: list[float] = []
    ys: list[float] = []

    msp = doc.modelspace()
    total_entities = 0
    for e in msp:
        total_entities += 1
        layer = e.dxf.layer or "0"
        dtype = e.dxftype()
        layers[layer][dtype] += 1

        if dtype == "INSERT":
            inserts[e.dxf.name or ""] += 1
            try:
                x, y, *_ = e.dxf.insert
                xs.append(x)
                ys.append(y)
            except Exception:
                pass

        elif dtype == "CIRCLE":
            try:
                center = e.dxf.center
                xs.append(center.x)
                ys.append(center.y)
                r = float(e.dxf.radius)
                bucket = round(r, 1)
                circle_radii[bucket] += 1
            except Exception as ex:
                logger.warning("CIRCLE 解析失败: %s", ex)

        elif dtype == "LWPOLYLINE":
            try:
                for p in e.get_points("xy"):
                    xs.append(p[0])
                    ys.append(p[1])
            except Exception:
                pass

        elif dtype == "POLYLINE":
            try:
                for v in e.vertices:
                    p = v.dxf.location
                    xs.append(p.x)
                    ys.append(p.y)
            except Exception:
                pass

        elif dtype == "LINE":
            try:
                s = e.dxf.start
                en = e.dxf.end
                xs.extend([s.x, en.x])
                ys.extend([s.y, en.y])
            except Exception:
                pass

        elif dtype == "ARC":
            try:
                cen = e.dxf.center
                r = e.dxf.radius
                start = math.radians(e.dxf.start_angle)
                end = math.radians(e.dxf.end_angle)
                xs.append(cen.x + r * math.cos(start))
                xs.append(cen.x + r * math.cos(end))
                ys.append(cen.y + r * math.sin(start))
                ys.append(cen.y + r * math.sin(end))
            except Exception:
                pass

    header_units = None
    try:
        header_units = doc.header.get("$INSUNITS")
    except Exception:
        pass

    bbox = None
    if xs and ys:
        bbox = {
            "x_min": min(xs), "x_max": max(xs),
            "y_min": min(ys), "y_max": max(ys),
            "x_delta": max(xs) - min(xs),
            "y_delta": max(ys) - min(ys),
        }

    return {
        "file": str(path),
        "total_entities_in_modelspace": total_entities,
        "header_insunits_raw": header_units,
        "header_insunits_human": _insunits_to_units(header_units),
        "bbox_from_model_vertices": bbox,
        "layer_entity_counts": {k: dict(v) for k, v in layers.items()},
        "insert_block_counts": dict(inserts.most_common()),
        "circle_radius_buckets": {
            f"{r:0.1f}": n for r, n in sorted(circle_radii.items(), key=lambda x: -x[1])
        },
    }


def _render_markdown(scan: Dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"# DXF 审计：{scan['file']}")
    lines.append("")
    lines.append(f"- 实体总数 (modelspace)：**{scan['total_entities_in_modelspace']}**")
    lines.append(f"- $INSUNITS：`{scan['header_insunits_raw']}` → `{scan['header_insunits_human']}`")
    bbox = scan.get("bbox_from_model_vertices")
    if bbox:
        lines.append(f"- 实扫 bbox：X∈[{bbox['x_min']:.1f}, {bbox['x_max']:.1f}]  Δ={bbox['x_delta']:.1f}；"
                     f"Y∈[{bbox['y_min']:.1f}, {bbox['y_max']:.1f}]  Δ={bbox['y_delta']:.1f}")
    lines.append("")
    lines.append("## 图层 × 实体类型")
    lines.append("")
    lines.append("| 图层 | 明细 |")
    lines.append("|---|---|")
    for layer, counts in scan["layer_entity_counts"].items():
        detail = ", ".join(f"{k}×{v}" for k, v in sorted(counts.items()))
        lines.append(f"| {layer} | {detail} |")
    lines.append("")
    lines.append("## INSERT 块 Top")
    lines.append("")
    lines.append("| 块名 | 数量 |")
    lines.append("|---|---|")
    for k, v in scan["insert_block_counts"] or []:
        lines.append(f"| {k} | {v} |")
    lines.append("")
    lines.append("## CIRCLE 半径分桶")
    lines.append("")
    lines.append("| 半径 (绘图单位) | 数量 |")
    lines.append("|---|---|")
    for r, n in scan["circle_radius_buckets"].items():
        lines.append(f"| {r} | {n} |")
    return "\n".join(lines) + "\n"


def main() -> None:
    p = argparse.ArgumentParser(description="DXF 结构审计工具")
    p.add_argument("dxf")
    p.add_argument("--format", choices=["json", "markdown"], default="markdown")
    p.add_argument("--out", help="输出文件路径；不传则打印到 stdout")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    path = Path(args.dxf)
    if not path.exists():
        raise SystemExit(f"DXF 不存在：{path}")

    scan = scan_dxf(path)
    if args.format == "json":
        text = json.dumps(scan, ensure_ascii=False, indent=2)
    else:
        text = _render_markdown(scan)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        logger.info("写入审计结果：%s", out_path)
    else:
        print(text)


if __name__ == "__main__":
    main()
