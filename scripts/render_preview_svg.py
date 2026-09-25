"""IR JSON → 简易 SVG 预览（房间多边形 + 灯具圆圈叠加）。

用于辅助 AC-7 肉眼对齐。不引入 GUI。
用法：python scripts/render_preview_svg.py <ir.json> --out build/preview.svg
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

ROOM_COLORS = ["#4e79a7", "#f28e2b", "#e15759", "#76b7b2", "#59a14f",
               "#edc948", "#b07aa1", "#ff9da7", "#9c755f", "#bab0ac"]


def _to_svg_polygon(poly_m, scale: float, ox: float, oy: float) -> str:
    pts = []
    for p in poly_m:
        x, y = p[0], p[1]
        sx = (x + ox) * scale
        sy = (y + oy) * scale  # SVG y 向下；等会儿我们用负 oy 翻转
        pts.append(f"{sx:.2f},{sy:.2f}")
    return " ".join(pts)


def render(ir: Dict[str, Any], margin_m: float = 0.5) -> str:
    # 取全局 bbox（米制）
    xs: List[float] = []
    ys: List[float] = []
    for storey in ir.get("storeys", []):
        for space in storey.get("spaces", []):
            for p in space.get("polygon", []):
                xs.append(p[0])
                ys.append(p[1])
            for lum in space.get("luminaires", []):
                xs.append(lum.get("x", 0))
                ys.append(lum.get("y", 0))
    if not xs or not ys:
        return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"></svg>'
    xmin = min(xs) - margin_m
    xmax = max(xs) + margin_m
    ymin = min(ys) - margin_m
    ymax = max(ys) + margin_m
    W_m = xmax - xmin
    H_m = ymax - ymin
    if W_m <= 0:
        W_m = 1.0
    if H_m <= 0:
        H_m = 1.0
    # 像素尺度：SVG 宽度 1200px（保持宽高比）
    svg_w = 1200
    scale = svg_w / W_m
    svg_h = max(int(H_m * scale), 1)

    def sx(x: float) -> float: return (x - xmin) * scale
    # y 翻转：SVG y 轴向下，真实世界 y 越大越向上
    def sy(y: float) -> float: return svg_h - (y - ymin) * scale

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_w} {svg_h}" '
        f'width="{svg_w}" height="{svg_h}">',
        '<style>.room {fill: rgba(78,121,167,0.12); stroke-width: 2.5;} '
        '.furniture {fill: rgba(242,142,43,0.25); stroke: #d97a1e; stroke-width: 1.5; stroke-dasharray: none;} '
        '.lum {fill: #e15759; stroke: #777; stroke-width: 1;} '
        '.label {font-family: sans-serif; font-size: 11px; fill: #333;} '
        '.flabel {font-family: sans-serif; font-size: 9px; fill: #c2680a; font-weight: bold;}</style>',
        f'<rect x="0" y="0" width="{svg_w}" height="{svg_h}" fill="#fafafa"/>',
    ]
    # 坐标轴信息：角落标注
    parts.append(f'<text x="10" y="20" class="label">'
                 f'bbox: W={W_m:.1f}m × H={H_m:.1f}m  (X∈[{xmin:.2f},{xmax:.2f}], Y∈[{ymin:.2f},{ymax:.2f}])</text>')

    # 先画房间（大面积，蓝色），再画家具（小面积，橙色），再画灯具
    # 判断 space 是房间还是家具：名称以"家具_"开头 或 在 furniture 列表中
    color_i = 0
    for storey in ir.get("storeys", []):
        for space in storey.get("spaces", []):
            poly = space.get("polygon", [])
            if len(poly) < 3:
                continue
            name = space.get("name") or space.get("id", "")
            is_furniture = name.startswith("家具_")

            if is_furniture:
                # 家具：橙色填充
                path = " ".join(f"{sx(p[0]):.2f},{sy(p[1]):.2f}" for p in poly)
                parts.append(
                    f'<polygon class="furniture" points="{path}" />'
                )
                # 标注家具编号
                xs_p = [p[0] for p in poly]
                ys_p = [p[1] for p in poly]
                cx = sx((min(xs_p) + max(xs_p)) / 2)
                cy = sy((min(ys_p) + max(ys_p)) / 2)
                # 从名称中提取家具编号
                furn_label = name.replace("家具_LINEARC_", "#").replace("家具_", "#")[:18]
                parts.append(f'<text x="{cx:.1f}" y="{cy:.1f}" class="flabel" '
                             f'text-anchor="middle">{furn_label}</text>')
            else:
                # 房间：蓝色半透明
                color = ROOM_COLORS[color_i % len(ROOM_COLORS)]
                color_i += 1
                path = " ".join(f"{sx(p[0]):.2f},{sy(p[1]):.2f}" for p in poly)
                parts.append(
                    f'<polygon class="room" stroke="{color}" points="{path}" />'
                )
                # 标注（房间 bbox 中心 + 名称前 20 字）
                xs_p = [p[0] for p in poly]
                ys_p = [p[1] for p in poly]
                cx = sx((min(xs_p) + max(xs_p)) / 2)
                cy = sy((min(ys_p) + max(ys_p)) / 2)
                label = name[:22]
                parts.append(f'<text x="{cx:.1f}" y="{cy:.1f}" class="label" '
                             f'text-anchor="middle">{label}</text>')

            # 灯具（只在非家具 space 上画，避免重复）
            if not is_furniture:
                for li, lum in enumerate(space.get("luminaires", [])):
                    cx1 = sx(lum.get("x", 0))
                    cy1 = sy(lum.get("y", 0))
                    attrs = lum.get("attrs") or {}
                    sym = lum.get("symbol", "")
                    if sym.startswith("RECT-"):
                        w_mm = float(attrs.get("rect_w_mm") or 150.0)
                        h_mm = float(attrs.get("rect_h_mm") or 30.0)
                        w_m = w_mm / 1000.0
                        h_m = h_mm / 1000.0
                        w_px = max(8.0, w_m * scale)
                        h_px = max(4.0, h_m * scale)
                        parts.append(
                            f'<rect x="{cx1 - w_px/2:.2f}" y="{cy1 - h_px/2:.2f}" '
                            f'width="{w_px:.2f}" height="{h_px:.2f}" '
                            f'fill="#2f7bd9" stroke="#1c4e9c" stroke-width="1.2" rx="1.5" ry="1.5" />'
                        )
                    else:
                        r = max(3.0, min(8.0, scale * 0.01))
                        parts.append(
                            f'<circle class="lum" cx="{cx1:.2f}" cy="{cy1:.2f}" r="{r:.1f}" />'
                        )
    parts.append('</svg>')
    return "\n".join(parts)


def main() -> None:
    p = argparse.ArgumentParser(description="IR JSON → SVG 预览")
    p.add_argument("ir_json")
    p.add_argument("--out", default="build/room_layout.svg")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    ir = json.loads(Path(args.ir_json).read_text(encoding="utf-8"))
    svg = render(ir)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(svg, encoding="utf-8")
    logger.info("SVG 预览已写：%s", out.resolve())


if __name__ == "__main__":
    main()
