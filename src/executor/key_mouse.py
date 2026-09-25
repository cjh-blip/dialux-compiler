"""执行器：消费 ActionPlan。优先程序化接口，兜底键鼠重放。

安全原则 (agent-spec.md)：
- Agent 只生成 actions.jsonl，本 runner 独立执行。
- 执行前必须 dry-run 确认；失败 dump 上下文并停止，不无限重试。
"""
from __future__ import annotations

import json
import logging
from typing import List, Optional

from .actions import ActionResult  # 方便外部 from executor.key_mouse import load_plan

logger = logging.getLogger(__name__)

MAX_RETRY = 3


class ExecutorHalted(RuntimeError):
    """当 _do 返回 HALT 或 human_confirm 被拒绝时抛出。"""


class BaseExecutor:
    """三档接口基类：dry-run 只打日志；真实执行循环重试最多 3 次。"""

    def execute(self, plan: List[dict], dry_run: bool = True) -> None:
        if dry_run:
            logger.info("DRY-RUN 计划 (%d 条):", len(plan))
            for a in plan:
                logger.info("  %s", a)
            return
        for action in plan:
            for attempt in range(1, MAX_RETRY + 1):
                result = self._do(action)
                if result == "OK":
                    break
                if result == "HALT":
                    raise ExecutorHalted(
                        f"动作 {action.get('type')} 返回 HALT（id={action.get('id')}）"
                    )
                if attempt >= MAX_RETRY:
                    logger.error("动作 %s (id=%s) 重试 %d 次仍失败，停止并 dump 上下文",
                                 action.get("type"), action.get("id"), MAX_RETRY)
                    self._dump_context(action)
                    raise RuntimeError(f"executor aborted after retries at {action.get('type')}")
                logger.warning("动作 %s (id=%s) 第 %d 次返回 RETRY，重试中…",
                               action.get("type"), action.get("id"), attempt)

    def _do(self, action: dict) -> ActionResult:  # pragma: no cover - 子类实现
        raise NotImplementedError

    def _dump_context(self, action: dict) -> None:
        logger.error("CONTEXT: %s", json.dumps(action, ensure_ascii=False, default=str))


class ProgramExecutor(BaseExecutor):
    """程序化接口（A 档）：MVP1 占位实现，仅对 action 做语义分发。

    - human_confirm：调 CLI input()，接受 y/Y → OK，其他 → HALT。测试可 monkeypatch input。
    - 其他动作（create_project/storey/space, place_luminaire, run_calculation, export_report）
      全部占位返回 OK。
    """

    def _do(self, action: dict) -> ActionResult:
        atype = action.get("type")
        if atype == "human_confirm":
            msg = (action.get("inputs") or {}).get("message") or "HALT violations, confirm?"
            try:
                ans = input(f"HALT 违规需要人工确认：\n{msg}\n继续执行？[y/N]: ")
            except (EOFError, RuntimeError):
                # 非交互环境（CI / 测试 monkeypatch 可能不挂 input）：默认拒绝
                logger.warning("无交互输入，human_confirm 默认 HALT")
                return "HALT"
            if ans.strip().lower() in ("y", "yes"):
                return "OK"
            return "HALT"
        # 其余全部占位 OK（MVP1 不真实驱动外部）
        return "OK"


class KeyMouseExecutor(BaseExecutor):
    """键鼠重放（B 档）：坐标用相对锚点 + 控件特征，禁止硬编码绝对像素。

    MVP1：_locate_control 默认返回 None，触发 RuntimeError + CONTEXT dump。
    """

    def _locate_control(self, control: str) -> Optional[tuple]:
        """通过控件特征 (OCR/图像) 定位；未实现时返回 None。"""
        # TODO: 接入 OpenCV/PaddleOCR，按 control 名查找锚点
        return None

    def _wait_for(self, dialog: str, timeout: float = 5.0) -> bool:  # pragma: no cover
        return True

    def _do(self, action: dict) -> ActionResult:
        atype = action.get("type")
        try:
            if atype == "create_project":
                self._click("menu-file-new")
                self._type((action.get("inputs") or {}).get("name", ""))
            elif atype == "create_space":
                self._click("tool-polygon")
                inputs = action.get("inputs") or {}
                poly = inputs.get("polygon") or []
                for x, y, *_ in poly:
                    self._click_at_anchor("draw-canvas", offset=(x, y))
                self._wait_for("space-created", timeout=5.0)
            elif atype == "place_luminaire":
                self._click("tool-place-luminaire")
                inputs = action.get("inputs") or {}
                self._type(inputs.get("symbol") or "")
                self._click_at_anchor(
                    "draw-canvas",
                    offset=(inputs.get("x", 0), inputs.get("y", 0)),
                )
            elif atype == "human_confirm":
                # 键鼠档不直接弹 CLI 输入；由上层人工确认后继续（MVP1 兜底返回 HALT，避免静默跳过）
                logger.warning("KeyMouseExecutor 不支持 CLI 式 human_confirm，请先人工确认")
                return "HALT"
            elif atype == "run_calculation":
                self._press_shortcut("ctrl+shift+space")
                self._wait_for("calculation-done", timeout=30.0)
            elif atype == "export_report":
                self._click("menu-file-export-report")
            else:
                logger.debug("未实现的动作 %s，跳过", atype)
            return "OK"
        except RuntimeError:  # 控件定位失败等已明确抛错
            self._dump_context(action)
            raise
        except Exception as e:
            logger.warning("动作 %s 失败: %s", atype, e)
            return "RETRY"

    def _click(self, control: str) -> None:
        point = self._locate_control(control)
        if point is None:
            raise RuntimeError(f"无法定位控件: {control}")
        logger.debug("click %s @ %s", control, point)

    def _click_at_anchor(self, anchor: str, offset: tuple) -> None:
        base = self._locate_control(anchor)
        if base is None:
            raise RuntimeError(f"无法定位锚点: {anchor}")
        logger.debug("click relative %s +%s", anchor, offset)

    def _type(self, text: str) -> None:
        logger.debug("type %r", text)

    def _press_shortcut(self, combo: str) -> None:
        logger.debug("shortcut %s", combo)

    def _dump_context(self, action: dict) -> None:
        logger.error("CONTEXT: %s", json.dumps(action, ensure_ascii=False, default=str))
