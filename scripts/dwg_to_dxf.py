"""DWG → DXF 转换：调用 ODA File Converter 批处理。

ODA 不支持按单文件转，只能按目录批处理。所以 convert_one 会：
1. 建临时输入目录 `<stem>_in`
2. 拷贝单 dwg 进去
3. 调用 ODA 输出到 `<out_dir>`
4. 返回生成的 dxf 绝对路径。
"""
from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_ACAD = "ACAD2018"

# 支持 `python scripts/dwg_to_dxf.py` 和测试导入都能找到 src 包
if __package__ in (None, ""):
    try:
        from src.core.env import get_oda_path
    except ImportError:
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
        from src.core.env import get_oda_path
else:
    from src.core.env import get_oda_path


# 旧接口兼容（tests/test_scripts.py 仍可能引用）
def resolve_oda_path(override: Optional[str] = None) -> Path:
    return get_oda_path(override)


def convert_one(src: Path, out_dir: Optional[Path] = None, acad: str = DEFAULT_ACAD,
                oda_override: Optional[str] = None) -> Path:
    """把单个 DWG/DXF（ODA 也能转 DXF 版本）转换为目标 DXF，返回 DXF 路径。"""
    src = Path(src).resolve()
    if not src.exists():
        raise FileNotFoundError(f"输入文件不存在: {src}")

    oda = get_oda_path(oda_override)
    if out_dir is None:
        out_dir = Path("build/_dxf_out").resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 创建临时输入目录（ODA 按目录批处理）
    tmp_root = Path("build/_cache").resolve()
    tmp_root.mkdir(parents=True, exist_ok=True)
    in_dir = Path(tempfile.mkdtemp(prefix=f"{src.stem}_in_", dir=str(tmp_root)))
    try:
        shutil.copy2(src, in_dir / src.name)
    except Exception:
        shutil.rmtree(in_dir, ignore_errors=True)
        raise

    target_out = out_dir / (src.stem + ".dxf")
    # ODA 命令：ODAFileConverter <in_dir> <out_dir> <acad_version> <DXF/DWG> <recurse> <audit> <file_filter>
    # 参考 ODA 文档：DXF 0 0 = ASCII DXF, no recurse, no audit
    cmd = [
        str(oda),
        str(in_dir),
        str(out_dir),
        acad,
        "DXF",
        "0",
        "0",
        f"*.{src.suffix.lstrip('.')}",
    ]
    logger.info("调用 ODA: %s", " ".join(cmd))
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    finally:
        shutil.rmtree(in_dir, ignore_errors=True)

    if proc.returncode != 0:
        logger.error("ODA stderr: %s", proc.stderr)
        raise RuntimeError(
            f"ODA File Converter 失败 (exit={proc.returncode})：\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
        )
    if not target_out.exists():
        # ODA 可能把 DXF 写入原文件名而非 .dxf（罕见），尝试找同 stem 的 dxf
        candidates = list(out_dir.glob(src.stem + "*"))
        if candidates:
            target_out = sorted(candidates)[0]
        else:
            raise FileNotFoundError(
                f"ODA 执行成功，但没找到生成的 DXF 文件：期望 {target_out}\n"
                f"stdout:\n{proc.stdout}"
            )
    logger.info("DWG → DXF 完成：%s → %s", src, target_out)
    return target_out


def main() -> None:
    p = argparse.ArgumentParser(description="DWG → DXF 批量转换（调用 ODA File Converter）")
    p.add_argument("input", help="输入 .dwg/.dxf 文件，或包含这些文件的目录")
    p.add_argument("-o", "--out", default="build/_dxf_out", help="输出目录")
    p.add_argument("--acad", default=DEFAULT_ACAD, help="目标 ACAD 版本，默认 ACAD2018")
    p.add_argument("--oda", help="ODA File Converter.exe 路径（默认取环境变量 ODA_PATH 或系统安装）")
    args = p.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    src = Path(args.input)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if src.is_dir():
        files = sorted([f for f in src.iterdir() if f.suffix.lower() in (".dwg", ".dxf")])
        if not files:
            logger.warning("目录中没有 DWG/DXF 文件：%s", src)
            return
        for f in files:
            try:
                convert_one(f, out_dir, acad=args.acad, oda_override=args.oda)
            except Exception as e:  # noqa
                logger.error("跳过 %s：%s", f, e)
    else:
        convert_one(src, out_dir, acad=args.acad, oda_override=args.oda)


if __name__ == "__main__":
    main()
