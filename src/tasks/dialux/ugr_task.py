"""UGR 计算任务：计算点 + UGR 度量 → 读回最大眩光值并落 JSON。

真机链路（2026-10-08 手工探测的固化形态）：计算元件 → 计算点 → UGR 开关 →
步进/视角范围 → 计算 → 结果面板读数（实测 16.2 / 单次约 45 s）。

参数（``params`` 或 ``config`` 任一通道）：
- ``point``: ``[x, y, z]`` 计算点世界坐标；缺省则复用工程已有计算点
- ``step_deg`` / ``range_from`` / ``range_to`` / ``target``: UGR 评估参数
- ``out_json``: 结果落盘路径（默认 ``build/ugr_result.json``）

SOP 关联：``docs/standard-dialux-run.md`` 的计算段；结果字段与 29 页报表
文本层的「计算点 (RUG)」形态对齐，可直接进结果包。
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from src.workbench.task import Task, TaskContext, TaskResult

logger = logging.getLogger(__name__)

DEFAULT_OUT = "build/ugr_result.json"


class UgrTask(Task):
    """UGR 计算（计算点 + 度量 → 读回最大值）。"""

    name = "UGR 计算"
    priority = 45

    def run(self, ctx: TaskContext) -> TaskResult:
        # params/config 双通道（2026-10-17 起 TaskContext 声明 params、Flow 逐步下发）；
        # getattr 保留对旧 ctx 实现的兼容。
        params: Dict[str, Any] = getattr(ctx, "params", None) or (ctx.config or {})

        raw_point: Optional[list] = params.get("point")
        point = tuple(float(v) for v in raw_point) if raw_point else None
        step_deg = float(params.get("step_deg", 15))
        range_from = float(params.get("range_from", 0))
        range_to = float(params.get("range_to", 360))
        target = float(params.get("target", 19.0))
        out_json = params.get("out_json") or DEFAULT_OUT

        from src.executor.uia.ugr import measure_ugr

        ctx.log(
            f"UGR 计算：{'新点 ' + str(point) if point else '复用已有计算点'} "
            f"step={step_deg} range={range_from}-{range_to}"
        )
        result = measure_ugr(
            point=point,
            step_deg=step_deg,
            range_from=range_from,
            range_to=range_to,
            target=target,
            cancel_check=ctx.cancelled,
        )
        if not result.ok:
            bad = [e for e in result.events if not e.ok]
            reason = bad[-1].detail if bad else "无输出"
            return TaskResult(False, f"UGR 度量失败：{reason}", result.to_json())

        out = Path(out_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(result.to_json(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        ctx.log(f"UGR 结果：最大 {result.ugr_max}（目标 ≤{target}）→ {out}")
        return TaskResult(
            True,
            f"UGR 最大 {result.ugr_max}（目标 ≤{target}）",
            result.to_json(),
        )
