"""CLI 入口：DWG + 灯具表 → IR → ActionPlan → (dry-run) 执行。"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

if __name__ == "__main__" and __package__ in (None, ""):
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.parser.dxf import ParseConfig, parse_dxf, extract_luminaires  # noqa: E402
from src.parser.xlsx import parse_xlsx  # noqa: E402
from src.planner.core import (  # noqa: E402
    build_action_plan,
)
from src.planner.join import join_luminaires  # noqa: E402
from src.planner.mount import (  # noqa: E402
    DEFAULT_PENDANT_DROP_M,
    DEFAULT_WALL_MOUNT_H_M,
    assign_mount_heights,
    count_unset_z,
)
from src.validator import validate_ir  # noqa: E402
from src.executor.actions import dump_plan  # noqa: E402


def _maybe_convert_dwg_to_dxf(path: str) -> str:
    """若扩展名是 dwg，调用 scripts/dwg_to_dxf.convert_one；否则原样返回。"""
    p = Path(path)
    if p.suffix.lower() != ".dwg":
        return str(p)
    # 延迟 import：避免 ODA 未装时连 CLI help 都用不了
    from scripts.dwg_to_dxf import convert_one
    out_dir = Path("build/_cache/dwg_converted").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    return str(convert_one(p, out_dir=out_dir))


def main():
    parser = argparse.ArgumentParser(description="DIALux 建模编译器（MVP1）")
    parser.add_argument("--dwg", required=True, help="房间布局 DWG 或 DXF 文件路径")
    parser.add_argument("--dwg-lighting",
                        help="（可选）独立灯具布置图 DWG/DXF；缺省从 --dwg 同一张图抽灯具")
    parser.add_argument("--luminaire", help="灯具表 Excel (.xlsx)（MVP1 仅读取、不自动匹配型号）")
    parser.add_argument("--config", help="ParseConfig JSON（见 tests/fixtures/sample_parse_config.json）")
    parser.add_argument("--out", default="build/project.json",
                        help="输出文件路径；--format plan 时扩展为 .jsonl")
    parser.add_argument("--format", choices=["ir", "plan", "report"], default="ir",
                        help="ir=IR JSON, plan=ActionPlan JSONL, report=validator 违规 JSON")
    parser.add_argument("--report", help="额外写 validator 报告 JSON 到该路径")
    parser.add_argument("--preview", action="store_true", help="同时输出 SVG 预览（build/room_layout.svg）")
    parser.add_argument("--execute", action="store_true",
                        help="真实执行（MVP1 默认 ProgramExecutor dry-run=False；不开启键鼠）")
    parser.add_argument("--pendant-drop", type=float, default=DEFAULT_PENDANT_DROP_M,
                        metavar="M",
                        help=f"吊装灯具吊杆长度（米），默认 {DEFAULT_PENDANT_DROP_M}")
    parser.add_argument("--wall-mount-h", type=float, default=DEFAULT_WALL_MOUNT_H_M,
                        metavar="M",
                        help=f"壁装灯具安装高度（米，距楼面），默认 {DEFAULT_WALL_MOUNT_H_M}")
    parser.add_argument("--overwrite-z", action="store_true",
                        help="无条件按 mount 重算所有灯具 z（默认只回填 z=0 的，尊重图纸已有高度）")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    cfg = ParseConfig()
    if args.config:
        cfg = ParseConfig.from_json(args.config)
        logging.info("加载 ParseConfig from %s", args.config)

    dwg_path = args.dwg
    if dwg_path.lower().endswith(".dwg"):
        try:
            dwg_path = _maybe_convert_dwg_to_dxf(dwg_path)
            logging.info("DWG → DXF：%s", dwg_path)
        except Exception as e:
            logging.error("DWG→DXF 失败：%s", e)
            raise SystemExit(2)

    ir = parse_dxf(dwg_path, cfg)

    # 灯具抽取：优先 --dwg-lighting 独立灯具图；否则同一张图抽
    import ezdxf as _ezdxf  # noqa: F401  # 懒用
    if args.dwg_lighting:
        # 独立灯具图：可能是 .dwg，需转换
        lum_dwg_path = args.dwg_lighting
        if Path(lum_dwg_path).suffix.lower() == ".dwg":
            try:
                lum_dwg_path = _maybe_convert_dwg_to_dxf(lum_dwg_path)
                logging.info("灯具 DWG → DXF：%s", lum_dwg_path)
            except Exception as e:
                logging.error("灯具 DWG→DXF 失败：%s", e)
                raise SystemExit(2)
    else:
        # 同一张图：复用已转换的 dwg_path（若是 .dwg 已在上面转成 .dxf）
        lum_dwg_path = dwg_path
    lum_doc = _ezdxf.readfile(lum_dwg_path)
    lumis = extract_luminaires(lum_doc, cfg)
    warnings = join_luminaires(ir, lumis)
    for w in warnings:
        logging.warning(w)

    # 挂载高度回填：2D DWG 没有高度，解析出的灯具 z 全是 0（趴在楼面）。
    # 必须在 validate_ir 之前跑，否则规则 7 会把这批本可自动修的 z=0 全报成 ERROR。
    mount_warnings = assign_mount_heights(
        ir,
        pendant_drop=args.pendant_drop,
        wall_mount_h=args.wall_mount_h,
        overwrite=args.overwrite_z,
    )
    for w in mount_warnings:
        logging.warning(w)
    unset = count_unset_z(ir)
    if unset:
        logging.warning("挂载高度回填后仍有 %d 盏灯具 z=0，见上方告警", unset)
    else:
        logging.info("挂载高度回填完成：所有灯具 z 已就位")

    if args.luminaire:
        try:
            specs = parse_xlsx(args.luminaire)
            logging.info("读取灯具表 %d 条（型号精确匹配功能留 MVP3）", len(specs))
        except Exception as e:  # noqa
            logging.error("灯具表读取失败：%s", e)

    violations = validate_ir(ir)
    halts = [v for v in violations if v.get("severity") == "HALT"]
    if violations:
        levels = {}
        for v in violations:
            levels[v["severity"]] = levels.get(v["severity"], 0) + 1
        # 日志级别跟着最高严重度走。以前这里恒用 logging.error，于是「HALT=0、只有
        # 几条 WARNING」的一次正常运行也会刷一条红色 ERROR，看着像失败了
        # ——2026-09-06 架构师就是这么被误导的。级别必须反映真实结论。
        if halts or levels.get("ERROR"):
            log = logging.error
        elif levels.get("WARNING"):
            log = logging.warning
        else:
            log = logging.info
        log("IR validator 结果：%s；HALT=%d 条%s",
            ", ".join(f"{k}×{v}" for k, v in sorted(levels.items())),
            len(halts),
            "" if halts else "（无阻塞项，流程继续）")
    else:
        logging.info("IR validator：全部通过 ✓")

    plan = build_action_plan(ir, halt_violations=halts)

    # ---------- 输出 ----------
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    fmt = args.format
    if fmt == "ir":
        out.write_text(json.dumps(ir, ensure_ascii=False, indent=2), encoding="utf-8")
        logging.info("IR JSON → %s (%d rooms, %d furniture, %d 灯具（入房间%d）)",
                     out, ir["_meta"]["rooms"], ir["_meta"].get("furniture", 0),
                     ir["_meta"]["luminaires"],
                     sum(len(s["luminaires"]) for st in ir["storeys"] for s in st["spaces"]))
    elif fmt == "plan":
        dump_plan(plan, str(out))
        logging.info("ActionPlan → %s (%d 条)", out, len(plan))
    else:  # report
        out.write_text(json.dumps(violations, ensure_ascii=False, indent=2), encoding="utf-8")
        logging.info("Validator 报告 → %s (%d 条)", out, len(violations))

    if args.report:
        Path(args.report).parent.mkdir(parents=True, exist_ok=True)
        Path(args.report).write_text(
            json.dumps(violations, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.preview:
        try:
            from scripts.render_preview_svg import render
            svg = render(ir)
            svg_out = Path("build/room_layout.svg")
            svg_out.write_text(svg, encoding="utf-8")
            logging.info("SVG 预览 → %s", svg_out)
        except Exception as e:  # noqa
            logging.error("SVG 预览生成失败：%s", e)

    if args.execute:
        # P2：ActionPlan 由执行器内核派发到 UiaDriver（STF 批量通道 + place_luminaire stub）。
        # ProgramExecutor 保留在 key_mouse.py 作为 MVP1 参考档，不再从这里进。
        from src.executor.kernel import execute_plan
        from src.executor.uia.driver_plan import UiaDriver

        driver = UiaDriver(ir, stf_path="build/demo_room.stf")
        events = execute_plan(plan, driver)
        if not all(e.ok for e in events):
            bad = [e for e in events if not e.ok]
            logging.error("执行失败：%s（%s）", bad[0].title, bad[0].detail)
            raise SystemExit(1)
        logging.info("ActionPlan 执行完成：%d 条全部派发（place_luminaire=%d 盏 stub 收集）",
                     len(events), len(driver.luminaires))
    else:
        logging.info("dry-run 模式，ActionPlan 共 %d 条；加 --execute 才执行 UiaDriver", len(plan))


if __name__ == "__main__":
    main()
