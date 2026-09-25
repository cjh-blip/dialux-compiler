# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: launcher.exe (dialux-compiler GUI 启动器，windowed）。
# 用法: python -m PyInstaller scripts/launcher.spec --noconfirm
#
# 打包 GUI（windowed）：双击打开启动器窗口，不弹黑框。
# 同 demo_run.spec：ROOT 用 SPECPATH 自动探测（spec 在 scripts/ 下，parent=仓库根）。

from pathlib import Path
SPEC_DIR = Path(SPECPATH)
ROOT = str(SPEC_DIR.parent)

block_cipher = None

datas = [
    (f"{ROOT}/src/executor/uia/dialux_driver.ps1", "src/executor/uia"),
    (f"{ROOT}/src/executor/uia/autosave.ps1", "src/executor/uia"),
    (f"{ROOT}/src/executor/uia/luminaire.ps1", "src/executor/uia"),
    (f"{ROOT}/spec/ir.schema.json", "spec"),
]

a = Analysis(
    [f"{ROOT}/src/ui/launcher.py"],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "src.ui.launcher",
        "src.executor.uia.driver",
        "src.executor.uia.luminaire",
        "src.executor.uia.driver_plan",
        "src.core.env",
        # 工作台骨架 + DIALux 任务（launcher 动态 import，需显式收集）
        "src.workbench.task",
        "src.workbench.trigger",
        "src.workbench.flow",
        "src.workbench.config",
        "src.workbench.dispatcher",
        "src.tasks.dialux",
        "src.tasks.dialux.room_task",
        "src.tasks.dialux.luminaires_task",
        "src.tasks.dialux.report_task",
        "src.tasks.dialux.autosave_trigger",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "matplotlib"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="launcher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,          # windowed：双击出窗口，无黑框
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="launcher",
)
