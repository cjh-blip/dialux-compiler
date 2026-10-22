# -*- coding: utf-8 -*-
"""第十批（2026-10-22 第九枪编码损耗）：ui= 中文现场经管道逐字可读。

链路事实（按代码钉的根因，非回执推测）：ps1 的 STEP 走 stdout（Emit =
Write-Output），python 读子进程流的**解码环节**才是损耗点——原口径
text=True + encoding='utf-8' + errors='replace' 盲读 PS 5.1 按机器 OEM 码表
（中文 Windows＝GBK/cp936）写的字节，中文在读入瞬间变成 U+FFFD 序列（第九枪
回执文件本体 EF BF BD；同条 STEP 的 title 是 python 自产所以完好）。

本文件钉三件事：
1. 复现：GBK 字节被旧口径读成 U+FFFD（EF BF BD），与第九枪文件本体逐字同源；
2. 往返：utf-8（ps1 头部声明 OutputEncoding=UTF8 后的字节）与 GBK（机器现实）
   两条路进 _decode_pipe 都逐字可读，真子进程字节同验，STEP 解析后 ui= 中文在；
3. 结构：report.py 不再有 text=True 盲读、读循环按字节行过解码器、stderr 同口径；
   report.ps1 头部有 OutputEncoding 声明。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from src.executor.uia.driver import _parse
from src.executor.uia.report import _decode_pipe

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "step_ui_printer_cjk.txt"
REPORT_PY = ROOT / "src" / "executor" / "uia" / "report.py"
REPORT_PS1 = ROOT / "src" / "executor" / "uia" / "report.ps1"

SAMPLE = FIXTURE.read_bytes().decode("utf-8").rstrip("\n")


def test_fixture_cjk_detail_survives_both_pipe_encodings():
    """两条管道字节路都要逐字可读：ps1 声明 UTF8 生效走 utf-8，不生效是 GBK。"""
    assert _decode_pipe(SAMPLE.encode("utf-8")) == SAMPLE
    assert _decode_pipe(SAMPLE.encode("gbk")) == SAMPLE


def test_old_decode_reproduces_ninth_shot_fffd():
    """根因复现（最小样例，不是猜）：旧口径读 GBK 字节 = U+FFFD 序列；
    编成 utf-8 后即第九枪回执所记的 EF BF BD 文件本体。"""
    gbk_raw = SAMPLE.encode("gbk")
    old = gbk_raw.decode("utf-8", errors="replace")
    assert "\ufffd" in old
    assert b"\xef\xbf\xbd" in old.encode("utf-8")
    assert "\ufffd" not in _decode_pipe(gbk_raw)


def test_step_line_parses_with_readable_ui_after_decode():
    """含中文的现场经链路传递后必须逐字可读（往返到 STEP detail 层）。"""
    for enc in ("utf-8", "gbk"):
        parsed = _parse(_decode_pipe(SAMPLE.encode(enc)))
        assert parsed is not None, enc
        name, ok, detail = parsed
        assert name == "report-printer" and not ok
        assert "打印 常规" in detail          # ui= 中文逐字可读
        assert "btn1='打印(&P)'" in detail
        assert "default='Brother'" in detail


def test_real_subprocess_bytes_decode_readable():
    """正向面：真子进程吐 GBK 字节，走字节行解码同样逐字可读。"""
    code = (
        "import sys; "
        "sys.stdout.buffer.write('打印 状态: 脱机\\n'.encode('gbk')); "
        "sys.stdout.buffer.flush()"
    )
    out = subprocess.run(
        [sys.executable, "-c", code],
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    assert _decode_pipe(out) == "打印 状态: 脱机\n"


def test_report_py_reads_stdout_as_bytes_through_decoder():
    """结构：读循环按字节行过解码器、stderr 同口径、盲读口径移除。"""
    src = REPORT_PY.read_text(encoding="utf-8")
    assert "_decode_pipe(raw_line)" in src, "stdout 读循环必须按字节行过解码器"
    assert "_decode_pipe(proc.stderr.read())" in src, "stderr 同口径"
    assert 'encoding="utf-8"' not in src, "盲读口径必须已移除"
    assert "text=True" not in src
    assert "bufsize=1" not in src


def test_report_ps1_declares_pipe_encoding():
    """ps1 侧自产自销：进程输出编码显式声明为无 BOM UTF-8（解码器兜底仍在）。"""
    src = REPORT_PS1.read_text(encoding="utf-8")
    assert "[Console]::OutputEncoding" in src
    assert "UTF8Encoding($false)" in src, "无 BOM 声明"
