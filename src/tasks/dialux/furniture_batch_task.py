"""家具批量建模任务：IR 家具伪 space → FurnitureTool 单件闭环循环。

复用隔壁会话已验证的 furniture.py::place_furniture 单件闭环
（probe_furniture_single.evo：FurnitureElement=1、坐标/尺寸全对），
本任务只做两件事：
1. IR 数据适配：家具伪 space（polygon）→ furniture 记录（bbox/height_m/room_id）
2. 批量循环 + 拆包验收（FurnitureElement 数量）

SOP Step 6（docs/standard-dialux-run.md v2）。
"""
from __future__ import annotations

import json
import logging
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.workbench.task import Task, TaskContext, TaskResult

logger = logging.getLogger(__name__)

DEFAULT_IR = "build/mvp3_ir.json"
DEFAULT_EVO = "build/demo_room.evo"
DEFAULT_TABLE_HEIGHT = 0.75   # SOP：会议桌工作面 0.75m


def _furniture_records(ir_path: Path, table_height: float) -> List[Dict[str, Any]]:
    """IR → furniture 记录列表（polygon → bbox，高默认桌面高）。"""
    ir = json.loads(ir_path.read_text(encoding="utf-8"))
    records: List[Dict[str, Any]] = []
    rooms = [sp for st in ir.get("storeys", []) for sp in st.get("spaces", [])
             if not sp.get("name", "").startswith("家具_")]
    room_id = rooms[0]["id"] if rooms else ""
    for st in ir.get("storeys", []):
        for sp in st.get("spaces", []):
            if not sp.get("name", "").startswith("家具_"):
                continue
            poly = sp.get("polygon") or []
            if len(poly) < 3:
                continue
            xs = [float(p[0]) for p in poly]
            ys = [float(p[1]) for p in poly]
            records.append({
                "id": sp["id"],
                "room_id": room_id,
                "bbox": [min(xs), min(ys), max(xs), max(ys)],
                "height_m": table_height,
            })
    return records


def count_furniture_elements(evo_path: Path) -> int:
    """.evo 拆包数 FurnitureElement（验收口径同灯具 LuminaireElement）。"""
    with zipfile.ZipFile(evo_path) as z:
        dat = z.read("Project/ProjectData/ProjectData.dat").decode("utf-8", "replace")
    import re
    return len(re.findall(r"#\d+ = FurnitureElement", dat))


class FurnitureBatchTask(Task):
    """批量家具建模：IR 22 件 → FurnitureTool 逐件 Cuboid。"""

    name = "批量家具建模"
    priority = 45

    def __init__(self, *, ir_path: str = DEFAULT_IR, evo_path: str = DEFAULT_EVO,
                 table_height: float = DEFAULT_TABLE_HEIGHT,
                 expect_count: Optional[int] = None):
        self.ir_path = Path(ir_path)
        self.evo_path = Path(evo_path)
        self.table_height = table_height
        self.expect_count = expect_count   # 缺省=IR 全部

    def run(self, ctx: TaskContext) -> TaskResult:
        from src.executor.uia.furniture import place_furniture

        records = _furniture_records(self.ir_path, self.table_height)
        if not records:
            return TaskResult(False, f"IR 无家具记录：{self.ir_path}")
        expect = self.expect_count if self.expect_count is not None else len(records)
        ctx.log(f"家具批量：{len(records)} 件待建（期望 {expect}）")

        done = failed = 0
        for i, rec in enumerate(records, 1):
            if ctx.cancelled():
                return TaskResult(False, f"已停止（{done}/{len(records)}）")
            try:
                events = place_furniture(rec, cancel_check=ctx.cancelled)
            except (RuntimeError, ValueError) as exc:
                failed += 1
                ctx.log(f"[{i}/{len(records)}] {rec['id']} 异常：{exc}")
                continue
            bad = [e for e in events if not e.ok]
            if bad or (events and events[-1].name.endswith("fail")):
                failed += 1
                ctx.log(f"[{i}/{len(records)}] {rec['id']} 失败：{bad[-1].detail if bad else '无输出'}")
                continue
            done += 1
            ctx.log(f"[{i}/{len(records)}] {rec['id']} 完成")

        ctx.log(f"家具批量结果：成功 {done} / 失败 {failed}")
        if done == 0:
            return TaskResult(False, "一件都没建成（见日志）")

        # 拆包验收（保存后 FurnitureElement 计数）
        if self.evo_path.exists():
            n = count_furniture_elements(self.evo_path)
            ctx.log(f"拆包 FurnitureElement={n}")
            if expect and n < expect:
                return TaskResult(False, f"家具数不足：FurnitureElement={n} < {expect}",
                                  {"done": done, "failed": failed, "elements": n})
            return TaskResult(True, f"家具批量完成 {done} 件（FurnitureElement={n}）",
                              {"done": done, "failed": failed, "elements": n})
        return TaskResult(True, f"家具批量完成 {done} 件（未拆包：{self.evo_path} 不存在）",
                          {"done": done, "failed": failed})
