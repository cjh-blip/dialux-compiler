# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: demo_run.exe (dialux-compiler CLI).
# Usage:
#   python -m PyInstaller scripts/demo_run.spec --noconfirm
#
# Bundles: python code + 3 driver .ps1 (as datas into _MEIPASS), no external
# drawings (user passes --dwg/--dwg-lighting at runtime).

from pathlib import Path
# 仓库根：spec 在 scripts/ 下，SPECPATH = spec 所在目录（scripts/），.parent = 仓库根。
# 参考 Mrite 的「运行时确定工作区」——构建时也自动探测，换目录/换机无需改。
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
    [f"{ROOT}/scripts/demo_run.py"],
    pathex=[ROOT],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "src.executor.uia.driver",
        "src.executor.uia.luminaire",
        "src.executor.uia.driver_plan",
        "src.executor.kernel",
        "src.core.env",
        "src.exporter.stf",
        "src.planner.core",
        "src.planner.join",
        "src.planner.mount",
        "src.parser.dxf",
        "src.validator",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PySide6", "PyQt5", "PyQt6", "matplotlib", "pytest", "pandas", "openpyxl"],
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
    name="demo_run",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
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
    name="demo_run",
)
