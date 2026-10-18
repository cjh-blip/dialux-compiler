#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""真机动作薄 runner（光枢队列 E 阶段1，2026-10-18）。

壳侧（optiflow-app 的 ``core.run_real``）用子进程调本脚本驱动 DIALux。契约：

  stdout 每行一个 JSON 对象——
    {"type":"step","name":…,"title":…,"ok":…,"detail":…,"progress":…}
    {"type":"receipt","ok":bool,"action":…,"data":{…},"err":"人话（失败时非空）"}
  日志一律走 stderr；通道异常收进 ``receipt.err``（类型＋人话），不甩栈。

用法::

    python scripts/real_action.py --list
    python scripts/real_action.py import_stf --params-json '{"stf": "room.stf"}'

纪律：**只加不改**——本文件是新增薄壳；五个通道的既有行为不动，
``on_step`` 是通道侧本轮新增的可选回调（缺省 None 不改行为）。
取消语义：收到 SIGTERM/SIGINT 置位，通道的 ``cancel_check`` 每读一行检查——
停在步与步之间，DIALux 里是半成品（界面必须如实提示，不假装干净退出）。
"""
from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Tuple

REPO = Path(__file__).resolve().parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

_CANCELLED = False

Channel = Callable[[Dict[str, Any], Callable[[Any], None], Callable[[], bool]],
                   Tuple[bool, Dict[str, Any], str]]


# ------------------------------------------------------------------ 内部
def _mark_cancel(_sig: Any = None, _frame: Any = None) -> None:
    global _CANCELLED
    _CANCELLED = True


def _cancelled() -> bool:
    return _CANCELLED


def _emit(event: Any) -> None:
    """StepEvent → stdout JSONL 行（壳侧逐行消费做进度）。"""
    print(json.dumps({
        "type": "step",
        "name": event.name,
        "title": event.title,
        "ok": bool(event.ok),
        "detail": event.detail or "",
        "progress": round(float(event.progress or 0.0), 1),
    }, ensure_ascii=False), flush=True)


def _events_err(events: Any) -> str:
    """事件表 → 人话失败原因（取最后一步，不编数）。"""
    if not events:
        return "通道无事件（没跑起来）"
    last = events[-1]
    return f"{last.title}：{last.detail or '失败'}"


def _ev_ok(events: Any) -> bool:
    return bool(events) and all(getattr(e, "ok", False) for e in events)


# ------------------------------------------------------------------ 五通道
def _ch_import_stf(params: Dict[str, Any], emit: Any, cancel: Any) -> Tuple[bool, Dict[str, Any], str]:
    from src.executor.uia.driver import run_import, succeeded

    stf = params.get("stf")
    if not stf:
        raise ValueError("缺参数 stf（STF 文件路径）")
    events = run_import(stf, on_step=emit, cancel_check=cancel)
    ok = succeeded(events)
    return ok, {"steps": len(events), "stf": str(stf)}, "" if ok else _events_err(events)


def _ch_place_luminaires(params: Dict[str, Any], emit: Any, cancel: Any) -> Tuple[bool, Dict[str, Any], str]:
    from src.executor.uia.luminaire import place_luminaires

    ies = params.get("ies")
    if not ies:
        raise ValueError("缺参数 ies（合规会员厂商 IES/LDT/GLDF 文件路径）")
    events = place_luminaires(
        ies,
        prototype_name=str(params.get("prototype_name") or ""),
        count_x=int(params.get("count_x") or 0),
        count_y=int(params.get("count_y") or 0),
        cancel_check=cancel,
        on_step=emit,
    )
    ok = _ev_ok(events)
    return ok, {"steps": len(events), "ies": str(ies)}, "" if ok else _events_err(events)


def _ch_place_furniture(params: Dict[str, Any], emit: Any, cancel: Any) -> Tuple[bool, Dict[str, Any], str]:
    from src.executor.uia.furniture import place_furniture

    furniture = params.get("furniture")
    if not isinstance(furniture, dict):
        raise ValueError("缺参数 furniture（IR 家具记录对象，含 id/bbox/height_m）")
    events = place_furniture(furniture, cancel_check=cancel, on_step=emit)
    ok = _ev_ok(events)
    return ok, {"steps": len(events)}, "" if ok else _events_err(events)


def _ch_ugr(params: Dict[str, Any], emit: Any, cancel: Any) -> Tuple[bool, Dict[str, Any], str]:
    from src.executor.uia.ugr import measure_ugr

    point = params.get("point")
    if point is not None:
        if not (isinstance(point, (list, tuple)) and len(point) == 3):
            raise ValueError("参数 point 必须是 [x, y, z] 或空（空＝复用工程计算点）")
        point = tuple(float(v) for v in point)
    ids = params.get("ids") or {}
    if not isinstance(ids, dict):
        raise ValueError("参数 ids 必须是对象（控件 id 逃生舱，可空）")
    result = measure_ugr(
        point=point,
        step_deg=float(params.get("step_deg") or 15.0),
        range_from=float(params.get("range_from") or 0.0),
        range_to=float(params.get("range_to") or 360.0),
        target=float(params.get("target") or 19.0),
        cancel_check=cancel,
        on_step=emit,
        **{str(k): str(v) for k, v in ids.items()},
    )
    data = result.to_json()
    data["steps"] = len(result.events)
    return result.ok, data, "" if result.ok else _events_err(result.events)


def _ch_export_report(params: Dict[str, Any], emit: Any, cancel: Any) -> Tuple[bool, Dict[str, Any], str]:
    from src.executor.uia.report import export_report, extract_text_layer

    pdf = params.get("pdf")
    if not pdf:
        raise ValueError("缺参数 pdf（输出 PDF 绝对路径）")
    ids = params.get("ids") or {}
    if not isinstance(ids, dict):
        raise ValueError("参数 ids 必须是对象（控件 id 逃生舱：report.ps1 是骨架，首跑用它钉 id）")
    events = export_report(pdf, cancel_check=cancel, on_step=emit,
                           **{str(k): str(v) for k, v in ids.items()})
    ok = _ev_ok(events)
    data: Dict[str, Any] = {"steps": len(events), "pdf": str(pdf)}
    if not ok:
        return False, data, _events_err(events)
    try:
        text = extract_text_layer(pdf)
        data["text_chars"] = len(text)
        data["pages"] = text.count("===== PAGE")
    except Exception as exc:                      # 打印段成了、文本层挂了：如实分段报
        return False, data, f"打印成功但文本层提取失败：{type(exc).__name__}：{exc}"
    return True, data, ""


ACTIONS: Dict[str, Channel] = {
    "import_stf": _ch_import_stf,
    "place_luminaires": _ch_place_luminaires,
    "place_furniture": _ch_place_furniture,
    "ugr": _ch_ugr,
    "export_report": _ch_export_report,
}


# ------------------------------------------------------------------ 入口
def _receipt(action: str, ok: bool, data: Dict[str, Any] | None = None, err: str = "") -> None:
    print(json.dumps({"type": "receipt", "ok": bool(ok), "action": action,
                      "data": data or {}, "err": err}, ensure_ascii=False), flush=True)


def main(argv: Any = None) -> int:
    ap = argparse.ArgumentParser(prog="real_action.py", description="光枢真机动作 runner（UIA→DIALux）")
    ap.add_argument("action", nargs="?", default="", help="动作名；--list 看清单")
    ap.add_argument("--params-json", default="{}", help="动作参数（JSON 对象）")
    ap.add_argument("--list", action="store_true", help="列出可用动作后退出")
    args = ap.parse_args(argv)

    if args.list:
        print(json.dumps({"actions": sorted(ACTIONS)}, ensure_ascii=False))
        return 0

    logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                        format="%(levelname)s %(name)s: %(message)s")
    signal.signal(signal.SIGTERM, _mark_cancel)
    signal.signal(signal.SIGINT, _mark_cancel)

    if args.action not in ACTIONS:
        _receipt(args.action or "?", False,
                 err=f"未知动作：{args.action or '（空）'}；--list 看清单（{'、'.join(sorted(ACTIONS))}）")
        return 1
    try:
        params = json.loads(args.params_json or "{}")
        if not isinstance(params, dict):
            raise ValueError("参数必须是 JSON 对象")
    except (ValueError, json.JSONDecodeError) as exc:
        _receipt(args.action, False, err=f"参数不是合法 JSON：{exc}")
        return 1

    try:
        ok, data, err = ACTIONS[args.action](params, _emit, _cancelled)
    except Exception as exc:                      # 通道异常一律收成人话（不甩栈）
        _receipt(args.action, False, err=f"{type(exc).__name__}：{exc}")
        return 1
    _receipt(args.action, bool(ok), data=data, err=err)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
