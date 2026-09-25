"""悬浮小部件：贴在 DIALux 窗口上，显示真进度并驱动整条流水线。

方案来源（抄的是方案，不是代码）
--------------------------------
- **BGI**（better-genshin-impact，GPL-3.0）：点启动 → 目标程序拉到前台 →
  工具自己缩成一个半透明小挂件 → 然后开始操作。它的 ``MaskWindow.xaml.cs``
  用 ``RefreshPositionForNormal()`` 不断把自己重新贴到游戏窗口的 rect 上，
  坐标要除以 DPI 缩放。这里照这个思路做，但**一行源码都没抄**——BGI 是
  GPL-3.0，抄源码会把整个项目传染成 GPL-3.0。用到的 Win32 窗口标志是微软公开
  API，不属于 BGI 的创作。
- **Mrite**（MIT，可以抄）：``renderer/panels/progress.js`` 的四态步骤列表
  （pending / active / completed / error）+ 进度条。这里的 STATE_GLYPH 就是它。
  但 Mrite 那条 5%→95% 的假进度曲线（``renderer/agent-events.js:81-130``）
  **不抄**——它是因为 LLM agent 的步数不可知才要造信心，我们的步数是确定的，
  照抄反而是降级。

与 BGI 的一个结构性差别
----------------------
BGI 必须让游戏保持前台，因为它用模拟输入（SendInput）。我们走 UIA + 窗口消息，
**不需要 DIALux 有焦点**，所以这个挂件不必做点击穿透，可以留一个真能点的
「停止」按钮。这是实测结论：后台导入和保存都成功过。

用法::

    python -m src.ui.overlay
"""
from __future__ import annotations

import ctypes
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# 必须在 QApplication 之前声明 per-monitor DPI 感知，否则 GetWindowRect 拿到的
# 物理像素和 Qt 的逻辑像素对不上，挂件会贴偏。
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:  # noqa: BLE001 - 老系统没这个 API，退化成系统 DPI 感知
    pass

import win32gui  # noqa: E402
from PySide6 import QtCore, QtGui, QtWidgets  # noqa: E402

from src.executor.uia.driver import run_import  # noqa: E402

DWG = "布局图.dwg"
DWG_LIGHTING = "灯具图.dwg"
CONFIG = "tests/fixtures/sample_parse_config.json"
IR_OUT = "build/demo_ir.json"
STF_OUT = "build/demo_room.stf"

# 步骤表。权重是 2026-09-05 实测的耗时占比（解析 2.62s / STF 0.48s / UIA 6.81s，
# 合计 9.91s），凑成 100 好让「累计权重」直接就是百分比。
# 2026-09-07 扩展：加入放灯链路（导入 NPTLED / Re295 + 排布），让悬浮窗实时
# 显示「正在做什么」——同 BetterGI MaskWindow 的执行动作反馈。
ROWS = [
    ("launch", "打开/挂到 DIALux", 2.0),
    ("parse", "解析图纸 DWG→DXF→IR", 20.0),
    ("stf", "导出 STF 房间壳", 4.0),
    ("import", "导入 STF 建房间", 18.0),
    ("lum-point", "导入筒灯型号 NPTLED", 10.0),
    ("arrange-point", "排布筒灯", 12.0),
    ("lum-linear", "导入线性灯 Re295", 10.0),
    ("arrange-linear", "排布线性灯", 12.0),
    ("save", "保存 .evo", 12.0),
]

# UIA 那 11 个细步骤归并到上面 4 行里。
UIA_TO_ROW = {
    "attach": "import", "activate": "import",
    "menu-file": "import", "menu-import": "import", "menu-import-stf": "import",
    "dialog": "import", "dialog-filename": "import", "import": "import",
    "import-settled": "import",
    "save": "save", "done": "save",
}

# 抄 Mrite renderer/panels/progress.js 的四态字形（MIT）
STATE_GLYPH = {"pending": "—", "active": "●", "completed": "OK", "error": "!!"}
STATE_COLOR = {"pending": "#6b7280", "active": "#38bdf8",
               "completed": "#22c55e", "error": "#ef4444"}


def find_dialux() -> int:
    """返回 DIALux 主窗口 hwnd，找不到返回 0。

    认的是 WPF 的 HwndWrapper 类名 + 可见 + 有标题，不认进程名，因为
    DIALux.exe 是个没有窗口的启动器，真界面在 DIALux_x64.exe 里。
    """
    hit = []

    def _cb(h, _):
        try:
            if (win32gui.IsWindowVisible(h)
                    and win32gui.GetClassName(h).startswith("HwndWrapper[DIALux")
                    and "DIALux evo" in win32gui.GetWindowText(h)):
                hit.append(h)
        except Exception:  # noqa: BLE001
            pass
        return True

    win32gui.EnumWindows(_cb, None)
    return hit[0] if hit else 0


class Pipeline(QtCore.QThread):
    """在后台跑完整条流水线，把每一行的状态变化发出来。"""

    row_state = QtCore.Signal(str, str)     # row_key, state
    progress = QtCore.Signal(float)         # 0~100
    log = QtCore.Signal(str)
    done = QtCore.Signal(bool, str)         # ok, 结论

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop = False
        self.link_start = True   # 是否自动打开 DIALux（由 UI 勾选框注入）

    def request_stop(self):
        self._stop = True

    # ---- 权重累加。只在一行真正完成时才加，进度条不会提前跑。
    def _advance(self, row_key: str):
        self._done_weight += dict((k, w) for k, _, w in ROWS)[row_key]
        self.progress.emit(min(100.0, self._done_weight))

    def _shell(self, cmd: list, row_key: str) -> bool:
        """跑子命令，逐行实时转发日志（BetterGI LogTextBox 模式）。

        encoding 必须写死 utf-8——子进程的中文日志用 GBK 解会炸。
        """
        self.row_state.emit(row_key, "active")
        try:
            p = subprocess.Popen(
                cmd, cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, encoding="utf-8", errors="replace", bufsize=1,
            )
        except OSError as exc:
            self.row_state.emit(row_key, "error")
            self.log.emit(f"起不了进程：{exc}")
            return False
        assert p.stdout is not None
        rc = None
        for line in p.stdout:
            if self._stop:
                p.kill()
                rc = -1
                break
            if line.strip():
                self.log.emit(line.strip()[:110])
        if rc is None:
            rc = p.wait()
        if rc != 0:
            self.row_state.emit(row_key, "error")
            self.log.emit(f"退出码 {rc}")
            return False
        self.row_state.emit(row_key, "completed")
        self._advance(row_key)
        return True

    def run(self):
        self._done_weight = 0.0
        py = sys.executable

        # 0) 自动开/挂 DIALux（同 BetterGI「同时启动原神」，由 UI 勾选框控制）
        self.row_state.emit("launch", "active")
        if not self.link_start:
            # 用户没勾：要求已开，挂到现有窗口
            if find_dialux():
                self.row_state.emit("launch", "completed")
                self._advance("launch")
            else:
                self.row_state.emit("launch", "error")
                self.log.emit("未勾「同时启动」，且 DIALux 没开")
                self.done.emit(False, "DIALux 没开，请勾「同时启动」或先打开")
                return
        else:
            try:
                from src.ui.launcher import launch_dialux
            except Exception:  # noqa: BLE001 - 打包/依赖差异兜底
                self.row_state.emit("launch", "error")
                self.log.emit("launcher 模块不可用")
                self.done.emit(False, "launcher 模块不可用")
                return
            if launch_dialux():
                self.row_state.emit("launch", "completed")
                self._advance("launch")
            else:
                self.row_state.emit("launch", "error")
                self.log.emit("DIALux 启动超时")
                self.done.emit(False, "DIALux 没起来")
                return
        if self._stop:
            self.done.emit(False, "已停止（还没碰 DIALux，无残留）")
            return

        self.row_state.emit("parse", "active")
        if not self._shell([py, "src/main.py", "--dwg", DWG,
                            "--dwg-lighting", DWG_LIGHTING, "--config", CONFIG,
                            "--out", IR_OUT], "parse"):
            self.done.emit(False, "解析失败")
            return
        if self._stop:
            self.done.emit(False, "已停止（还没碰 DIALux，无残留）")
            return

        self.row_state.emit("stf", "active")
        if not self._shell([py, "-m", "src.exporter.stf", "--validate",
                            IR_OUT, STF_OUT], "stf"):
            self.done.emit(False, "STF 导出失败")
            return
        if self._stop:
            self.done.emit(False, "已停止（还没碰 DIALux，无残留）")
            return

        # UIA 段：把 11 个细步骤映射到 4 行，行内第一个细步骤点亮，最后一个收尾。
        row_seen = set()

        def on_step(ev):
            row = UIA_TO_ROW.get(ev.name)
            if row is None:
                return
            if not ev.ok:
                self.row_state.emit(row, "error")
                self.log.emit(f"{ev.title}：{ev.detail}")
                return
            if row not in row_seen:
                row_seen.add(row)
                self.row_state.emit(row, "active")
            self.log.emit(ev.title)
            # 行内最后一个细步骤 → 这一行完成
            tail = [k for k, v in UIA_TO_ROW.items() if v == row][-1]
            if ev.name == tail:
                self.row_state.emit(row, "completed")
                self._advance(row)

        try:
            events = run_import(STF_OUT, on_step=on_step,
                               cancel_check=lambda: self._stop)
        except RuntimeError as exc:
            self.log.emit(str(exc)[:160])
            self.done.emit(False, "预检没通过")
            return

        if events and events[-1].name == "cancelled":
            self.done.emit(False, events[-1].detail)
            return
        ok = bool(events) and all(e.ok for e in events) and events[-1].name == "done"
        if not ok:
            self.progress.emit(self._done_weight)
            self.done.emit(False, "建壳失败")
            return
        self.progress.emit(min(100.0, self._done_weight))

        # 放灯：两批（point→NPTLED, linear→Re295），实时显示每步
        from src.executor.uia.luminaire import _last_ok, place_luminaires

        def place(kind, ies, row_import, row_arrange):
            self.row_state.emit(row_import, "active")
            self.log.emit(f"布灯 {kind}：{Path(ies).name}")
            lev = place_luminaires(ies, prototype_name=str(Path(ies).stem))
            if not _last_ok(lev):
                bad = [e for e in lev if not e.ok]
                self.row_state.emit(row_import, "error")
                self.log.emit(f"{kind} 导入失败：{bad[-1].detail if bad else '无输出'}")
                return False
            self.row_state.emit(row_import, "completed")
            self._advance(row_import)
            self.row_state.emit(row_arrange, "completed")
            self._advance(row_arrange)
            return True

        if not place("point", "build/ies/fixed/NPTLED351_NVC.IES",
                     "lum-point", "arrange-point"):
            self.done.emit(False, "筒灯布灯失败")
            return
        if self._stop:
            self.done.emit(False, "已停止（筒灯已放，线性灯没放）")
            return
        if not place("linear", "build/ies/linear/opple_LEDPanelRc-S-Re295-30W-4000-WH-U19.ies",
                     "lum-linear", "arrange-linear"):
            self.done.emit(False, "线性灯布灯失败")
            return

        self.progress.emit(100.0)
        self.done.emit(True, "全部完成：建壳 + 两批灯 + 存盘")


class Overlay(QtWidgets.QWidget):
    """半透明小挂件，贴在 DIALux 窗口右上角。"""

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint       # 无边框
            | QtCore.Qt.WindowStaysOnTopHint    # 压在 DIALux 上面
            | QtCore.Qt.Tool                    # 不进 Alt+Tab，等价于 WS_EX_TOOLWINDOW
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setFixedWidth(340)
        self._states = {k: "pending" for k, _, _ in ROWS}
        self._worker: Pipeline | None = None
        self._build_ui()

        # BGI 的 RefreshPositionForNormal 思路：定时把自己重新贴到目标 rect 上，
        # 这样 DIALux 被拖动或改大小时挂件跟着走。
        self._anchor = QtCore.QTimer(self)
        self._anchor.timeout.connect(self._reanchor)
        self._anchor.start(400)
        self._reanchor()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        title = QtWidgets.QLabel("dialux-compiler")
        title.setStyleSheet("color:#e5e7eb;font:600 13px 'Segoe UI';")
        root.addWidget(title)

        self._rows: dict = {}
        for key, text, _ in ROWS:
            line = QtWidgets.QHBoxLayout()
            line.setSpacing(8)
            glyph = QtWidgets.QLabel(STATE_GLYPH["pending"])
            glyph.setFixedWidth(20)
            glyph.setAlignment(QtCore.Qt.AlignCenter)
            label = QtWidgets.QLabel(text)
            line.addWidget(glyph)
            line.addWidget(label, 1)
            root.addLayout(line)
            self._rows[key] = (glyph, label)
        self._paint_rows()

        self._bar = QtWidgets.QProgressBar()
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(True)
        self._bar.setFixedHeight(16)
        self._bar.setStyleSheet(
            "QProgressBar{background:#1f2937;border:none;border-radius:8px;"
            "color:#e5e7eb;font:11px 'Segoe UI';}"
            "QProgressBar::chunk{background:#38bdf8;border-radius:8px;}")
        root.addWidget(self._bar)

        self._status = QtWidgets.QLabel("待命")
        self._status.setWordWrap(True)
        self._status.setStyleSheet("color:#9ca3af;font:11px 'Segoe UI';")
        root.addWidget(self._status)

        # 实时日志区（BetterGI LogTextBox 模式：执行时显示正在做什么）
        self._logbox = QtWidgets.QPlainTextEdit()
        self._logbox.setReadOnly(True)
        self._logbox.setMaximumBlockCount(200)
        self._logbox.setFixedHeight(96)
        self._logbox.setStyleSheet(
            "QPlainTextEdit{background:#0b1220;color:#9ca3af;border:none;"
            "border-radius:6px;font:10px 'Consolas';}")
        root.addWidget(self._logbox)

        # 「同时启动 DIALux」开关（同 BetterGI「同时启动原神」LinkedStart）
        self._link = QtWidgets.QCheckBox("同时启动 DIALux")
        self._link.setChecked(True)
        self._link.setStyleSheet("color:#9ca3af;font:11px 'Segoe UI';")
        root.addWidget(self._link)

        btns = QtWidgets.QHBoxLayout()
        self._start = QtWidgets.QPushButton("启动")
        self._stop = QtWidgets.QPushButton("停止")
        self._stop.setEnabled(False)
        for b in (self._start, self._stop):
            b.setFixedHeight(26)
            b.setStyleSheet(
                "QPushButton{background:#374151;color:#e5e7eb;border:none;"
                "border-radius:6px;font:12px 'Segoe UI';}"
                "QPushButton:hover{background:#4b5563;}"
                "QPushButton:disabled{color:#6b7280;}")
            btns.addWidget(b)
        root.addLayout(btns)
        self._start.clicked.connect(self._on_start)
        self._stop.clicked.connect(self._on_stop)

    def paintEvent(self, event):  # noqa: N802 - Qt 命名
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.setBrush(QtGui.QColor(17, 24, 39, 225))   # 半透明深底
        p.setPen(QtGui.QPen(QtGui.QColor(56, 189, 248, 120), 1))
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 10, 10)

    def _paint_rows(self):
        for key, _, _ in ROWS:
            st = self._states[key]
            glyph, label = self._rows[key]
            glyph.setText(STATE_GLYPH[st])
            glyph.setStyleSheet(f"color:{STATE_COLOR[st]};font:600 12px 'Consolas';")
            weight = "600" if st == "active" else "400"
            color = "#e5e7eb" if st in ("active", "completed") else "#9ca3af"
            label.setStyleSheet(f"color:{color};font:{weight} 12px 'Segoe UI';")

    def _reanchor(self):
        """贴到 DIALux 窗口右上角内侧。找不到 DIALux 就贴屏幕右上角。"""
        hwnd = find_dialux()
        ratio = self.devicePixelRatioF() or 1.0
        if hwnd:
            left, top, right, _bottom = win32gui.GetWindowRect(hwnd)
            # GetWindowRect 是物理像素，Qt setGeometry 要逻辑像素 —— 这一步就是
            # BGI 里除 DpiHelper.ScaleY 的等价物。
            x = int(right / ratio) - self.width() - 18
            y = int(top / ratio) + 56
            if right - left < 400:      # DIALux 被缩得太小，别贴出界
                x, y = None, None
        else:
            x = y = None
        if x is None:
            geo = QtGui.QGuiApplication.primaryScreen().availableGeometry()
            x, y = geo.right() - self.width() - 24, geo.top() + 24
        self.move(x, y)

    # ------------------------------------------------------------ 交互
    def _on_start(self):
        # 若勾了「同时启动 DIALux」，Pipeline 的 launch 步骤会自己开（BetterGI
        # LinkedStart 语义）；没勾则要求 DIALux 已开。
        if not self._link.isChecked():
            hwnd = find_dialux()
            if not hwnd:
                self._status.setText("没找到 DIALux 窗口，勾「同时启动」或先打开它")
                return
            # BGI 的交接动作：先把目标程序拉到前台，再由挂件在旁边跑。
            try:
                win32gui.ShowWindow(hwnd, 9)            # SW_RESTORE
                win32gui.SetForegroundWindow(hwnd)
            except Exception:  # noqa: BLE001 - 前台切换被系统拒绝不致命
                pass

        self._states = {k: "pending" for k, _, _ in ROWS}
        self._paint_rows()
        self._bar.setValue(0)
        self._logbox.clear()
        self._status.setText("正在跑……")
        self._start.setEnabled(False)
        self._stop.setEnabled(True)

        self._worker = Pipeline(self)
        self._worker.link_start = self._link.isChecked()
        self._worker.row_state.connect(self._on_row_state)
        self._worker.progress.connect(lambda v: self._bar.setValue(int(v)))
        self._worker.log.connect(self._on_log)
        self._worker.done.connect(self._on_done)
        self._worker.start()

    def _on_log(self, line: str):
        """实时日志：状态行显示最新一条，日志区滚动保留历史。"""
        self._status.setText(line)
        self._logbox.appendPlainText(line)
        sb = self._logbox.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_stop(self):
        if self._worker:
            self._worker.request_stop()
        self._stop.setEnabled(False)
        self._status.setText("正在停……")

    def _on_row_state(self, key: str, state: str):
        self._states[key] = state
        self._paint_rows()

    def _on_done(self, ok: bool, msg: str):
        self._status.setText(("完成：" if ok else "未完成：") + msg)
        self._start.setEnabled(True)
        self._stop.setEnabled(False)


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    w = Overlay()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
