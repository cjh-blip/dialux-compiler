# -*- coding: utf-8 -*-
"""real_action 薄 runner 契约：JSONL step/receipt、异常收人话不甩栈、通道 on_step 可用。

全部用假通道/内省完成，**不碰 PowerShell、不碰真机**（阶段1 在 Mac 可跑）。
"""
from __future__ import annotations

import importlib.util
import inspect
import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location("real_action", REPO / "scripts" / "real_action.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse_out(capsys) -> list[dict]:
    lines = [ln for ln in capsys.readouterr().out.splitlines() if ln.strip()]
    return [json.loads(ln) for ln in lines]


def test_list_has_five_actions(capsys) -> None:
    ra = _load()
    assert ra.main(["--list"]) == 0
    (payload,) = _parse_out(capsys)
    assert payload["actions"] == ["export_report", "import_stf", "place_furniture",
                                  "place_luminaires", "ugr"]


def test_ok_channel_streams_steps_then_receipt(capsys) -> None:
    """正常路：step 行逐个流出（带 progress），最后一行 receipt ok=true，退出 0。"""
    from src.executor.uia.driver import StepEvent

    ra = _load()

    def fake(params, emit, cancel):
        emit(StepEvent("attach", "挂到 DIALux 进程", True, "", 10.0))
        emit(StepEvent("done", "完成", True, "", 100.0))
        return True, {"steps": 2}, ""

    ra.ACTIONS["import_stf"] = fake
    assert ra.main(["import_stf", "--params-json", "{}"]) == 0
    out = _parse_out(capsys)
    assert [o["type"] for o in out] == ["step", "step", "receipt"]
    assert out[0]["progress"] == 10.0 and out[1]["name"] == "done"
    assert out[-1] == {"type": "receipt", "ok": True, "action": "import_stf",
                       "data": {"steps": 2}, "err": ""}


def test_channel_exception_becomes_human_receipt(capsys) -> None:
    """通道抛异常 → receipt.err 带类型＋人话，输出里没有 Traceback，退出 1。"""
    ra = _load()

    def boom(params, emit, cancel):
        raise ValueError("缺参数 stf（STF 文件路径）")

    ra.ACTIONS["import_stf"] = boom
    assert ra.main(["import_stf"]) == 1
    out = _parse_out(capsys)
    (receipt,) = out
    assert receipt["ok"] is False
    assert "ValueError" in receipt["err"] and "缺参数 stf" in receipt["err"]
    assert "Traceback" not in receipt["err"]


def test_false_channel_fails_with_last_event_detail(capsys) -> None:
    """通道返回不成功 → receipt err=最后一步人话，退出 1。"""
    ra = _load()
    ra.ACTIONS["ugr"] = lambda p, e, c: (False, {"steps": 3}, "UGR 计算：控件没找到")
    assert ra.main(["ugr"]) == 1
    (receipt,) = _parse_out(capsys)
    assert receipt["ok"] is False and receipt["err"] == "UGR 计算：控件没找到"


def test_unknown_action_and_bad_json_rejected(capsys) -> None:
    ra = _load()
    assert ra.main(["nope"]) == 1
    (r1,) = _parse_out(capsys)
    assert "未知动作" in r1["err"] and "import_stf" in r1["err"]

    ra.ACTIONS["import_stf"] = lambda p, e, c: (True, {}, "")
    assert ra.main(["import_stf", "--params-json", "{broken"]) == 1
    (r2,) = _parse_out(capsys)
    assert "不是合法 JSON" in r2["err"]


def test_all_five_channels_accept_on_step() -> None:
    """本轮 dc 四处 on_step 增补的钉子（driver 原生就有）：签名缺了就红。"""
    from src.executor.uia.driver import run_import
    from src.executor.uia.furniture import place_furniture
    from src.executor.uia.luminaire import place_luminaires
    from src.executor.uia.report import export_report
    from src.executor.uia.ugr import measure_ugr

    for fn in (run_import, place_luminaires, place_furniture, measure_ugr, export_report):
        assert "on_step" in inspect.signature(fn).parameters, fn.__name__
        assert "cancel_check" in inspect.signature(fn).parameters, fn.__name__
