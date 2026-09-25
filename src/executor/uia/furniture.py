"""DIALux FurnitureTool 通道：先验证 Cuboid 尺寸与位置控件，再保存工程。"""
from __future__ import annotations

import logging
import subprocess
from typing import List, Optional

from src.core.env import resource_path

from .driver import StepEvent, _parse

logger = logging.getLogger(__name__)

FURNITURE_PS1 = resource_path("src/executor/uia/furniture.ps1")

_STEPS = {
    "furniture-tool": "切换家具工具",
    "furniture-dimensions": "写入家具尺寸",
    "furniture-position": "写入家具位置",
    "furniture-save": "保存工程",
    "furniture-done": "完成",
}


def place_furniture(
    furniture: dict,
    *,
    process_name: str = "DIALux_x64",
    timeout_s: int = 180,
    cancel_check: Optional[callable] = None,
) -> List[StepEvent]:
    """在当前 DIALux 工程中放置一个 IR 家具记录。"""
    if not FURNITURE_PS1.exists():
        raise FileNotFoundError(f"家具驱动脚本缺失：{FURNITURE_PS1}")
    _validate_furniture(furniture)
    bbox = [float(value) for value in furniture["bbox"]]
    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(FURNITURE_PS1),
        "-Name", _ascii_name(furniture["id"]),
        "-Width", str(bbox[2] - bbox[0]),
        "-Length", str(bbox[3] - bbox[1]),
        "-Height", str(furniture["height_m"]),
        "-CenterX", str((bbox[0] + bbox[2]) / 2.0),
        "-CenterY", str((bbox[1] + bbox[3]) / 2.0),
        "-BaseZ", "0",
        "-ProcessName", process_name,
    ]
    try:
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
    except OSError as exc:
        raise RuntimeError(f"起不了家具 PowerShell 驱动：{exc}") from exc

    events: List[StepEvent] = []
    cancelled = False
    assert proc.stdout is not None
    for line in proc.stdout:
        if cancel_check is not None and cancel_check():
            proc.kill()
            cancelled = True
            break
        parsed = _parse(line)
        if parsed is None:
            if line.strip():
                logger.debug("家具驱动输出（非 STEP）：%s", line.rstrip())
            continue
        name, ok, detail = parsed
        event = StepEvent(
            name=name,
            title=_STEPS.get(name, name),
            ok=ok,
            detail=detail,
            progress=min(100.0, len(events) / len(_STEPS) * 100.0),
        )
        events.append(event)
        if not ok:
            break
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        logger.error("家具驱动超时 %ds，已终止", timeout_s)
    stderr = (proc.stderr.read() if proc.stderr else "") or ""
    if stderr.strip():
        logger.warning("家具驱动 stderr：%s", stderr.strip()[:500])
    if cancelled:
        events.append(StepEvent(
            "cancelled", "已停止", False,
            "停在家具放置中途，DIALux 里可能保留半成品",
            events[-1].progress if events else 0.0,
        ))
    return events


def _validate_furniture(furniture: dict) -> None:
    required = ("id", "room_id", "bbox", "height_m")
    missing = [key for key in required if key not in furniture]
    if missing:
        raise ValueError(f"家具缺少字段：{','.join(missing)}")
    if not furniture["room_id"]:
        raise ValueError(f"家具 {furniture['id']} 缺少 room_id")
    if len(furniture["bbox"]) != 4:
        raise ValueError(f"家具 {furniture['id']} bbox 必须有 4 个值")
    if float(furniture["height_m"]) <= 0:
        raise ValueError(f"家具 {furniture['id']} height_m 必须为正")


def _ascii_name(value: object) -> str:
    name = str(value)
    encoded = name.encode("ascii", errors="ignore").decode("ascii")
    return encoded or "FURNITURE"
