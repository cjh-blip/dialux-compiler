"""冒烟测试：真实写 DXF 文件 → main 流水线 → 产出 project.json + dry-run 计划。"""
import ezdxf
import json
import subprocess
import sys


def test_main_pipeline(tmp_path):
    dwg = tmp_path / "sample.dxf"
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()
    # 闭合房间 (mm)
    msp.add_lwpolyline(
        [(0, 0), (10000, 0), (10000, 8000), (0, 8000), (0, 0)],
        dxfattribs={"layer": "ROOM"},
    )
    # 灯具块参照 (mm)
    msp.add_blockref("LED-PNL-600", (5000, 4000, 2790), dxfattribs={"layer": "LUM"})
    doc.saveas(str(dwg))

    out = tmp_path / "project.json"
    result = subprocess.run(
        [sys.executable, "src/main.py", "--dwg", str(dwg), "--out", str(out)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, f"stderr:\n{result.stderr}"
    assert out.exists(), "应产出 project.json"
    data = json.loads(out.read_text())
    assert data["_meta"]["rooms"] == 1
    assert data["_meta"]["luminaires"] == 1
    assert data["_meta"]["rooms_closed"] == 1
    combined = (result.stdout + result.stderr).lower()
    assert "dry-run" in combined, f"应包含 dry-run 提示，stdout={result.stdout} stderr={result.stderr}"
