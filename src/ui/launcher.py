"""dialux-compiler GUI 启动器（PySide6）。

交互参考 BetterGI 的 HomePage（抄交互模式，不抄代码）：
- 一个「启动」大按钮 + 「同时启动 DIALux」开关（LinkedStart：目标程序未开则自动开）；
- 配置区（图纸路径 / 灯具文件，带浏览选择）；
- 实时日志区（跑 demo_run 全链路：解析 → STF 建壳 → 导入灯具 → 排布 → 存盘）。

用法::

    python -m src.ui.launcher

打包（windowed，双击出窗口）::

    python -m PyInstaller scripts/launcher.spec --noconfirm
"""
from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

# 必须在 QApplication 之前声明 per-monitor DPI 感知（同 overlay.py）
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:  # noqa: BLE001 - 老系统无此 API
    pass

import win32gui  # noqa: E402
from PySide6 import QtCore, QtWidgets  # noqa: E402

# ---------------------------------------------------------------- 进程工具

def _dialux_exe() -> Path:
    """DIALux 启动器路径，统一走 src.core.env（override > env > 默认）。"""
    from src.core.env import get_dialux_path
    return get_dialux_path()


def _exe_dir() -> Path:
    """打包后 exe 所在目录；源码版是仓库根。运行时确定（参考 Mrite，不硬编码）。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return REPO


def _default_file(name: str) -> str:
    """优先 exe 旁/仓库根的常见文件，找不到返回空（让用户浏览选）。"""
    cand = _exe_dir() / name
    return str(cand) if cand.exists() else ""


def dialux_hwnd() -> int:
    """返回 DIALux 主窗口 hwnd，没有返回 0（认 HwndWrapper 类名 + 标题）。"""
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


def launch_dialux(timeout_s: float = 90.0) -> bool:
    """启动 DIALux.exe 并等待主窗口出现；返回是否成功。"""
    if dialux_hwnd():
        return True
    try:
        subprocess.Popen([str(_dialux_exe())], cwd=str(REPO))
    except (OSError, RuntimeError) as exc:
        logging.error("启动 DIALux 失败：%s", exc)
        return False
    import time
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if dialux_hwnd():
            return True
        time.sleep(2)
    return False


# ---------------------------------------------------------------- 工作线程

class Runner(QtCore.QThread):
    """后台跑完整流程，逐行发日志与进度。"""

    log = QtCore.Signal(str)
    done = QtCore.Signal(bool, str)
    progress = QtCore.Signal(float)

    def __init__(self, dwg: str, dwg_lighting: str, config: str,
                 ies: str | None, furniture_probe: bool,
                 link_start: bool, parent=None):
        super().__init__(parent)
        self._dwg, self._dwg_lighting, self._config = dwg, dwg_lighting, config
        self._ies = ies
        self._furniture_probe = furniture_probe
        self._link_start = link_start
        self._stop = False

    def request_stop(self):
        self._stop = True

    def run(self):
        import logging as _l
        _l.basicConfig(level=_l.INFO, format="%(message)s")
        self.log.emit("──── dialux-compiler 启动器 ────")

        # 1) 可选：自动打开 DIALux（LinkedStart，参考 BetterGI「同时启动原神」）
        if self._link_start:
            self.log.emit("检查 DIALux…")
            if not dialux_hwnd():
                self.log.emit("DIALux 未运行，自动启动…")
                if not launch_dialux():
                    self.done.emit(False, "启动 DIALux 失败，请手动打开后重试")
                    return
                self.log.emit("DIALux 已启动")
            else:
                self.log.emit("DIALux 已在运行")

        # 2) 一条龙 Flow（workbench）：建壳 → 家具探针（可选）→ 布灯 → 报告
        from src.tasks.dialux import FurnitureTask, LuminairesTask, ReportTask, RoomTask
        from src.workbench.flow import Flow
        from src.workbench.task import TaskContext

        cfg = {
            "dwg": self._dwg,
            "dwg_lighting": self._dwg_lighting,
            "parse_config": self._config,
        }
        flow = Flow("一键建案")
        flow.add(RoomTask(), params=cfg, title="自动房间布置", weight=2.0)
        if self._furniture_probe:
            flow.add(FurnitureTask(ir_path="build/demo_ir.json", limit=1),
                     title="家具单件探针", weight=1.0)
        if self._ies:
            flow.add(LuminairesTask(),
                     params={} if self._ies == "auto" else {},
                     title="自动布灯", weight=2.0)
        flow.add(ReportTask(), title="自动报告", weight=1.0)

        total = len(flow.steps)
        ctx = TaskContext(
            config=cfg,
            log=lambda m: self.log.emit(str(m)[:200]),
            cancel_check=lambda: self._stop,
        )

        def on_step(idx, step, result):
            self.progress.emit(min(100.0, (idx + 1) / total * 100.0))

        results = flow.run(ctx, on_step=on_step)
        ok = bool(results) and all(r.ok for r in results)
        if self._stop:
            self.done.emit(False, "已停止")
            return
        self.done.emit(ok, "一条龙完成" if ok else
                       f"失败：{results[-1].detail if results else '无步骤'}")


# ---------------------------------------------------------------- 窗口

class Launcher(QtWidgets.QWidget):
    """启动器主窗口：启动按钮 + 同时启动开关 + 配置 + 日志。"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("dialux-compiler 启动器")
        self.resize(560, 520)
        self._runner: Runner | None = None
        self._build_ui()

    def _build_ui(self):
        root = QtWidgets.QVBoxLayout(self)
        root.setContentsMargins(16, 14, 16, 14)
        root.setSpacing(10)

        title = QtWidgets.QLabel("dialux-compiler")
        title.setStyleSheet("font:700 16px 'Segoe UI';color:#e5e7eb;")
        root.addWidget(title)

        # ---- 启动卡片（参考 BetterGI HomePage）----
        card = QtWidgets.QGroupBox("启动")
        card.setStyleSheet(_GROUP_BOX_QSS)
        cl = QtWidgets.QVBoxLayout(card)
        cl.setSpacing(8)

        row1 = QtWidgets.QHBoxLayout()
        self._start_btn = QtWidgets.QPushButton("启动")
        self._start_btn.setStyleSheet(_BTN_QSS)
        self._start_btn.setMinimumHeight(44)
        self._start_btn.clicked.connect(self._on_start)
        self._link_switch = QtWidgets.QCheckBox("同时启动 DIALux（未运行则自动打开）")
        self._link_switch.setChecked(True)
        self._link_switch.setStyleSheet("color:#d1d5db;")
        self._furniture_switch = QtWidgets.QCheckBox("家具单件探针（实验）")
        self._furniture_switch.setChecked(False)
        self._furniture_switch.setStyleSheet("color:#d1d5db;")
        row1.addWidget(self._start_btn, 1)
        row1.addWidget(self._link_switch)
        row1.addWidget(self._furniture_switch)
        cl.addLayout(row1)
        root.addWidget(card)

        # ---- 配置区 ----
        cfg = QtWidgets.QGroupBox("配置")
        cfg.setStyleSheet(_GROUP_BOX_QSS)
        cfl = QtWidgets.QVBoxLayout(cfg)
        cfl.setSpacing(6)

        self._dwg_edit = self._path_row(cfl, "房间图 DWG/DXF：",
                                        _default_file("布局图.dwg"))
        self._lighting_edit = self._path_row(cfl, "灯具图 DWG/DXF：",
                                             _default_file("灯具图.dwg"))
        self._config_edit = self._path_row(
            cfl, "ParseConfig：",
            _default_file("sample_parse_config.json"))
        self._ies_combo = QtWidgets.QComboBox()
        self._ies_combo.addItem("auto（默认两件套：NPTLED 筒灯 + Re295 线性灯）", "auto")
        self._ies_combo.addItem("不布灯（只建房间壳）", "")
        # 运行时探测 exe 旁的 build/ies（参考 Mrite：路径运行时确定，不写死）
        nptled = _default_file("build/ies/fixed/NPTLED351_NVC.IES")
        if nptled:
            self._ies_combo.addItem("NPTLED351 筒灯", nptled)
        re295 = _default_file("build/ies/linear/opple_LEDPanelRc-S-Re295-30W-4000-WH-U19.ies")
        if re295:
            self._ies_combo.addItem("OPPLE Re295 线性灯", re295)
        ies_lbl = QtWidgets.QLabel("灯具型号：")
        ies_lbl.setStyleSheet("color:#9ca3af;")
        ies_row = QtWidgets.QHBoxLayout()
        ies_row.addWidget(ies_lbl)
        ies_row.addWidget(self._ies_combo, 1)
        cfl.addLayout(ies_row)
        root.addWidget(cfg)

        # ---- 日志区 ----
        log_lbl = QtWidgets.QLabel("运行日志：")
        log_lbl.setStyleSheet("color:#9ca3af;")
        root.addWidget(log_lbl)
        self._log = QtWidgets.QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(300)
        self._log.setStyleSheet(
            "QPlainTextEdit{background:#111827;color:#d1d5db;border:none;"
            "border-radius:6px;font:11px 'Consolas';}")
        root.addWidget(self._log, 1)

        self._status = QtWidgets.QLabel("待命")
        self._status.setStyleSheet("color:#9ca3af;font:11px 'Segoe UI';")
        root.addWidget(self._status)

    def _path_row(self, layout, label: str, default: str) -> QtWidgets.QLineEdit:
        row = QtWidgets.QHBoxLayout()
        lbl = QtWidgets.QLabel(label)
        lbl.setStyleSheet("color:#9ca3af;")
        edit = QtWidgets.QLineEdit(default)
        edit.setStyleSheet("QLineEdit{background:#1f2937;color:#e5e7eb;border:none;"
                           "border-radius:4px;padding:4px 8px;}")
        browse = QtWidgets.QPushButton("浏览…")
        browse.setStyleSheet(_BTN_QSS)
        browse.setMaximumWidth(64)
        browse.clicked.connect(lambda: self._browse(edit))
        row.addWidget(lbl)
        row.addWidget(edit, 1)
        row.addWidget(browse)
        layout.addLayout(row)
        return edit

    def _browse(self, edit: QtWidgets.QLineEdit):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "选择文件")
        if path:
            edit.setText(path)

    # ------------------------------------------------------------ 交互
    def _on_start(self):
        if self._runner is not None and self._runner.isRunning():
            self._runner.request_stop()
            self._status.setText("正在停止…")
            return
        dwg = self._dwg_edit.text().strip()
        if not dwg:
            self._status.setText("请先选房间图")
            return
        self._log.clear()
        self._start_btn.setText("停止")
        self._status.setText("正在跑…")
        self._runner = Runner(
            dwg=dwg,
            dwg_lighting=self._lighting_edit.text().strip() or dwg,
            config=self._config_edit.text().strip(),
            ies=self._ies_combo.currentData(),
            furniture_probe=self._furniture_switch.isChecked(),
            link_start=self._link_switch.isChecked(),
        )
        self._runner.log.connect(self._log.appendPlainText)
        self._runner.done.connect(self._on_done)
        self._runner.start()

    def _on_done(self, ok: bool, msg: str):
        self._start_btn.setText("启动")
        self._status.setText(("完成：" if ok else "未完成：") + msg)


# ---------------------------------------------------------------- 样式

_GROUP_BOX_QSS = """
QGroupBox{color:#e5e7eb;font:600 13px 'Segoe UI';border:1px solid #374151;
          border-radius:8px;margin-top:10px;padding-top:8px;}
QGroupBox::title{subcontrol-origin:margin;left:12px;padding:0 4px;}
"""

_BTN_QSS = """
QPushButton{background:#2563eb;color:#fff;border:none;border-radius:6px;
            font:600 13px 'Segoe UI';padding:6px 14px;}
QPushButton:hover{background:#1d4ed8;}
QPushButton:disabled{background:#374151;color:#6b7280;}
"""


def main() -> int:
    app = QtWidgets.QApplication(sys.argv)
    w = Launcher()
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
