"""产品级 UGR 计算通道：计算点 + UGR 度量 + 步进/视角范围 → 计算 → 读回。

2026-10-08 真机手工探测（计算元件 → 计算点 + UGR 开关 + 步进/视角范围 →
CalculationButtonStart → 结果面板 16.2，单次约 45 s）的固化形态。
契约与 ``luminaire.py`` 一致：调用方给参数，本模块起 ``ugr.ps1``，
逐行解析 ``STEP`` 事件并把 ``ugr-read`` 的面板文本还原成结构化结果。

用法::

    from src.executor.uia.ugr import measure_ugr
    result = measure_ugr(point=(4.785, 5.5, 1.2))
    if result.ok:
        print(result.ugr_max)   # 16.2

依赖: ``ugr.ps1``（纯 ASCII，PowerShell UIA 驱动）。点坐标给空则复用
工程中已有的计算点（调用方负责它已被选中）。
"""
from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .driver import StepEvent, _parse
from src.core.env import resource_path

logger = logging.getLogger(__name__)

UGR_PS1 = resource_path("src/executor/uia/ugr.ps1")

# 与 ugr.ps1 的 Emit 一一对应。权重平均：每步都是秒级 UI 操作。
_UGR_STEPS = {
    "ugr-tool": "进入计算元件工具",
    "ugr-point": "放置/选定计算点",
    "ugr-metric": "打开 UGR 度量",
    "ugr-params": "写入步进与视角范围",
    "ugr-calc": "触发计算并等待完成",
    "ugr-read": "读回 UGR 结果",
    "ugr-done": "完成",
}

_ESC_RE = re.compile(r"\\u([0-9A-Fa-f]{4})")
# 面板文本里取「最大值」：中文「最大 16.2」/ 英文 "Maximum 16.2"
_MAX_RE = re.compile(r"(?:最大|Maximum)\D{0,8}?(\d+(?:\.\d+)?)", re.IGNORECASE)
# 兜底：UGR 值域 10~30，取文本里第一个一位整数+小数形式
_NUM_RE = re.compile(r"\b(\d{1,2}\.\d)\b")
# ugr-read 的 detail 尾部：target=19.0 step=15 from=0 to=360
_TAIL_RE = re.compile(
    r"target=(?P<target>-?\d+(?:\.\d+)?)\s+step=(?P<step>-?\d+(?:\.\d+)?)"
    r"\s+from=(?P<frm>-?\d+(?:\.\d+)?)\s+to=(?P<to>-?\d+(?:\.\d+)?)"
)


def _unescape(text: str) -> str:
    """把 ugr.ps1 的 ``\\uXXXX`` 转义还原为原文。"""
    return _ESC_RE.sub(lambda m: chr(int(m.group(1), 16)), text)


def _extract_ugr(text: str) -> Optional[float]:
    """从面板文本里抽最大 UGR 值。"""
    m = _MAX_RE.search(text)
    if m:
        return float(m.group(1))
    m = _NUM_RE.search(text)
    return float(m.group(1)) if m else None


@dataclass
class UgrResult:
    """一次 UGR 度量的结果；``events`` 与 StepEvent 契约一致。"""

    events: List[StepEvent] = field(default_factory=list)
    panel_text: str = ""
    ugr_max: Optional[float] = None
    target: Optional[float] = None
    step_deg: Optional[float] = None
    range_from: Optional[float] = None
    range_to: Optional[float] = None
    calc_sec: Optional[int] = None

    @property
    def ok(self) -> bool:
        return (
            bool(self.events)
            and all(e.ok for e in self.events)
            and self.events[-1].name == "ugr-done"
        )

    def to_json(self) -> dict:
        """结果包友好的 JSON（字段名与 29 页报表文本层对齐）。"""
        return {
            "ugr_max": self.ugr_max,
            "target": self.target,
            "step_deg": self.step_deg,
            "range_from": self.range_from,
            "range_to": self.range_to,
            "calc_sec": self.calc_sec,
            "panel_text": self.panel_text,
        }


def measure_ugr(
    *,
    point: Optional[Tuple[float, float, float]] = None,
    step_deg: float = 15.0,
    range_from: float = 0.0,
    range_to: float = 360.0,
    target: float = 19.0,
    process_name: str = "DIALux_x64",
    timeout_s: int = 120,
    calc_timeout_s: int = 300,
    cancel_check: Optional[callable] = None,
    on_step: Optional[callable] = None,
    **id_overrides: str,
) -> UgrResult:
    """在当前 DIALux 工程里做一次 UGR 度量并读回最大值。

    参数:
        point: 计算点世界坐标 ``(x, y, z)``；``None`` 表示复用工程里已有的
            计算点（调用方负责它已选中）。
        step_deg / range_from / range_to: 视角评估参数（默认 15° / 0-360°）。
        target: 目标眩光上限（仅随结果回传，供报告标注）。
        id_overrides: 逃生舱——``ugr_check_id`` / ``step_id`` / ``range_from_id``
            / ``range_to_id`` / ``result_id``，用于钉死 DIALux 未文档化的
            控件 AutomationId（参见 ugr.ps1 头部说明）。
        cancel_check: 每读一行调用，返回 True 时中止（停在步与步之间）。

    返回: ``UgrResult``；``result.ok`` 判断是否跑完，``result.events`` 看逐步状态。
    抛 FileNotFoundError 当 ``ugr.ps1`` 缺失；RuntimeError 当 PowerShell 起不来。
    """
    if not UGR_PS1.exists():
        raise FileNotFoundError(f"UGR 驱动脚本缺失：{UGR_PS1}")

    cmd = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(UGR_PS1),
        "-StepDeg", str(step_deg),
        "-RangeFromDeg", str(range_from),
        "-RangeToDeg", str(range_to),
        "-Target", str(target),
        "-ProcessName", process_name,
        "-CalcTimeoutMs", str(int(calc_timeout_s * 1000)),
    ]
    if point is not None:
        cmd += ["-PointX", str(point[0]), "-PointY", str(point[1]), "-PointZ", str(point[2])]
    for key, flag in (
        ("ugr_check_id", "-UgrCheckId"),
        ("step_id", "-StepId"),
        ("range_from_id", "-RangeFromId"),
        ("range_to_id", "-RangeToId"),
        ("result_id", "-ResultId"),
    ):
        val = id_overrides.get(key)
        if val:
            cmd += [flag, str(val)]

    logger.info(
        "UGR 驱动启动：%s step=%s range=%s-%s",
        "new point" if point else "existing point",
        step_deg,
        range_from,
        range_to,
    )

    result = UgrResult()
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as exc:
        raise RuntimeError(f"起不了 PowerShell：{exc}") from exc

    assert proc.stdout is not None
    cancelled = False
    for line in proc.stdout:
        if cancel_check is not None and cancel_check():
            proc.kill()
            cancelled = True
            logger.warning("收到停止请求，UGR 度量中止（DIALux 内是半成品）")
            break
        parsed = _parse(line)
        if parsed is None:
            if line.strip():
                logger.debug("UGR 输出（非 STEP）：%s", line.rstrip())
            continue
        name, ok, detail = parsed
        ev = StepEvent(
            name=name,
            title=_UGR_STEPS.get(name, name),
            ok=ok,
            detail=detail,
            progress=min(100.0, len(result.events) / len(_UGR_STEPS) * 100.0),
        )
        result.events.append(ev)
        logger.info(
            "[%5.1f%%] %s %s%s",
            ev.progress,
            ev.title,
            "OK" if ok else "失败",
            f"（{detail}）" if detail else "",
        )
        if on_step is not None:
            on_step(ev)
        if name == "ugr-calc" and ok:
            m = re.search(r"sec=(\d+)", detail)
            if m:
                result.calc_sec = int(m.group(1))
        if name == "ugr-read":
            _absorb_read(result, detail)
        if not ok:
            break

    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        logger.error("UGR 驱动超时 %ds，已杀掉", timeout_s)
    stderr = (proc.stderr.read() if proc.stderr else "") or ""
    if stderr.strip():
        logger.warning("UGR stderr：%s", stderr.strip()[:300])
    if cancelled:
        result.events.append(
            StepEvent(
                "cancelled",
                "已停止",
                False,
                "停在 UGR 度量中途，DIALux 里是半成品",
                result.events[-1].progress if result.events else 0.0,
            )
        )
    return result


def _absorb_read(result: UgrResult, detail: str) -> None:
    """把 ugr-read 的 detail 拆成面板文本 + 参数（文本是 \\uXXXX 转义）。"""
    body = detail
    if body.startswith("text="):
        body = body[len("text="):]
    tail_m = _TAIL_RE.search(body)
    if tail_m:
        head = body[: tail_m.start()]
        result.target = float(tail_m.group("target"))
        result.step_deg = float(tail_m.group("step"))
        result.range_from = float(tail_m.group("frm"))
        result.range_to = float(tail_m.group("to"))
    else:
        head = body
    result.panel_text = _unescape(head).strip()
    result.ugr_max = _extract_ugr(result.panel_text)
