# MVP3 演示计划：悬浮小部件驱动 DIALux

> 定案时间：2026-09-05 深夜 | 六步链第 ④ 步产物 | 执行层遵循 karpathy-guidelines
> 交付时限：**次日可写进周报**

## 执行结果（2026-09-06）

**P0 保底、P1 进度契约、P2 悬浮壳全部完成并真机验收；P3 家具占位未做。**
验收数字、证据链、踩坑记录一律只记在 `KANBAN.md`「MVP3 演示交付」一条里，
本文件不复述——按仓库约定，KANBAN 是唯一现役状态板。

计划里判断错的一处，留在这里当教训：原计划假设文件对话框也能走 UIA
（`ValuePattern` 填文件名 + `InvokePattern` 点打开）。**实测这条路完全不通**，
对话框在 UIA 里是一堆没有任何 pattern 的 `Pane`，最终改成菜单走 UIA、
对话框走 Win32 窗口消息。写计划时我把「上一轮验证过导入链」错记成「验证过
UIA 能操作对话框」，实际上上一轮验的是菜单那一段。

## 一、已定案的决策（第②步 grill 结论）

| 编号 | 问题 | 定案 |
|---|---|---|
| Q1 | 周报要什么形态的结果 | **录屏**，且录带界面的那一版 |
| Q2 | 明天赌多大 | **进阶档**（建壳 + 家具占位），但**先锁保底** |
| Q3 | Pro 试用期要不要处理 | **不管**，只在 KANBAN 记一笔 |
| 附1 | UIA 驱动换 Python 原生？ | **不换**。PowerShell 链是唯一真机验证过的路，`comtypes` 未装，此时动它是找死 |
| 附2 | 悬浮窗要不要点击穿透？ | **不穿透**。我们走 UIA 不需要焦点，留一个能点的「停止」更有用 |

### 抄用边界（许可证）

- **Mrite = MIT** → 可以抄代码，注明出处。
- **BGI = GPL-3.0** → **只抄方案，不抄代码**。抄源码会让本项目被迫 GPL-3.0。
  Win32 flag 的组合与调用顺序属微软公开 API，不是 BGI 的创作，可自由使用。

### 关键环境事实（已实核，不是假设）

- `PySide6 6.9.2 / Qt 6.9.2`、`PyQt5`、`pywin32`、`flask`、`fastapi`、`tkinter` **均已安装**
  → 原生桌面壳**零新依赖**。
- `WS_EX_LAYERED=0x80000`、`WS_EX_TRANSPARENT=0x20`、`WS_EX_TOOLWINDOW=0x80` 在 `win32con` 里都有。
- `comtypes` / `uiautomation` / `pywinauto` **未装** → 不走 Python 原生 UIA。
- DIALux evo 5.14.0.5 正在运行（`DIALux.exe` PID 19220 / `DIALux_x64.exe` PID 12740）。
- Pro 试用 9 项功能 2026-09-08 到期（`Licenses.dat` 明文）：`DxIfcImport/Export`、
  `DxImportLuminaire`、`DxPrintExport{Csv,Word,Excel,PowerPoint}`、`DxPrintTemplate{Select,Import}`。
  **STF 导入、建模、存 .evo 都不在名单里**，到期不影响主路径。

## 二、执行顺序与验收标准

严格按 P0 → P1 → P2 → P3。**P0 未锁死不许动 P2。**

### P0 保底：一条命令从 DWG 跑到 DIALux 里的房间

- 新增 `src/executor/uia/dialux_driver.ps1`（**ASCII-only**，CJK 会让 PowerShell 5.1 按 GBK 解析而报
  `ParserError`）：挂到运行中的 DIALux → `File → Import → ImportStf` → 文件对话框选文件 →
  `Open`(AutomationId=`1`) → 主工具栏 `Save`。每步向 stdout 打一行 `STEP <name> <ok|fail>`。
- 新增 `src/executor/uia/driver.py`：`subprocess` 调上面的脚本，逐行解析 `STEP`，把进度回调出去。
- 新增 `scripts/demo_run.py`：串起 DWG → IR → STF → 驱动 DIALux → `.evo`。

**验收**：跑完得到 `.evo`；用 ZIP 拆包确认
`Project/STF/*.tmp` 与本地 STF **字节一致**，且房间顶点坐标在 `Project/ScenegraphScene` 里
以 float64 米命中（沿用已验证的 `struct.pack("<d", v)` 扫描法，必须带房间顶点作对照组）。

### P1 进度契约

`build_action_plan` 现有 55 条动作已带 `id`（`a0001` 格式）与 `type`，缺的是显示名和权重。
只加两个字段，不动别的：

- `title` — 中文显示名，给步骤列表用。
- `weight` — 预估耗时权重。等权重会让进度条很跳（一次 UIA 点击约 0.3 s，
  一次 STF 导入约 3 s，一次 DIALux 保存约 2 s）。

现有类型分布（真实图纸）：`place_luminaire`×28、`create_space`×23、
`create_project`/`create_storey`/`run_calculation`/`export_report` 各 ×1。

**验收**：pytest 新增用例断言每条动作都有非空 `title` 与正数 `weight`；
权重求和 > 0；`--format plan` 输出里可见新字段。

### P2 悬浮小部件（PySide6）

新增 `src/ui/overlay.py`：

- 无边框 + `WA_TranslucentBackground` + `WindowStaysOnTopHint` + `Tool`（不进 Alt+Tab）。
- 用 `win32gui.GetWindowRect(DIALux hwnd)` 读目标窗口 rect，把自己贴到右上角，定时跟随。
- 步骤列表（抄 Mrite `panels/progress.js` 的 `pending/active/completed/error` 四态）+ 真进度条。
- 一个「停止」按钮。

**验收**：能启动、贴住 DIALux、跑 P0 流程时步骤逐条亮起、进度条走到 100%、录屏可见。

### P3 有余力才做：家具长方体占位

用已摸到的 `CuboidWidth`/`CuboidLength`/`CuboidHeight`（可写 Edit）+ `aid_DrawRectangle`，
尺寸取 IR 的家具 bbox。**验收同 P0 的 ZIP 拆包法。**

## 三、风险与降级

| 风险 | 降级动作 |
|---|---|
| P2 做不完 | 周报用 P0 的 CLI 录屏。**P0 录完先存一份，不要等 P2** |
| DIALux 弹未知模态框 | 驱动脚本每步前枚举子 `Window`，遇未知标题就停下并截图 |
| 停止按钮语义未定 | 本轮只做「停在当前步并如实显示 17/55」，检查点/回滚推到 MVP3 之后 |

## 四、遗留（不在本轮）

- 停止后半装修状态的检查点/回滚策略。
- `mount` 仍全靠默认 `recessed`，真实项目需从灯具表或图层名推断。
- `DxImportLuminaire` 到期后的 GLDF 替代路径（DIALux 自带 `Gldf.Net.dll`）。
