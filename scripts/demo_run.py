"""一条命令：DWG 图纸 → DIALux evo 里建好的房间 → （可选）放灯 → 存成 .evo。

这是「保底交付」——周报录屏就录这条命令。它把已经各自验证过的三段串起来：

    1. 解析：DWG → DXF → IR（src.main 那条管道，测试见 tests/）
    2. 导出：IR → STF（房间几何真机验收过，顶点 11/11 回环命中）
    3. 落地：UIA 驱动 DIALux 导入 STF 并保存（src.executor.uia）

用法::

    python scripts/demo_run.py                     # 用默认的两张真实图纸
    python scripts/demo_run.py --skip-parse        # 复用已有 IR，只跑落地
    python scripts/demo_run.py --no-drive          # 只出 STF，不碰 DIALux
    python scripts/demo_run.py --luminaires auto   # 建壳后按 IR 灯具自动导型号+排布
    python scripts/demo_run.py --luminaires path/to/lamp.ies   # 显式给灯具文件

**灯具**：STF 的 NrLums/Lum{i} 段在 evo 14.0 被忽略（2026-09-05/06 双重真机判定），
所以灯具走 `--luminaires` 的 computer use 通道（导入 IES + ArrangementFromSpace 自动排布，
2026-09-07 真机闭环）。
"""
from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# PyInstaller 冻结时：exe 在 dist/demo_run/ 下，图纸应放 exe 同目录；未冻结时
# 用仓库根。冻结检测：sys.frozen 存在。
_FROZEN = getattr(sys, "frozen", False)
BASE = Path(getattr(sys, "_MEIPASS", REPO)) if _FROZEN else REPO

from src.executor.uia import run_import, succeeded  # noqa: E402

DEFAULT_DWG = "布局图.dwg"
DEFAULT_DWG_LIGHTING = "灯具图.dwg"
DEFAULT_CONFIG = "tests/fixtures/sample_parse_config.json"
DEFAULT_IR = "build/demo_ir.json"
DEFAULT_STF = "build/demo_room.stf"


def _default_path(name: str) -> str:
    """打包版：图纸/config 从 exe 同目录找（用户把 布局图.dwg 等放 exe 旁）；否则仓库根。"""
    if _FROZEN:
        # dist/demo_run/ 目录（EXE 同级）
        exe_dir = Path(sys.executable).resolve().parent
        cand = exe_dir / name
        if cand.exists():
            return str(cand)
        return name  # 找不到就保持原名（后面报错说明）
    return name


def _work_path(name: str) -> str:
    """打包版：IR/STF 写到 exe 旁 _work/ 目录（自建），避免依赖仓库 build/。"""
    if _FROZEN:
        exe_dir = Path(sys.executable).resolve().parent
        work = exe_dir / "_work"
        work.mkdir(exist_ok=True)
        return str(work / name)
    return name


def _run(cmd: list, label: str) -> None:
    """跑一个子命令，失败就抛。输出直通终端，录屏时能看见。

    打包版：子命令在 exe 同目录跑（图纸/config 相对位置一致）；源码版用仓库根。
    """
    logging.info("──── %s ────", label)
    cwd = Path(sys.executable).resolve().parent if _FROZEN else REPO
    r = subprocess.run(cmd, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(f"{label} 失败（退出码 {r.returncode}）")


def _parse_to_ir(dwg: str, dwg_lighting: str, config: str, out: str) -> None:
    """DWG → IR。打包版进程内调用（无独立 python）；源码版 subprocess。"""
    if _FROZEN:
        import src.main as _main
        argv = ["src/main.py", "--dwg", dwg,
                "--dwg-lighting", dwg_lighting,
                "--config", config, "--out", out]
        old = sys.argv
        sys.argv = argv
        try:
            _main.main()
        except SystemExit as exc:
            if exc.code not in (None, 0):
                raise RuntimeError(f"解析失败（退出码 {exc.code}）") from exc
        finally:
            sys.argv = old
        return
    _run([sys.executable, "src/main.py",
          "--dwg", dwg, "--dwg-lighting", dwg_lighting,
          "--config", config, "--out", out], "1/3 解析图纸 → IR")


def _stf_export(ir: str, stf: str) -> None:
    """IR → STF。打包版进程内调用；源码版 subprocess。"""
    if _FROZEN:
        from src.exporter import stf as _stf
        rc = _stf.main(["--validate", ir, stf])
        if rc != 0:
            raise RuntimeError(f"STF 导出失败（退出码 {rc}）")
        return
    _run([sys.executable, "-m", "src.exporter.stf", "--validate", ir, stf],
         "2/3 IR → STF")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dwg", default=_default_path(DEFAULT_DWG))
    p.add_argument("--dwg-lighting", default=_default_path(DEFAULT_DWG_LIGHTING))
    p.add_argument("--config", default=_default_path(DEFAULT_CONFIG))
    p.add_argument("--ir", default=_work_path(DEFAULT_IR))
    p.add_argument("--stf", default=_work_path(DEFAULT_STF))
    p.add_argument("--skip-parse", action="store_true", help="复用已有 IR，跳过解析")
    p.add_argument("--no-drive", action="store_true", help="只出 STF，不驱动 DIALux")
    p.add_argument("--luminaires", nargs="*", metavar="KIND=IES",
                   help="建壳后自动放灯。格式 KIND=IES 可多个（point=筒灯文件 "
                        "linear=线性灯文件），按 IR 灯具 kind 分组排布；"
                        "传 auto 用内置默认两件套；传裸路径 = 所有灯用一个文件")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.skip_parse:
        _parse_to_ir(args.dwg, args.dwg_lighting, args.config, args.ir)
    else:
        logging.info("──── 1/3 解析（跳过，复用 %s）────", args.ir)

    _stf_export(args.ir, args.stf)

    if args.no_drive:
        logging.info("──── 3/3 落地（--no-drive，止步于 %s）────", args.stf)
        return 0

    logging.info("──── 3/3 UIA 驱动 DIALux ────")
    events = run_import(args.stf)
    if not succeeded(events):
        bad = [e for e in events if not e.ok]
        logging.error("落地失败：%s", bad[-1].title if bad else "驱动无输出")
        return 1

    # 放灯：--luminaires 支持 KIND=IES 映射 / auto（内置默认两件套）/ 裸路径
    if args.luminaires:
        import json as _json
        from src.executor.uia.luminaire import _last_ok, place_luminaires

        # 1) 解析映射
        DEFAULT_LUMS = {
            "point": "build/ies/fixed/NPTLED351_NVC.IES",
            "linear": "build/ies/linear/opple_LEDPanelRc-S-Re295-30W-4000-WH-U19.ies",
        }
        mapping: dict = {}
        if args.luminaires == ["auto"]:
            mapping = dict(DEFAULT_LUMS)
        else:
            for item in args.luminaires:
                if "=" in item:
                    kind, path = item.split("=", 1)
                    mapping[kind.strip()] = path.strip()
                else:
                    # 裸路径：所有 kind 用同一个文件
                    mapping = {"point": item, "linear": item}

        # 2) 读 IR 统计各 kind 盏数（决定哪类该放；0 盏的 kind 跳过）
        ir = _json.loads(Path(args.ir).read_text(encoding="utf-8"))
        kind_counts: dict = {}
        for st in ir.get("storeys", []):
            for sp in st.get("spaces", []):
                for lu in sp.get("luminaires", []):
                    k = lu.get("kind", "point")
                    kind_counts[k] = kind_counts.get(k, 0) + 1

        # 3) 逐 kind 放灯（每类一次 ArrangementFromSpace）
        for kind, path in mapping.items():
            n = kind_counts.get(kind, 0)
            if n <= 0:
                logging.info("── 布灯 %s：IR 无该类灯具（%d 盏），跳过 ──", kind, n)
                continue
            ies = Path(path)
            if not ies.exists():
                logging.warning("灯具文件不存在，跳过 %s：%s", kind, ies)
                continue
            logging.info("── 布灯 %s（%d 盏）→ %s ──", kind, n, ies.name)
            lev = place_luminaires(ies, prototype_name=str(ies.stem))
            if not _last_ok(lev):
                bad = [e for e in lev if not e.ok]
                logging.error("布灯失败 %s：%s（%s）", kind,
                              bad[-1].detail if bad else "无输出", ies.name)
                return 1

    logging.info("完成。DIALux 已保存项目，去它的项目目录取 .evo。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
