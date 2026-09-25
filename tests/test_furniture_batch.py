"""家具批量任务测试：IR 适配 + 拆包验收（mock place_furniture，不碰真机）。"""
import json
import zipfile
from pathlib import Path

from src.tasks.dialux.furniture_batch_task import (
    FurnitureBatchTask,
    _furniture_records,
    count_furniture_elements,
)


def _make_ir(tmp_path: Path, n_furn: int = 2):
    spaces = [{
        "id": "ROOM1", "name": "房间", "polygon": [[0, 0], [10, 0], [10, 8], [0, 8]],
        "luminaires": [],
    }]
    for i in range(n_furn):
        spaces.append({
            "id": f"F{i}", "name": f"家具_F{i}",
            "polygon": [[1 + i, 1], [2 + i, 1], [2 + i, 2], [1 + i, 2]],
            "luminaires": [],
        })
    ir = {"schema_version": "1", "project": {"name": "t", "source": "t", "units": "m"},
          "storeys": [{"level": 1, "spaces": spaces}]}
    p = tmp_path / "ir.json"
    p.write_text(json.dumps(ir, ensure_ascii=False), encoding="utf-8")
    return p


def test_furniture_records_adapter(tmp_path):
    """IR 伪 space → bbox/height_m/room_id 适配。"""
    recs = _furniture_records(_make_ir(tmp_path, 3), 0.75)
    assert len(recs) == 3
    r0 = recs[0]
    assert r0["id"] == "F0"
    assert r0["room_id"] == "ROOM1"
    assert r0["bbox"] == [1.0, 1.0, 2.0, 2.0]
    assert r0["height_m"] == 0.75


def test_furniture_records_skip_non_furniture(tmp_path):
    """非家具_前缀的 space 不进记录。"""
    recs = _furniture_records(_make_ir(tmp_path, 1), 0.75)
    assert all(r["id"].startswith("F") for r in recs)


def test_batch_all_fail_returns_false(tmp_path, monkeypatch):
    """place_furniture 全异常 → 任务失败。"""

    def boom(rec, **kw):
        raise RuntimeError("真机不可用")

    monkeypatch.setattr("src.executor.uia.furniture.place_furniture", boom)
    task = FurnitureBatchTask(ir_path=str(_make_ir(tmp_path, 2)),
                              evo_path=str(tmp_path / "no.evo"))
    result = task.run(type("C", (), {"log": staticmethod(lambda m: None),
                                     "cancelled": staticmethod(lambda: False)})())
    assert not result.ok


def test_batch_counts_evo_elements(tmp_path, monkeypatch):
    """成功路径：place_furniture mock 成功 + evo 拆包计数（造一个含 FurnitureElement 的假包）。"""

    monkeypatch.setattr(
        "src.executor.uia.furniture.place_furniture",
        lambda rec, **kw: [type("E", (), {"ok": True, "name": "furniture-done", "detail": ""})()],
    )
    # 造假 .evo：zip 里放含 2 个 FurnitureElement 的 dat
    evo = tmp_path / "t.evo"
    dat = "#1 = FurnitureElement (...);\n#2 = FurnitureElement (...);\n"
    with zipfile.ZipFile(evo, "w") as z:
        z.writestr("Project/ProjectData/ProjectData.dat", dat)
    task = FurnitureBatchTask(ir_path=str(_make_ir(tmp_path, 2)), evo_path=str(evo))
    result = task.run(type("C", (), {"log": staticmethod(lambda m: None),
                                     "cancelled": staticmethod(lambda: False)})())
    assert result.ok
    assert result.metrics["elements"] == 2


def test_count_furniture_elements_real_format(tmp_path):
    """拆包正则匹配真实 STEP 行格式。"""
    evo = tmp_path / "t.evo"
    with zipfile.ZipFile(evo, "w") as z:
        z.writestr("Project/ProjectData/ProjectData.dat",
                   "#577 = FurnitureElement('A',(...));\n#616 = LuminaireElement(...);\n")
    assert count_furniture_elements(evo) == 1
