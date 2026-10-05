# KANBAN — dialux-compiler

> 协作中枢 + 审核入口。状态：`待办 / 进行中 / 待验收 / 完成 / 阻塞`
> 约定：`done` 必须挂「审查意见」（谁审、结论、遗留），否则不算完成。
> 本文件是唯一现役状态板：门禁数字、几何口径、实现边界、遗留项的权威解释都在这里，
> `AGENTS.md` 与 `README.md` 只放指针，不复述数字。
> 上游（现役）：`D:\homework\plans\20260902_dialux-compiler_MVP2投产_计划.md`（Q15-Q20 定案 + S0-S4）
> 上游（历史）：`D:\homework\plans\20260831_dialux-compiler_MVP1收尾_计划.md`（grill 6 条定案 + S1-S4）
> 角色库：`~/.claude/agents/`（目录即真身，数量不在文档里写死）；
> 选型说明见 `D:\homework\plan\03_Resources\prompts\强AI工作流-角色库-v2.md`（v1 废弃）

## 门禁实测

2026-10-05 复核（开源脱敏后），Python 3.11 + 本仓依赖。这里是全仓唯一权威数字。

| 门禁 | 命令 | 结果 |
|---|---|---|
| 测试 | `python -m pytest tests/ -q` | **干净 clone：246 passed / 3 skipped，退出码 0**（3 项 skip 为缺 build/ 运行产物的环境性跳过） |
| lint | `python -m ruff check .` | **0 errors（All checks passed）**，退出码 0，ruff **0.15.1** |

- pytest 9.0.2，configfile `pytest.ini`（testpaths=tests、addopts=-ra、pythonpath=.）；
  249 = 收集总数（干净 clone：246 passed + 3 skipped；2026-10-05 复核）。
  历史门禁数字：237 = 198 个 `def test_` + parametrize 展开（2026-09-08，含家具 IR/Task 测试）。
  历史门禁数字（2026-09-06）：221 = 182 个 `def test_` + parametrize 展开；当日新增
  `tests/test_executor_kernel.py` 9 条（P2 execute_plan 派发/重试/HALT/进度）、
  `tests/test_driver_plan.py` 7 条（UiaDriver STF 批量 + place_luminaire stub）、
  `tests/test_progress_contract.py` 扩展 5 条（保存弹窗自动应答）+ 计划驱动进度 1 条。
- **lint 已归零**：2026-09-04 集中治理（E702×43 / F401×15 / E741×9 / F541×6 / F841×4 /
  E701×2 / E731×2 = 81 条全清，集中在 `src/parser/_chain.py`、`scripts/render_preview_svg.py`、
  `src/parser/dxf.py`），**未放宽任何 ruff 配置**。历史数字 81 只在
  「2026-09-04 git-project-analyzer 分析改进」章节作为过程记录保留。
- **0 比 81 更稳，绑定条件也变了**：`--no-respect-gitignore` 现在只有 **8 条，且全部来自
  `better-genshin-impact/` 参考项目**（F401×4 + F541×4，都在它的 `.github/workflows/*.py`），
  **本仓自有代码在两种口径下都是 0**。旧记录里的「225 条」已失效（当时 `build/` 内有大量
  `debug_*.py`，现已 0 个）。
- 漂移风险（2026-10-05 修正）：`requirements.txt` **已锁** `ruff==0.15.1`；ezdxf / pandas / openpyxl / jsonschema 仍为 `>=` 浮动，升级可能引起回归。
- 仓库、`D:\dev`、`D:\`、用户级均无任何 ruff 配置文件（无 pyproject.toml / ruff.toml），
  走的是 ruff 默认规则集 E4/E7/E9+F。
- 2026-09-03 的 `.gitignore` 调整**没有改动生效忽略面**：交付口径是「删除 4 条冗余规则行
  （`build/_cache/`、`build/_dxf_out/`、`build/_dwg_in/`、`.trae/history/`）+ 调整注释」，
  `git check-ignore -v` 实测被删的四条仍分别命中 `build/` 与 `.trae/` 两条现存规则，忽略面等价。

## 现役几何口径

`build/room_layout.json` 主房间（样例图纸）：**顶点数按首尾闭合去重**，
鞋带法 signed_area 为**正值即 CCW**。全仓统一用这一种表述，其余位置只放指针。

- 同批产物：`build/mvp2_fixed.stf` NrPoints=17。修复前快照 `build/room_layout_before_fix.json`
  主房间 `LINEARC_020_E53_355C` = 54 个点（53 个唯一顶点）/ signed_area **-93.628 m²（CW）**，
  对应 `build/mvp2_out.stf` NrPoints=54 —— 这就是 MVP2 绕向从 CW 变 CCW 的出处。
- 同一 IR 共 23 个 space：1 个真房间 + 22 个家具伪 space（`name` 以 `家具_` 开头），
  只有 1 个 space 带 `ceil_h`。
- 解析器已在主房间上挂出 28 盏灯，28 个 `catalog_match=true` / 0 个 false。
  **权威产物是 `build/mvp3_ir.json`（2026-09-05 复跑，房间图 + 灯具图两张图）**：每盏灯带
  `symbol`/`x`/`y`/`z`/`catalog_match`/`kind`/`dims`/`mount`，`kind` = 16 `point` + 12 `linear`，
  `z` 全 = 2.8（挂载高度已回填），`dims` 收敛成 `{radius_mm:76.0}`×16 与
  `{w_mm:1555.0,h_mm:300.0}`×12，`_meta.luminaires=28`。
- 旧产物 `build/room_layout.json` 与 `build/room_layout_before_fix.json`（均 2026-09-02，
  来源 `build/_cache/dwg_converted/布局图.dxf`）**已过期，勿再引用数字**：无 `kind`/`dims`，
  `z` 全 0，`_meta.luminaires` 写 0（回填逻辑 09-04 才加），`radius_mm` 还是未换算的 7.6。
  它们只在「MVP2 绕向修复前后对照」这一处仍有史料价值。
- `build/` 全量进 `.gitignore`：本文件引为验收证据的 `room_layout.json` / `room_layout.svg` /
  `mvp2_*.stf` / `mvp2_code_review_round1|2.md` 都不入库，重跑或清 `build/` 即消失。

## 现役实现边界

2026-09-05 代码实核（覆盖 09-03 快照）。跑通的是「DXF → IR → STF 房间几何 → evo 真机建房间」。

1. **executor 仍是空转 stub**（唯一未消除的一条）：`src/executor/key_mouse.py:88-91`
   的 `KeyMouseExecutor._locate_control` 恒 `return None`（注释仍写「TODO: 接入
   OpenCV/PaddleOCR」），`_click`（:136-139）随即抛 RuntimeError；`ProgramExecutor._do`
   （:78-79）对除 `human_confirm` 外的动作一律 `return "OK"`；`src/main.py:143-145` 的
   `--execute` 只挂 `ProgramExecutor`。
   连带一条**看着能跑、实际空转的假布灯路径**：`src/planner/core.py:143-160` 会产出
   `place_luminaire` 动作，`key_mouse.py:109-116` 有对应分支，但因控件定位恒返 None 而永远失败。
   → **真动作现在走「computer use 通道」**（UIA `AutomationId` + `InvokePattern`，已在 evo 真机
   跑通全链路）。`_locate_control` 的正确实现方向已由此确定：走 UIA 语义，不走 OCR/图像锚点。
2. **STF 灯具段已开，家具段仍关**：`src/exporter/stf.py` 现在写
   `NrStruct=0 / NrLums={实际盏数} / NrFurns=0`，`NrLums` 按 `space["luminaires"]` 实取
   （2026-09-04 改）。**2026-09-05 + 2026-09-06 双重真机判定：DIALux evo 14.0 忽略该段，
   0 个灯具落地**——旧格式（`Lum{i}=x y z symbol`）与修正后的正确格式（对照 Revit
   STF-Exporter 的 `LumN=name`+`LumN.Pos=X Y Z`+`LumN.Rot=0 0 0`，2026-09-06 已改）
   都试过，导入执行了但 `LuminaireElement=0`。官方文档：STF 支持灯具位置但 evo 的
   STF export 标注 "in preparation" → **evo STF 导入很可能只实现房间几何**。
   → **STF 的实际职责只有房间几何**；`NrStruct` / `NrFurns` 恒 0 不变；
   `_luminaire_lines` 保留正确格式（供老 DIALux / 未来 evo 版本）。
   本仓不写 `.dlx`/`.evo`；`.evo` 由 DIALux 自己另存（2026-09-05 实测产出
   `build/mvp2_fixed.evo` 69112 B 与 `build/mvp3_lums.evo` 69378 B）。
3. **`--dwg` 单参不再崩**（2026-09-04 修）：`src/main.py:82-85` 的 else 分支改为
   `lum_dwg_path = dwg_path`（复用上游已转换的 DXF），与 `--dwg-lighting` help 文本
   「缺省从同一张图抽灯具」一致。修前是直接 `ezdxf.readfile` 读 `.dwg` 抛
   `OSError: not a DXF file`。

> 历史对照：09-03 快照曾把第 2 条记为「灯具永远进不了 STF」、第 3 条记为「待复现崩溃」。
> 两条均已在 09-04 消除，上面是现役答案，不要再引用旧断言。

## computer use 通道（2026-09-05 新增，evo 真机可驱动）

MVP2 验收是用这条通道跑完的，不是人眼在工位点的。**这是 MVP3.5 executor 的现成参考实现**——
`KeyMouseExecutor._locate_control` 需要的「按名字找控件并点」在 DIALux 上已被证明可行。

| 环节 | 事实 |
|---|---|
| DIALux 安装位置 | 以本机为准（默认 `C:\Program Files\DIAL GmbH\DIALux\DIALux.exe`，可用 `DIALUX_PATH` 覆盖）；启动后 launcher PID 的 `MainWindowHandle=0`，真 UI 在子进程 `DIALux_x64` |
| UIA 可读性 | 主窗口 `ClassName=Window` / `AutomationId=MainWindow`；开始页 157 个后代，载入工程后 271 个。菜单、按钮、文件对话框全部有稳定 `AutomationId` |
| 关键 AutomationId | 菜单 `File` → `Import` → `ImportStf` / `ImportDrawing` / `ImportIfc` / `ImportDlx4` / `ImportLuminaire` / `ImportFurniture`；按钮 `Save` / `Undo` / `Redo`；模式菜单 `MenuGotoConstructionMode`（展开后有 14 个 `MenuItem` 可 `Invoke`：`MenuGotoShowLuminaireArrangementTool` / `MenuGotoShowLuminaireCatalogPopup` / `MenuGotoShowFurnitureTool` / `MenuGotoShowCalculationObjectTool` 等） |
| 驱动方式 | `ExpandCollapsePattern.Expand()` 展菜单 → `InvokePattern.Invoke()` 点菜单项 → 文件对话框里 `SelectionItemPattern.Select()` + `InvokePattern.Invoke()` 双击 ListItem。**全程零像素坐标** |
| 状态判据 | `Save` 按钮 `IsEnabled` 从 False 变 True = 工程已载入；窗口标题带完整工程路径 = 导入成功 |
| 屏幕文字 | 装了 `dsh-computer-use-win` v0.1.2（22 工具，PowerShell UIA 后端 + Windows.Media.Ocr）。可绕过 MCP 直接调后端：`powershell -File <插件>/scripts/windows-uia.ps1 -Action ocr`，JSON 走 stdin（`{"nativeWindowHandle":<hwnd>}`） |
| 视觉现状 | 本会话主模型 `deepseek-v4-flash` **无 image 输入**，`settings.yaml` 里三个 provider 的模型全是 `input: [text]`；`describe_image` 插件报 `baseURL must be an absolute http(s) URL`。**所以屏幕判读靠 OCR + UIA 文本，不靠视觉模型** |

**踩过的坑（复用时直接避开）**：

1. PowerShell 中文字符串在 bash heredoc 里会乱码 → 中文匹配一律走 `AutomationId`，
   要打印中文就转 UTF-16 码点（`'{0:X4}' -f [int]$_`）。
2. 文件对话框是主窗口的**后代**，不是独立顶层窗口 —— 按 `Name` 找顶层窗口会找不到，
   必须在主窗口的 `TreeScope::Descendants` 里搜。
3. `New-Object <Type>(...)` 跨行 + 嵌套 `[Type]::Prop` 会被 PS 5.1 解析器判成语法错误；
   `.ps1` 文件用 write 工具写，别用 bash heredoc。
4. OCR 前必须 `activate_window`：窗口最小化时 `imageBounds` 会返回 `x=-31993,y=-32000`
   的哨兵坐标，OCR 结果为空。

### 家具库 / 灯具库实核（2026-09-05，回答「拼积木」与「选型」两问）

**试用期澄清（2026-09-05 更正，我之前把它说重了）**：OCR 读到的「试用期还剩 3 天」
**不是**所有真机验证的死线。查 `%LOCALAPPDATA%\DIAL GmbH\DIALux\Licenses.dat`
（14438 B，明文 ASCII）——到期的只有 **9 项 Pro 附加功能**，全部 2026-09-08 到期：
`DxIfcImport`、`DxIfcExport`、`DxImportLuminaire`、`DxPrintExportCsv`、
`DxPrintExportWord`、`DxPrintExportExcel`、`DxPrintExportPowerPoint`、
`DxPrintTemplateSelect`、`DxPrintTemplateImport`。
**STF 导入、基础建模、另存 `.evo` 都不在名单里，到期后主路径照跑。**
和我们真正相关的只有 `DxImportLuminaire`（导入自有灯具文件）；替代口子是
DIALux 自带的 `Gldf.Net.dll`（GLDF 开放标准），大概率不受这条许可门控——未验。

**家具库 = 磁盘静态资源，可离线建索引**（`D:\dev\DIAL GmbH\DIALux\Media\Furnitures\M3D\`，76 MB）：

| 分类 | 个数 | 分类 | 个数 |
|---|---|---|---|
| Moebel（家具） | **159** | Gebaeude（建筑） | 78 |
| Shop | 101 | Verkehrseinrichtungen（交通设施） | 64 |
| Personen（人物） | 28 | Regale/Schraenke 见下 | — |
| Stadtmobiliar | 17 | Buerozubehoer（办公配件） | 13 |
| Sanitaer（卫浴） | 12 | Fahrzeuge（车辆） | 8 |
| Baeume/Treppen | 各 5 | Pflanzen/Sportstaetten | 3 / 1 |

共 **494 个 `.m3d`**。Moebel 下 8 个子类：Tische(67) / Designklassiker(23) / Regale(18) /
Schraenke(17) / Polstermoebel(11) / Stuehle(11) / Werkbaenke(7) / Betten(5)。

**关键：文件名直接编码尺寸**（cm），可纯规则匹配 IR 家具 bbox：
`Tische/200x100_Konferenz` / `160x80_standard` / `Schraenke/110x200_2Tueren` / `Regale/110x120_Bueroregal`。
- `.m3d` 容器是 OLE2/CFBF（magic `d0cf11e0a1b11ae1`），**内部未解**（本机无 olefile）
  → 现在只有文件名尺寸，真实 bbox 未校验。
- 结论：**家具选型不需要联网、不需要 UI 浏览**，可以在 planner 里查表决策。

**家具「拼积木」通道已找到**（构造模式 → `FurnitureTool` TabItem，`SelectionItemPattern.Select()`）：

| AutomationId | 作用 | 对我们的意义 |
|---|---|---|
| `CuboidWidth` / `CuboidLength` / `CuboidHeight` | 三个**可写 Edit** | `ValuePattern.SetValue()` 直接灌 IR bbox → 最朴素可靠的占位积木 |
| `aid_DrawRectangle` / `DrawPolygon` / `DrawCircle` / `DrawLine` / `DrawPoint` | 画放置轮廓 | 定位 |
| `aid_DrawExtrusionFurniture` | 拉伸体家具 | 异形家具 |
| `aid_ArrangementFromSpace` | **按空间自动排布** | 可能是灯具/家具自动阵列的现成入口，**未点开验证** |
| `aid_StartChangePrototypeSelected` / `…All` | 换原型（换型号） | 占位立方体 → 真 m3d 模型的替换路径 |
| `FurnitureCatalog` | 家具目录弹窗 | **未点开，内部树结构未知** |
| `EditableName` | 家具命名 | 可回写 IR space.id 便于追溯 |

→ **推荐两段式：先用立方体按 IR bbox 占位（尺寸可写、零联网、可回归测试），
再按需 `StartChangePrototype` 换成真模型。** 不要一上手就啃 `FurnitureCatalog`。

**灯具库 = 在线为主，但「选型规则」是本地的**：

- `C:\ProgramData\DIAL GmbH\DIALux\*.opk2` = **453 个厂商插件描述包**（84.9 MB，
  每个是 **SQLite** 库，magic `SQLite f`，schema 统一 8 表）。里面**只有厂商元数据**，
  不含光度数据：官网 URL、插件下载 URL（`plugindownload.dial.de/<slug>.zip`）、
  接入模式（**online 416 / offline 37**）、许可等级（Basic 260 / Standard 126 / Premium 67）。
- **装机自带 0 个光度文件**（安装目录 `*.ldt/*.ies/*.uld/*.gldf` 各 0 个），灯具目录纯在线要登录。
  **但本机另有 Zemax 样本可用**：`<Zemax 安装>\Objects\Sources\EULUMDAT\Sample.LDT`
  （351 KB）+ `IESNA\` 下 4 个 `.ies`（OSRAM / Projector / sample）——**可作离线导入测试素材**。
- **2026-09-06 实测 `File → Import → ImportLuminaire` 存在且 `en=True`**，文件对话框的类型过滤器
  （Win32 控件 1136，`CB_GETLBTEXT` 读出 8 条）明确收 **`*.uld;*.gldf;*.ldt;*.ies;*.cib;*.ltl`**。
  但**确认按钮 `BM_CLICK` 无效**（对话框不关、不报错、`CatalogListBox` 仍空、存盘拆 `.evo` 0 个灯具
  条目；换文件、等 9 s、不主动取消结果一致）——疑似新版 `IFileDialog` 需真实 accept 流程，
  STF 那套老对话框配方不适用。**这是灯具通道当前的唯一硬钉子**，三种未试手段见
  `docs/plan-mvp3-luminaire.md` P0。
- 装了 `Gldf.Net.dll` → **支持 GLDF 开放标准**，这是我们喂自有灯具数据的口子。
- **`%LOCALAPPDATA%\DIAL GmbH\DIALux\Mappings\ManufacturerMatchingRules.xml`（62 KB）
  是选型的金矿**：449 个厂商 + 186 个别名映射 + 20 条全局黑名单 + 18 条消歧规则。
  这是 DIALux 自己「从文本认厂商」的口径，直接复用可保证我们和它一致。
  样例：`PHILIPS ← [PHILIPS LEUCHTEN, ALKCO, CHLORIDE, COLOR KINETICS, DAY-BRITE, CFI,
  GARDCO, HADCO, LEDALITE, LIGHTOLIER, LUMEC, STONCO, INDAL]`。
  实测在表内：PHILIPS / Signify / ZUMTOBEL / ERCO / TRILUX / Thorn / iGuzzini / Fagerhult /
  Regiolux / **OPPLE / NVC / PAK**；不在表内：OSRAM、Delta Light。黑名单含「海洋王」。
- `RecentLuminaires` / `RecentLamps` / `RecentFurnitures` / `ObjectInfos` 四个缓存目录**全空**
  → 本机还没在 evo 里放过任何灯具/家具，没有可抄的既有样本。

## MVP1 收尾（已完成，2026-09-01 neat-freak 复核）

**2026-09-01 neat-freak 复核（Alice）：git 状态/README/architecture/agent-spec 勘误已核。pytest 实测 31 绿 + 1 挂（test_smoke 子进程读取线程 GBK 编码崩溃，属测试壳编码缺陷，非产品代码缺陷；Trae Work 的 UTF-8 环境下 32 全绿）。MVP1 验收结论不变。**

- [x] grill 6 条定案（2026-08-31）｜PM｜定案表见上游计划
- [x] prompts/trae-work.md v2 三模式模板（design/code/work）｜文档专员｜已定稿
- [x] S1-S3：真实图接入 + LINE+ARC 拼接 + CIRCLE/矩形灯具识别｜工程开发｜commit 1f35851
- [x] AC-7 肉眼对齐验收（用户 rubric）｜你｜房间轮廓整体对齐，左下角细节待 MVP2 改进｜build/room_layout.svg
- [x] 灯具去重 + 伪房间过滤｜工程开发｜commit de6b3da
- [x] 家具识别修复（T形交叉容差 bug + 十字交叉分割）｜工程开发｜commit 99754fc
- [x] test_parse_config_roundtrip 断言同步（0.5→2.0）｜工程开发｜已修复，pytest 全绿
- [x] 删除 prompts/zcode.md + AGENTS.md/agent-spec.md 勘误｜文档专员｜test_project_hygiene 4 项通过
- [x] neat-freak 文档收尾｜文档专员｜README/architecture/KANBAN 同步
- [x] neat-freak 复核补漏｜Alice｜agent-spec.md 模式表述勘误（第 31 行漏网）；遗留 → MVP2 修复单

**MVP1 交付物**：1 房间 + 22 家具 + 28 灯具（16 CIRCLE + 12 RECT）；产物 `build/room_layout.json`
+ `build/room_layout.svg`，其顶点数与面积口径见「现役几何口径」（该 JSON 已被 t_0deee369 的 parser
修复重跑覆盖，MVP1 期的面积数字在仓库里无对应产物）。

## MVP2（几何回环已验收，视觉复核转 MVP3 观察项）

**终态（2026-09-05 更新）**：代码与测试完成，门禁见「门禁实测」；README 快速开始三条命令端到端
跑通（ODA 27.1.0 → IR → STF，1 房间 / 22 家具 / 28 灯具 / validator 9 WARNING 0 HALT，几何见
「现役几何口径」）。修复后几何 `build/mvp2_fixed.stf` 已于 2026-09-05 在 evo 14.0 真机导入并
另存为 `build/mvp2_fixed.evo`，**顶点坐标 11/11 回环命中、内嵌 STF 字节相同** → MVP2 从「待验收」
转「几何验收通过」。剩下的只是墙体朝向 / profile 归类两条**人眼观察项**，已转 MVP3 观察项，
不再阻塞 MVP2。范围提醒：STF 只出房间几何，灯具不进文件（见「现役实现边界」第 2 条）。

- [x] **P0 修复单**：test_smoke 子进程编码修复（subprocess.run 加 encoding="utf-8"）｜AI 会话｜2026-09-02，pytest 32 全绿
- [x] 技术栈文档同步（README/agent-spec 天硕版：Hermes 追踪 + claude 子员工，TR-7.3/7.4 断言同步）｜AI 会话｜2026-09-02
- [x] **MVP2：IR → STF 生成器（src/exporter/stf.py）**｜backend-developer｜2026-09-02｜t_7c5dc714
  - 审查：两轮 code-reviewer（CRITICAL/HIGH 全修），测试 22→70 条
  - 遗留：房间轮廓疑似混入家具边（柜子识别成墙壁）→ 已在 t_0deee369 修复（见下）
- [x] **架构师 evo 14.0 真机实测（2026-09-02，导 `build/mvp2_out.stf`）**：闭合形态 + 保留 IR 原绕向
  + 非凸多边形 + 中文名 4 条全过，**结论已回填 `src/exporter/stf.py` docstring**；当时观察到的
  「多余墙体」= parser 柜子变墙，已由 t_0deee369 修掉
- [x] **Parser 修复：房间多边形混入家具边（柜子变墙）**｜backend-developer｜2026-09-02｜t_0deee369
  - 根因：真实图里贴墙柜顶边**直接借用墙线**，两者共享端点；`_chain` 的 T 形分割把整条墙线
    在柜子端点处切断，环搜索走到断点时拐进柜子轮廓 → 柜子凸台/凹槽被并进房间环
  - 修法（只动 parser，三道机制）：
    1. 墙线环 pass：`extract_rings_from_line_arc(split_at_t_junctions=False)` 额外跑一轮，
       墙线保持整条 → 直接拼出真实墙围轮廓（`ParseConfig.wall_ring_pass`，默认开）
    2. 锯齿择优：`ring_preference_key` = (是否墙线环, <0.2m 短边数, -顶点数)，
       替掉 `dedup_rooms` / `parse_dxf` 里原来「保留顶点最多」的择优
    3. 房间环平滑兜底：`smooth_room_ring` 填平 <0.5 m²（= validator 规则 2 下限）
       且**填平后面积变大**的凹槽 + 合并共线断点（`ParseConfig.smooth_room_rings`，默认开）
  - 真实图实测（布局图.dwg 重跑）：主房间候选从 LINE+ARC 链环 `LINEARC_020_E53_355C`
    （含锯齿的旧环）换成墙线环（0 条锯齿，几何见「现役几何口径」）；
    北墙单边直通、东墙直通、西墙台阶消失；南墙真实凸台保留
  - 无回归：22 家具仍全部识别、28 灯具全部落在房间内、validator 违规数不变（9 WARNING，
    全是家具小面积，0 HALT）；pytest 全绿（该任务新增 45 条测试，门禁数字见「门禁实测」）
  - 产物：`build/room_layout.json`、`build/room_layout.svg`、`build/mvp2_fixed.stf`
  - 已知边界：柜子一侧正好贴转角/隔墙时凹槽退化成转角台阶，几何上与真实转角不可区分，
    按设计不动（有专测记录）
- [x] **evo 14.0 真机复验（原 MVP2 唯一阻塞项）**｜你（computer use 代跑，非架构师人眼）｜2026-09-05
  - 做法：DIALux evo 14.0 真机（`D:\dev\DIAL GmbH\DIALux.exe`，PID 12740），全程 UI Automation
    驱动，无坐标盲点：`文件(aid=File)` → `导入(aid=Import)` → `STF 文件(aid=ImportStf)`
    → 文件对话框选中 `mvp2_fixed.stf` ListItem（Select+Invoke）→ `保存(aid=Save)`。
    工具链见「computer use 通道」。
  - **几何回环验收通过**，5 条硬证据：
    1. 导入后窗口标题变 `D:\dev\dialux-compiler\build\mvp2_fixed.evo - DIALux evo 14.0 (64-Bit)`；
       UIA 后代 157 → 271，`Save` 由 disabled 变 enabled，新出现 `MenuGotoConstructionMode`
       → 已进构造模式且工程已载入
    2. 房间名 `WALLRING_000_E18_2DF7` 落地：屏幕 OCR 读到 `WALLRING 000`，
       `.evo` 内 `Project/ProjectData/ProjectData.dat` 中出现 **6 次**
    3. 另存原生工程成功：`build/mvp2_fixed.evo`（**69112 bytes**，ZIP 容器 27 项，
       `ArchiveInfo.xml` Version 5.14.0.5 / Title `mvp2_fixed`）
    4. `.evo` 内嵌 `Project/STF/k0lkngwj.tmp` 与源 `mvp2_fixed.stf` **逐字节相同**
       （均 591 bytes，sha256 前 16 位 `5d8001dfaea2f7bb`）
    5. **全部顶点坐标以「米 + float64」出现在 `Project/ScenegraphScene`**，
       且出现次数与 STF 里的复用次数成正比（复用 2 次的值出现 84 次、3 次的出现 126 次、
       其余各 42 次）。**无毫米单位命中** → evo 内部按米存，STF 的米口径无需换算
  - **多余墙段消失**：本次导入的是 16 唯一顶点版（旧坏几何 53 唯一顶点），
    `.evo` 里内嵌 STF 字节相同且顶点坐标全中 → 柜子边没有任何进入房间轮廓的通道
  - **仍待人眼复核（不阻塞 MVP2 收尾，转 MVP3 观察项）**：
    - 墙体朝向（CCW 绕向在 evo 里的实际法向）无法从坐标断言，需截图人眼看
    - evo 自动套的 profile 是 `5.1 DIALux 预设` / `5.1.4 标准（室外交通区域）`，
      而 mvp2 是室内会议室 → STF 导入走的是「建筑物/场地」容器而非「室内空间」，
      是否影响后续照度计算未验
    - 工程缩略图 `build/_evo_thumbnail.png`（128×96，337 色，28.1% 非背景像素 → 有绘制内容，
      非空白）已导出备查，但本会话主模型无图像输入，未做视觉判读

## MVP3 待办

- [ ] MVP3：灯具表 → 已有房间布灯｜坐标正确、型号匹配（含 Q5 灯具表匹配 TODO）
- [x] **MVP3 演示交付：悬浮小部件驱动 DIALux 全自动建壳｜2026-09-06 完成**
      计划文档 `docs/plan-mvp3-demo.md`。**一条命令 `python scripts/demo_run.py`
      从 DWG 跑到 DIALux 里存好 `.evo`，实测 9.91 s**（解析 2.62 s / STF 0.48 s /
      UIA 6.81 s）。带界面版 `python -m src.ui.overlay`。

      **落地验收（拆 `.evo` ZIP，非人眼）**：`build/demo_room.evo` 69363 B，
      `Project/STF/53ch443s.tmp` 与 `build/demo_room.stf` **逐字节相同**；
      房间顶点 + 层高共 **11/11 个已知坐标**在 `Project/ScenegraphScene` 里
      命中 float64 米（命中次数与复用次数一致），
      对照组证明扫描法有效。

      **界面验收（无视觉模型，直接数像素）**：`build/overlay_mid.png` /
      `overlay_done.png`——进度条填充宽 **80 px → 268 px**（条内宽约 272 px，
      对应 31% → 100%），绿色 OK 字形块 **2 个 → 6 个**，与六行步骤一致。

      **两个真机踩坑（都是这轮付出真代价换来的，已写进代码注释 + 测试）**：
      1. **DIALux 的文件对话框对 UIA 完全不可用**：37 个后代全是 `ControlType.Pane`
         且 `GetSupportedPatterns()` **为空**，没有 `ValuePattern` 也没有
         `InvokePattern`。但它 Win32 层是标准 `#32770`，控件 id 齐全
         （1=打开、2=取消、1148=文件名 ComboBoxEx32、1136=类型筛选）。
         → **菜单走 UIA，对话框走 Win32 窗口消息**。填文件名只有
         `SetWindowText` 有效，`SendMessage(WM_SETTEXT)` 完全无效，且
         ComboBoxEx32 与内层 Edit **不互相同步**，必须两层都写。
      2. **PowerShell 把 P/Invoke 的 `$null` 字符串参数编成空字符串**，
         不是 NULL 指针。`FindWindowEx(..., $null)` 于是只匹配标题为空的窗口，
         对任何真对话框都返回 0。必须用 `[NullString]::Value`。**这个坑吃掉了
         三次真机失败。**
      3. **任何一个可见模态框都会把主窗口的 UIA 后代数从 310 压成 3**，
         于是 `File`/`Save` 全找不到，报出来却是 `menu-file not-found`，
         指向完全错误的方向。上一轮被一个更早会话遗留的「重命名」框卡死两次。
         → `driver.py` 加了预检：自动取消遗留的**文件**对话框，遇到其它模态框
         **拒绝启动并要求人工处理**（可能是「是否保存更改」，自动点会丢工作）。

      审查意见：自审两轮。第二轮（2026-09-06 凌晨，架构师看屏幕发现异常触发）
      **推翻了第一轮的一个错误结论**，见下。结论——保底路径可复现（**连跑 3 次 3/3，
      每次验「STF 字节一致 + 坐标 7/7 命中 + 屏幕零残留」三项**），门禁 199 passed + ruff 0。
      遗留：① 停止只能停在步与步之间，DIALux 里已建的东西不回滚，界面如实显示
      「停在第 N 步，是半成品」，检查点/回滚推到 MVP3 之后；② 家具占位（P3）未做；
      ③ `run_calculation` / `export_report` 两类动作的 `weight` 是占位 1.0，
      从未真跑过，别当实测数据。

      **④ 自审勘误：对话框不关是我们自己的 bug，不是 DIALux 的习性｜2026-09-06 已修**

      我第一轮写的是「DIALux 每次导入后会留下一个**用户看不见**的文件对话框，
      预检不是冗余是必需品」——**这句话错了两处**，是架构师看屏幕说「好像卡在
      导入 STF 这一步」才被抓出来的。实核：那个窗口 960×540、位于 (244,156)、
      `showCmd=NORMAL`、**Z 序第 1 层压在 DIALux 主窗口上面**，文件名框里还留着
      我们填的路径。它不是看不见，它就明明白白摆在屏幕正中，任何人看了都会以为
      流程卡住了。

      真正的根因不在 DIALux，在我们：**`BM_CLICK` 到「打开」按钮会真的触发导入
      （标题改了、场景重建了），但不会让对话框销毁自己**——大概是绕开了新版
      `IFileDialog` 关闭自身所需要的正常输入路径。逐阶段快照证明它从
      `dialog-filename` 一路活到 `done` 之后，始终是同一个 hwnd。

      修法：`import-settled` 确认标题变化之后，显式 `BM_CLICK` 控件 2（取消）把窗口
      收掉并轮询确认消失，收不掉就 `Fail 'dialog-still-on-screen'`。导入已经落地，
      点取消不撤销任何东西。必须放在 `save` 之前——留着它就是个可见模态框，
      而可见模态框会把 UIA 后代数压成 3，`Save` 会跟着找不到。

      预检（`cancel_file_dialogs`）仍然保留，但定位从「必需品」降级为
      **崩溃残局的兜底**：正常收尾现在自己扫干净，预检只管上一次跑崩了的情况。

      连带教训（第二次踩同一个坑）：这轮改 `.ps1` 时我用 `edit` 工具写了中文注释，
      618 个非 ASCII 字节 → PowerShell 按 GBK 读 → `ParserError` 炸在第 242 行。
      **仓里本来就有 `test_driver_ps1_is_pure_ascii` 这条测试专门防它，我却先跑真机
      才跑门禁。** 顺序错了：改完先跑门禁，再碰真机。
- [ ] **P3 家具长方体占位｜2026-09-06 状态更新：导航障碍已解除，本轮仍主动不做**
      1. ~~`CuboidWidth` 等 AutomationId 全部 MISSING，得先摸清怎么切到家具页~~ ——
         **已解决**：`MenuGotoConstructionMode` → `MenuGotoShowFurnitureTool`（`Invoke`），
         家具工具页可达，`aid_DrawRectangle` 等布置原语会随激活出现（2026-09-06 实测导航层）。
      2. 仍未解决且更硬：**放家具要在 3D 视口里点坐标，而视口是自绘的、UIA 完全看不见**
         （`Tree`/`TreeItem`/`List`/`ListItem` 枚举恒为 0）。那意味着要退回
         「算像素坐标 + 模拟鼠标」，机制上比现在这套 UIA + 窗口消息脆弱一个量级。
      结论：不在赶周报的窗口里开这条战线。下一轮评估 `aid_ArrangementFromSpace`
      （自动排布，可能绕开点坐标）。
- [x] **MVP3 前置：STF 灯具段真机判定｜2026-09-05 结论为「此路不通」**
      （computer use 代跑，非人眼，方法同 MVP2 的 `.evo` 拆包比对）

      **DIALux evo 14.0 完整读入 STF 但彻底忽略 `NrLums` / `Lum{i}` 段，0 个灯具对象落地。**

      证据链（`build/mvp3_lums.stf` 1618 B → 导入 → 另存 `build/mvp3_lums.evo` 69378 B）：
      1. 嵌入的 `Project/STF/1ohjxjrj.tmp` 与本地 STF **逐字节相同**，`NrLums=28`、
         28 行 `Lum{i}` 全在里面 —— 文件确实被完整接收，不是被截断或拒绝。
      2. `Project/ScenegraphScene` 与无灯基线 `mvp2_fixed.evo` **同长度 85749 B**，
         仅 36 字节不同 = 12 个 3 字节块，全是 0.65~1.03 区间的 float32 **值置换**
         （0.65↔0.857、0.825↔1.03、0.69↔0.897 互换位置，值集合不变），
         属 GUID 哈希序导致的重排，**不是新增几何**。
      3. 灯具 8 个唯一坐标（x: 0.945 / 4.281 / 7.617 / 10.954，y: 0.959 / 3.003 / 5.047 / 7.091）
         在 `ScenegraphScene` 里 **0/8 命中** float64 米，**0/8 命中**毫米。
         同一文件的对照组房间顶点 **4/4 命中**（命中次数与复用次数一致）→ 扫描方法有效，负结果可信。
      4. `Project/InteractionManager/StfManager.dat` 只记 `StfManager (0, 0, #2)` +
         文件引用（`StfVersionSimple=0` / `StfVersionCoords=0`），无任何灯具对象。

      **根因判断**（未逐条验证，属推断）：STF 是 DIALux 4 时代格式，灯具需引用真实厂商型号 +
      光度数据（LDT/IES/GLDF），而我们写的第 4 字段是从 DWG 块名派生的几何符号
      （`CIRCLE-r7.6-0` / `RECT-1555.0x300.0-11`），不可能被解析成灯具。改字段格式的天花板很低。

      → **决策：灯具落地改走 computer use 通道**，STF 只保留房间几何职责。
      `_luminaire_lines` 保留但必须在 docstring 标注「evo 14.0 实测无效」，
      不要再当作可用出口；`NrLums` 是否继续写待你定（写了无害，但会误导读者）。

      **顺带暴露两个 IR 侧缺陷（新增待办）**：
      - **28 盏灯的 `z` 全是 0**（地面），天花高 2.8 m。DWG 是 2D 图，没有高度信息，
        布灯必须由规则引擎补挂载高度（吸顶 2.8 / 吊装 2.8−吊杆），现在完全没有这一步。
      - **两类灯具混在一个未区分的列表里**：16 盏 `CIRCLE-r7.6`（半径 7.6 的筒灯）
        + 12 盏 `RECT-1555.0x300.0`（1555×300 mm 线性灯具/灯带）。选型和布置逻辑完全不同，
        IR 需要显式 `luminaire_kind`（点光源 / 线性），不能靠下游猜 symbol 前缀。
- [x] **MVP3 前置：灯具挂载高度与类型分类｜2026-09-05 完成**（承接上一条真机验证暴露的两个洞）

      改动与实测（真实两张图复跑：`布局图.dwg` + `灯具图.dwg`）：

      1. **宪法**（`spec/ir.schema.json`）给 `Luminaire` 加两字段并写清 `z` 语义：
         `kind` 枚举 `point|linear|area|unknown`（解析器显式声明，**下游禁止靠 symbol 前缀反推**）、
         `dims` 对象（`radius_mm`/`w_mm`/`h_mm`，选型尺寸）。`required` 未动，向后兼容。
      2. **解析器**（`src/parser/dxf.py`）：`Luminaire` dataclass 加 `kind`；CIRCLE→`point`，
         RECT→新函数 `classify_rect_luminaire` 按长宽比判（阈值 `LINEAR_ASPECT_MIN=3.0`，
         ≥3 为 `linear` 否则 `area`），INSERT 块引用显式写 `unknown`（块名不携带几何，判不了）。
      3. **join**（`src/planner/join.py`）此前只写 5 个字段，**把 parser 的 `attrs` 整个丢掉**
         → 新增 `_dims_from_attrs` 显式搬运尺寸，并圆到 3 位小数消除
         `1555.0000000000014` 这类浮点噪声（修前同型号 12 盏线性灯分裂成 4 组不同 dims）。
      4. **新模块 `src/planner/mount.py`**：`assign_mount_heights` 按 `mount` 回填 `z` ——
         `recessed`/`surface`→`ceil_h`，`pendant`→`ceil_h − 吊杆`（默认 0.5，不许压到楼面下），
         `wall`→壁装高（默认 2.2，夹到不超天花），`floor`→0，`other`→告警交人工；
         `ceil_h` 缺失或非正则整个 space 跳过并告警。默认只回填 `z=0` 的，尊重图纸已有高度。
      5. **validator 补两条规则**：规则 7 `LUM_MOUNT_Z_UNSET`（ERROR）抓吊顶类灯具 `z=0`
         —— 这正是 28 盏灯趴地板却零告警的缺口（规则 4 只查上溢）；
         规则 8 `LUM_KIND_DIMS_MISMATCH`（WARNING）抓 `kind` 与 `dims` 不自洽。
         `validate_ir` docstring 同步成准确的 7 条规则表，并说明规则 6 为何不在其中
         （需额外传 xlsx 字典，仍零调用者）。
      6. **CLI 接线**（`src/main.py`）：回填插在 `join` 之后、`validate_ir` 之前，
         新增 `--pendant-drop` / `--wall-mount-h` / `--overwrite-z`。

      **顺手修掉一个单位错误**：CIRCLE 分支原先把 `entity.dxf.radius` 直接塞进 `radius_mm`，
      而本图 `$INSUNITS` 是 cm → 7.6 cm 被当成「7.6 mm」写出去，**差 10 倍**
      （直径 15.2 mm 的筒灯不存在）。RECT 分支本来就有 `convert_to_meters(...)*1000`，
      CIRCLE 漏了。修后 `radius_mm=76.0`（直径 152 mm，正常筒灯开孔），原始值保留在
      `radius_raw` + `raw_units` 供复核。此前一直没暴露，是因为 `attrs` 根本没进 IR。

      **复跑实测**（`build/mvp3_ir.json`）：28 盏灯 `kind` = 16 `point` + 12 `linear`；
      `z` 全 = 2.8（回填前全 0）；`mount` 全显式写回 `recessed`；
      `dims` 收敛成两组（`{radius_mm:76.0}` ×16、`{w_mm:1555.0,h_mm:300.0}` ×12）；
      `_meta.luminaires=28`（旧产物是 0，此处一并证实 09-04 的回填修复生效）。
      validator 从 37 条降到 9 条，`LUM_MOUNT_Z_UNSET`×28 全清，剩 9 条是家具伪 space 的
      `AREA_OUT_OF_RANGE`（既有问题，与本次无关）。jsonschema 0 错。
      门禁 **187 passed**（新增 40 条，`tests/test_luminaire_kind_mount.py`）+ ruff 0 errors。

      **遗留**：`mount` 目前全靠默认值 `recessed` —— 图纸没有明装/吊装信息，真实项目需从
      灯具表或图层名推断，属 MVP3 选型的一部分，未做。
- [ ] **MVP3 主路径：computer use 布灯｜2026-09-06 P0 破解（硬钉子已拔），P1 坐标机制已探明**
      1. **导航层找到了**：`MenuGotoConstructionMode` → `MenuGotoShowLuminaireArrangementTool`
         （`Invoke`）即进入灯具布置工具，工具页整批换成 `Lighting.*` / `Luminaires.*` 系列。
      2. **布置原语齐全**（`IsEnabled` 随是否有灯具型号变化）：`aid_DrawPoint`（点光源，
         对应 IR 16 个 `point`）、`aid_DrawLine`（灯带，对应 12 个 `linear`）、
         `aid_ArrangementFromSpace`（按空间排布）、`aid_StartChangePrototypeSelected`/`…All`。
         2026-09-06 实测：导入灯具成功后三者全部 `en=True`。
      3. **目录按钮是 `TogglePattern`**：`LuminaireCatalogButton` / `BrandCatalogButton`；
         Toggle 开 → `CatalogListBox` = 「本项目已用灯具」，children 从 0 → ≥1 当有型号时。
      4. ~~唯一硬钉子：`ImportLuminaire` 对话框确认无效~~ → **2026-09-06 已破解，两层结论**：
         - 机制层：`BM_CLICK` 对 DirectUI/IFileDialog 无效，**有效 accept =
           UIA 树里按文件名找 `ListItem` → `SelectionItemPattern.Select()` →
           `InvokePattern.Invoke()`**（双击语义）；对照 `ImportDrawing` 干净通过。
         - 授权层（真凶）：**免费版只放行 DIAL 会员厂商灯具**。LDT/IES 第 1 行厂商名非会员
           （自造 `DC-MINIMAL-LDT`、`ZEMAX`）→ 弹「解锁非会员」付费墙（`ButtonBuyNow`/
           `ButtonGoToDialuxPro`/`ButtonClose`），0 落地；同文件改第 1 行成 `PHILIPS`/`OPPLE`
           → **导入成功，CatalogListBox=1**。判据=厂商名是否 DIAL 会员（`ManufacturerMatchingRules.xml`
           449 厂商可复用）。详见 `docs/plan-mvp3-luminaire.md` P0。
      5. **P1 坐标机制已探明**：`aid_ArrangementFromSpace` Invoke 后出现**整套可写数值控件**
         （不是像素点视口）：`ToolPartFieldArrangementPosition`（`PolygonPosition_X/Y/Z` 米）、
         `ToolPartFieldArrangement`（`ElementCountX/Y` + 对齐 radio + `ArrangementObjectName`）、
         `ToolPartMountingHeight`（`MountingHeight_Value`/`LightPointHeight_Value` 米）、
         `ToolPartSpaceAssignment`（`GlobalSpaceComboBox` 选空间）、多边形点表格
         `ToolPartFieldArrangementPolyLine`（`PART_Input` x/y/z/°）。`aid_DrawPoint` 反而无数值框
         （提示「在 CAD 视窗单击/拖放」）→ 像素路线，脆，弃。
      6. 2026-09-06 真机实证（破坏性，工程已 dirty 后存盘 `build/mvp3_lums.evo` 177990 B）：
         `aid_ArrangementFromSpace` 激活 + Save 后拆包，`.evo` 内 `ProjectData.dat`（非
         ScenegraphScene）出现 **`LuminaireElement`×114 / `FieldArrangementElementPositionData`×114**
         （两次激活各生成一套规则网格）→ **灯具实体确实落盘**。
         房间轮廓自动进入排布多边形（`PART_Input` 内坐标与现役
         几何口径吻合），`ElementCountX/Y`=9/7、估算照度 510 lx @目标 500。
         遗留：① 这是**规则网格自动排布（房间外不封闭点被扣）**，不是 IR 图纸逐盏坐标；
         ② 验收扫描对象要从 `ScenegraphScene` 换成 `ProjectData.dat`（灯具数据在后者，
         ScenegraphScene 85749 B 全程未变）；③ 演示 LDT 厂商名是改 ZEMAX 数据第 1 行来的，
         交付前需换真实会员厂商公开文件或明确「占位型号」。
         **正式型号文件**：`build/ies/fixed/NPTLED351_NVC.IES`（NVC 官网真实光数据 +
         补全 `[MANUFAC] NVC` 字段；原始文件在 `build/ies/`）。
      7. 实测结论已入 `docs/plan-mvp3-luminaire.md` 与 KANBAN；探针脚本与临时记忆文件
         （`build/p*.ps1`、`build/P0_PROGRESS.md`）2026-09-06 已随「没用的就删了」清理。
      8. **P2 执行器内核 2026-09-06 完成**：`src/executor/kernel.py`（execute_plan 派发/重试/
         HALT/进度）+ `src/executor/uia/driver_plan.py`（UiaDriver：create_space 走 STF 批量、
         place_luminaire stub 收集）+ `src/main.py --execute` 接新链路。真实图实测 55 条全派发、
         28 盏 stub、进度 0→100%；门禁 216 passed + ruff 0。计划文档 P2 段已更新。
      9. **P1 真机收尾 2026-09-06 晚（架构师在场）**：干净流程跑通「重开 demo_room → 导入
         NVC 真实 IES（无 paywall）→ 切工具 → Invoke ArrangementFromSpace **恰好 1 次** →
         Save」，拆包 1 套排布 / 12 盏（4×3）/ 原点 (5.95, 4.39) 房间中心。
         **两个关键经验**：① 每次 Invoke ArrangementFromSpace 都叠一套排布（最多叠到
         7 套 88 盏，视觉像「放歪」），正确做法是恰好一次；② ElementCountX/Y 可写但
         re-invoke 会被 DIALux 按房间自动重算（4×4 → 跳回 4×3），**不能靠它精确复现
         图纸坐标**——DIALux 网格是「均匀铺满房间」（间距=房间/列数），图纸是「固定
         间距」（3.336/2.044m）。架构师口头确认：自动排布「灯具在房间里均匀分布」可作
         MVP3 演示交付，如实标注「非图纸原位精确坐标」。拆包坐标模型：灯具绝对坐标 =
         LuminaireArrangement.CoordSys3D 原点 + CoordSys3D 局部偏移；PART_Input 多边形
         表格只读（只能在 CAD 视口画）。
      10. **保存弹窗自动应答 2026-09-06 完成（BetterGI 思路的 UIA 版）**：
          `src/executor/uia/autosave.ps1` + `driver.auto_answer_save_prompt()`：识别
          DIALux 进程里「含 Yes/No 按钮 + 至少一个 Edit」的 WPF 弹窗（=保存/覆盖确认框），
          命中就点「是」（保留工作），其它模态框不碰。已接入 run_import 预检。门禁
          221 passed + ruff 0。
      11. **DIALux 生态资料调研 2026-09-06**：`docs/reference-dialux-ecosystem.md`
      12. **合规线性灯配光已下载 2026-09-07（自动化执行）**：24 个会员厂商线性灯/面板灯 IES
          → `build/ies/linear/`（含 `_下载报告.md` + 3 个留档脚本 + 2 个 JSON，调试残留已清）。
          OPPLE 16 个全合规（Re295 面板灯 245×1145mm 最贴近需求）+ NVC 8 个（NLI 线性灯 4 个
          合规、NPN 面板灯 4 个 MANUFAC 空/ETI 已如实标注、待补齐 NVC 再导入）。
      13. **OPPLE Re295 线性灯导入已验证 2026-09-07**：真机走 ImportLuminaire（ListItem
          Select+Invoke），无 paywall、CatalogListBox 出现 `LEDPanelRc-S-Re295-30W-4000-WH-U19`，
          Save 后工程正常。**演示口径确定为三段式**：① demo_run 真跑建壳 → ② 12 盏 NVC 筒灯
          展示 → ③ 线性灯文件+导入已通（不承诺 28 盏）；家具只展示 IR 数据层（不真放）；
          录屏用 Xbox Game Bar。演示方案见 `docs/plan-mvp3-demo-stage.md`。
      14. **两批灯已一起放好 2026-09-07**：`demo_room.evo` 现含 **2 套排布 32 盏**——12 盏
          NPTLED 筒灯（4×3）+ 20 盏 Re295 线性灯（4×5），原点同房间中心、网格错开。
          Arrangement=2 / LuminaireElement=64，已保存并备份 `demo_room.evo.2batches`。
          「一起录」可行：打开该工程即可同屏展示两批不同型号灯具。
      15. **放灯链路已产品化 + exe 交付 2026-09-07**：
          - `src/executor/uia/luminaire.ps1` + `luminaire.py`：一条命令导入 IES + 切工具 +
            选原型 + ArrangementFromSpace 排布 + 保存（纯 ASCII，STEP 协议）。
          - `driver_plan.py` `place_luminaire` 从 stub 升级为 `arrangement` 真通道
            （按 kind 解析 IES、失败 RETRY、注入 place_fn 可测）。
          - `demo_run.py --luminaires auto`：建壳后自动放两批灯（point→NPTLED、
            linear→Re295），真机 exit=0，`arr=20 x Opple Re295` 验证厂商前缀匹配修复。
          - **PyInstaller 打包 `dist/demo_run/demo_run.exe`（~11MB）**：含 3 个 .ps1 +
            spec/ir.schema.json 为 datas；exe 内进程调用（不依赖外部 python）；
            validator/schema 路径 PyInstaller 兼容（`src/core/env.resource_path`）。
            exe 需同目录放图纸 + config + `build/ies/`。门禁 224 passed + ruff 0。
          - 演示用 exe 真跑（非预放），README 已加打包/运行说明。
          - **GUI 启动器 2026-09-07**：`src/ui/launcher.py`（PySide6）+ `scripts/launcher.spec`
            → `dist/launcher/launcher.exe`（windowed，双击出窗口，~127MB 含 PySide6）。
            交互参考 BetterGI HomePage：大「启动」按钮 + 「同时启动 DIALux」开关
            （LinkedStart：目标未运行则自动打开）+ 配置区（图纸/config/灯具可浏览选择，
            默认自动探测 exe 旁文件）+ 实时日志区。源码版 `python -m src.ui.launcher`。
            路径运行时确定（参考 Mrite，不硬编码）；spec ROOT 用 SPECPATH 自动探测。
          - **overlay 悬浮窗升级 2026-09-07（BetterGI MaskWindow 体验）**：`src/ui/overlay.py`
            ROWS 扩到 9 行（自动开 DIALux → 解析 → STF → 导入 → 导入筒灯 → 排布筒灯 →
            导入线性灯 → 排布线性灯 → 保存），子进程日志 Popen 逐行实时转发到半透明窗
            （LogTextBox 模式），加「同时启动 DIALux」勾选框（LinkedStart）+ 滚动日志区。
            执行时用户能实时看到每步在做什么。源码版 `python -m src.ui.overlay`。
          （官方 STF/GLDF 格式、GitHub 参考库（本地 D:\dev\dialux-references\）：
          STF-Exporter/EvoParse/eulumdat-py/dialux-mcp/DIALux_Toolkit，详见
          docs/reference-dialux-ecosystem.md，合规灯具配光获取路径）。STF 灯具段格式已
          按 STF-Exporter 修正（LumN.Pos 三行式），
          但 evo 14.0 仍忽略（双重证据见「现役实现边界」第 2 条）。
      下一步：Q4 落位口径 **已定 2026-09-07：自动排布（非图纸毫米级原位）**——架构师
      现场确认「放得挺准」，作为 MVP3 演示交付；精确图纸坐标（DrawPoint 像素/直写 .evo）
      列为后续。演示用 exe 真跑（`demo_run --luminaires auto`），验收沿用 `.evo` 拆包
      （灯具在 `ProjectData.dat`，不是 `ScenegraphScene`）。
      16. **通用工作台骨架 2026-09-07（全抄 BetterGI 架构）**：`src/workbench/`（Task/Trigger/
          Flow/Config/Dispatcher）+ `src/tasks/dialux/`（room_task 建壳、luminaires_task 布灯、
          report_task 报告占位、autosave_trigger 实时保存应答）。
          BetterGI 映射：GameTask→tasks/、ITaskTrigger→workbench/trigger、OneDragon→workbench/flow、
          Config→workbench/config、TriggerDispatcher→workbench/dispatcher。
          原则（架构师）：先堆城堡用户删减；不绑死 DIALux，未来 Zemax/Transport 复用骨架。
          门禁 231 passed + ruff 0。
      17. **标准流程文档 2026-09-07（架构师推荐：按标准任务流程 v1 生成）**：
          `docs/standard-dev-workflow.md`（软件开发七步链：素材→定案→计划→执行→门禁→真机→收尾提交）、
          `docs/standard-dialux-run.md`（DIALux 运行 SOP agent 可执行版，v2 已扩：解析→STF→导入→布灯→
          家具→桌面评估区→计算→读结果，含已验证链路与坑）、
          `docs/reference-standard-task-flow-v1.md`（通用六步链 v1 参考）。
          软件开发增量按七步链走；DIALux 运行对照既有手动 SOP 与本流程（自动）差异表。
          家具建模/评估区/计算三通道真机探针见 `build/probe_20260907_channels.txt`
          （Cuboid 可写 + DrawExtrusionFurniture 拉伸 + CalculationButtonStart en=True）。
      18. **GUI 启动器 + overlay 悬浮窗 2026-09-07/08**：`src/ui/launcher.py`（启动按钮 +
          「同时启动 DIALux」开关 + 配置 + 日志，内部跑 workbench Flow 一条龙）+
          `overlay.py` 9 行步骤实时显示（LogTextBox 模式）。打包 `dist/launcher/launcher.exe`。
      19. **计算链路真机验证 + 家具路线三反转定案 2026-09-08**：
          - **计算 ✅**：`CalculationButtonStart` 触发（按钮变「取消」→变回「计算」=完成，
            32 盏灯 <1 分钟）→ **UIA 直读结果**：`ResultsMonitorSurfaceResultAverage`=实测读数、
            `UniformityAverage`=实测值。照度远超目标 = 自动排布偏密（链路通、策略待调）。
          - **「家具=空间」最终判死（架构师 3D 验收）**：UIA ListItem 双击导入成功
            （probe_furniture.evo，Space=23），但三重缺陷——22 家具各成**独立建筑物**
            （STF ROOM=建筑语义）、拆包 CoordSys3D 证实全堆原点 (0,0)（STF 绝对坐标被当
            建筑内相对坐标）、名称乱码（家具_→溜踩佂）。教训：**导入成功 ≠ 位置正确，
            必须 3D 人眼验收**。灯具不受影响（后导入走房间内排布，坐标正确）。
          - **IFileDialog accept 唯一有效姿势**：UIA `ListItem.Select()+Invoke()`；
            Win32 SetWindowText+BM_CLICK/Enter 全部无效（对话框残留假象，勿据此判成败——
            判据 = 标题变化或拆包数实体）。
          - **计算元件工具探明**：`MenuGotoShowCalculationObjectTool`（矩形/多边形/单点
            三种元件 + HeightOffset 高度 + 网格密度参数），均画布绘制语义（唯一剩余脆点）。
          - 家具当时下一步曾暂定直写 `.evo`；该结论已被 2026-09-08 的 FurnitureTool 单件 UIA 闭环覆盖，
            批量路线见第 20 条。
          - 全过程见 `docs/standard-dialux-run.md` v2（Step 7/9/9.5/10 真机结论）。
      20. **感知层 L2 落地 2026-09-09（三省六部定案 + BetterGI 模式逐点对比）**：
          `docs/plan-perception-layer.md`（含对比表）→ 实现 `workbench/recognition.py`
          （UiState 状态机 + Win32 感知：NO_WINDOW/IDLE/DIALOG/CALCULATING）、
          Trigger.supported_states 状态路由（对应 BetterGI SupportedGameUiCategory）、
          Dispatcher 每轮先感知再派发 + on_state_change 广播、autosave_trigger 挂
          dialog 态、新增 calc_watch_trigger（计算完成边沿检测，为「读结果」铺路）。
          三省裁决：抄 BetterGI 感知循环（状态识别+触发器路由），执行层保 UIA。
          门禁 244 passed + ruff 0；真机验收四场景全过（IDLE/无弹窗不误报/路由/NO_WINDOW，
          见 plan 文档证据表）。vibe 试点：requirements→plan 冻结流程跑通（run a2ed09de/9e4d443c）。
      21. **计算链路 vibe 增量 2026-09-09（进行中，明日续）**：vibe 冻结 4 模块
          （furniture→eval-area→calc→read-result，run 0b006474→3142b123→0b006474 修订），
          状态 ready_for_execution。**当日进展**：① 撞车发现——家具单件闭环/计算/UIA 直读
          照度隔壁会话 9/8 已完成，Wave1/3/4 修订缩窄；② 新增
          `furniture_batch_task.py`（IR 适配 polygon→bbox/height_m 0.75m + 批量循环 +
          拆包验收 FurnitureElement），5 测试全绿；③ **批量首跑 22/22 失败**——
          真机教训：家具尺寸 Edit 只在「选中已建对象」后出现；DrawPoint 点画布中心
          落在空间外（ViewAll 后房间不满视口）→「结果是无效」弹窗；**架构师现场纠偏
          路线：点「选择」→ 物件库面板展开 → 更多物件…（完整家具库，非简单几何体）**；
          ④ 工具沉淀 `build/win_click.ps1`（BetterGI 式窗口比例点击，最大化+相对坐标，
          免绝对坐标漂移）；⑤ 明日继续：按架构师路线走「选择→库→更多物件→选桌子→
          点画布置入」序列，或评估区直上（CalculationObjectTool）。
          运行态：DIALux 已关（demo_room.evo 未保存家具，FurnitureElement=0 基线）。
      20. **家具识别 IR + 单件 Cuboid UIA 闭环 2026-09-08**：
          - `src/parser/dxf.py` 样例图纸仍抽出 **1 房间 + 26 家具**；家具记录新增
            `room_id/kind/height_m/rotation/confidence/source_layer/source_entity`，中心点按房间
            包含关系归属，低置信度候选保留。
          - 新增 `FurnitureTask`、`src/executor/uia/furniture.py/.ps1`，工作台启动器增加显式
            「家具单件探针（实验）」开关，默认关闭。
          - **真机单件通过**：隔离 `build/probe_furniture_single.evo` 走
            FurnitureTool → `aid_DrawPoint` 临时创建 → Cuboid 尺寸 → `PositionVectorControl_X/Y/Z`
            回写 → 保存；拆包 `ProjectData.dat` 得 `FurnitureElement=1`、对象名
            `PROBE_FURNITURE_1`、`CoordSys3D=(2.0,1.5,0.0)`，尺寸 UIA 写入 `2.0×1.0×0.75m`。
          - 识别/任务/全仓门禁：**237 passed + ruff 0**；批量 22 件、重开工程、三维误差扫描仍待验收。
          - 审查意见：单件闭环证据成立；下一步先在隔离副本重开验证，再扩 22 件，不能把单件通过写成
            MVP3 家具全量完成。
- [ ] MVP3 backlog（来自 MVP2 审查）：
  - IR schema 加显式 `kind: "furniture"`，让 parser 声明家具、exporter 不再靠 name 前缀猜（M3）
  - `--validate` 目前刻意摘掉 luminaires（STF 不导灯具，不该被灯具规则挡住）；MVP3 导灯具时要把
    灯具一起校验，见 `_validate_rooms` docstring（M-new-1）
  - 自交多边形（bowtie）无检测：|面积| 非零就放过；validator 也没这条规则
- [ ] MVP4：计算 + 报告抽取｜自动计算，抽照度/功率密度
- [ ] MVP5：视觉自愈 + 异常处理｜弹窗识别、重试、日志

## 需求 ID 溯源

2026-09-03 建。代码与测试注释里有 37 处 `AC-*/TR-*/FR-*` 引用（`tests/` 里 34 处，`src/planner/core.py`、
`src/planner/join.py`、`scripts/render_preview_svg.py` 各 1 处），
但编号定义源不在 git 权威层，且编号空间被复用：

| 编号族 | 定义在哪 | 状态 |
|---|---|---|
| MVP1 `AC-1`~`AC-10`、`FR-*`、`NFR-*` | `.trae/specs/dialux-compiler-mvp1/spec.md` | ⚠️ 该目录被 `.gitignore` 忽略，**不在 git 里** |
| MVP1 `Task 1`~`9`、`TR-1.1`~`TR-7.4` | `.trae/specs/dialux-compiler-mvp1/tasks.md` | ⚠️ 同上 |
| 「柜子变墙」验收 | `prompts/parser_furniture_fix_task.md`（tracked） | 只有散文验收标准，**没有 AC 编号** |

**冲突**：`tests/test_real_dxf.py` 为柜子变墙修复自造了第二套 `AC-1`~`AC-6`/`AC-8`，与 MVP1 spec
（`.trae/specs/dialux-compiler-mvp1/spec.md`）的同名编号含义完全不同。两种情况要分开看
（行号为 2026-09-03 实测）：

- **同一文件内双义**（只有 `AC-2`、`AC-3` 两个编号在 `tests/test_real_dxf.py` 里各有两种含义；
  `AC-2` 字面命中共 4 处（`:1`、`:93` 是 MVP1 义的同义复述），`AC-3` 字面命中 2 处）：
  - `AC-2`＝MVP1「主房间面积 ∈ [73,136] m²」(`test_real_dxf.py:86`)　vs　柜子变墙「北墙 y=8.05 是一条边」(:158)
  - `AC-3`＝MVP1「validator 无 HALT」(:106)　vs　柜子变墙「四面墙锯齿全消」(:180)
- **跨文件同号不同义**（`AC-1`/`AC-4`/`AC-5`/`AC-6`/`AC-8`）：这五个在 `tests/test_real_dxf.py` 里
  **各只出现一次**（AC-1:140、AC-4:201、AC-5:216、AC-6:229、AC-8:118，全是柜子变墙义），
  它们的 MVP1 义只在 `spec.md`（AC-1:154、AC-4:178、AC-5:186、AC-6:194、AC-8:213）——
  两义分居两个文件，单看测试文件不会撞车，跨文件引用才会。

约定（立即生效）：引用 AC-N 必须写清出处，例如 `AC-2(MVP1)` / `AC-2(柜子变墙)`。
彻底修法见下方待决项。

## 遗留与待决

2026-09-03 实核。以下都需要架构师裁决，worker 不自行处置。

- [ ] **验收标准与验收证据两头都在 git 外（当前最高工程风险）**：`.trae/` 被 `.gitignore` 末行的
      `.trae/` 规则忽略（2026-09-03 实测：`.gitignore` 全文 44 行，该规则在第 44 行；行号随注释
      增删漂移，引用以规则内容为准，别钉行号），
      而 `.trae/specs/dialux-compiler-mvp1/`（约 45 KB）是 MVP1 全部 AC/FR/NFR/TR 的**唯一定义源**，
      clone 或换机即丢；`build/` 同样全量忽略，本文件引用的产物证据也不在库里。
      两个处置选项，二选一由你定：(A) 把 `.trae/specs/` 纳入版本控制（改 `.gitignore` 白名单）；
      (B) 迁进 `spec/`（如 `spec/mvp1-acceptance.md`）并让 `.trae/` 保持忽略。
      另需单独决定关键产物快照是否入库。
- [x] **ruff 门禁失真｜2026-09-04 关闭**：81 条已全清（治理口径见「门禁实测」），
      未放宽任何配置、未改 `.gitignore` 忽略面 → MVP1 spec 的
      `AC-8「pytest 全绿 + ruff clean」` 现在**成立**。原来摆的三个选项
      （派单清 / 写 ruff 配置 / 撤 AC-8 条款）里走的是第一条。
      **遗留**：`requirements.txt` 仍未锁 ruff 版本，升级到新规则集可能重新出错 —— 这条待你定。
- [x] **铁律与实际执行不一致（治理）｜2026-09-05 随体系换代关闭**：原缝隙是「现行铁律只堵
      Hermes gateway 子 agent，没堵住顶层会话 + 同名 profile」，2026-09-02 的 MVP2 两张卡
      （t_7c5dc714 / t_0deee369）实际由 Hermes 顶层会话执行，只把审查转包给
      `claude --agent code-reviewer`。**架构师 2026-09-05 口头定案停用 Hermes 与 claude 子员工，
      改为 DSH 桌面版直接执行**，「执行者必须是 claude 子员工」这条铁律已从 `AGENTS.md` 删除
      → 原本要在选项 A（收紧）与 B（放宽留痕）之间做的选择**自然失效**，无需再决。
      新铁律见 `AGENTS.md`「铁律」第 1 条；沿革见 `docs/agent-spec.md`。
- [x] **DWG 直读崩溃｜2026-09-04 修复**：`src/main.py:82-85` 的 else 分支改为
      `lum_dwg_path = dwg_path`（复用上游已转换的 DXF），与 help 文本一致，不再抛
      `OSError: not a DXF file`。2026-09-05 代码实核确认。**遗留**：仍无专门覆盖
      「只给 `--dwg`」这条 CLI 路径的回归测试（`tests/test_smoke.py:11` 喂的是 .dxf）。
- [x] **`_meta.luminaires` 聚合计数｜2026-09-04 修复**：`src/planner/join.py:56-63` 在
      `join_luminaires` 末尾按 `storeys[*].spaces[*].luminaires` 求和回填 `_meta.luminaires`，
      `tests/test_smoke.py:30` 有断言覆盖。
      ⚠ **现存产物 `build/room_layout.json` 是 2026-09-02 的旧文件**，实测仍是
      `_meta.luminaires = 0` 而房间上挂着 28 盏 —— 这是产物过期，不是代码缺陷；重跑 pipeline 即一致。
- [x] **`catalog_match` 保持现状 2026-09-07（架构师定）**：字段是解析期占位（join.py 硬编码 True），
      不接受改名/删除；MVP3「型号匹配」验收不拿这 28 个 true 当已匹配证据（真实比对是后续）。
      spec/ir-schema.md 已注明该字段为占位语义。
- [ ] **校验规则 6 零调用者 + docstring 陈旧**：规则 6（灯具 params 与 xlsx 一致）只存在于
      `src/validator/__init__.py:172` 的 `validate_with_luminaire_xlsx`，全仓**没有任何调用者**；
      而 `validate_ir` 的 docstring 仍写「6 条业务规则」，实际只 extend 规则 1~5。
      待你定：MVP3 接上调用，还是把规则 6 从「校验规则」降级为可选工具函数并同步 docstring。
- [x] **退役工具引用已清 2026-09-06**（架构师确认「没用的就删了」）：`prompts/` 4 份退役文档
       （`trae-work.md` / `dispatch_fix_parse_config_test.md` / `mvp2_stf_exporter_task.md` /
       `parser_furniture_fix_task.md`）已删除；`test_project_hygiene.py::test_prompts_three_modes_sections`
       改为断言「退役文档应不存在」——原断言钉死 trae-work.md 必须存在，与换代事实打脸。
       TR-7.3/7.4 此前已改为断言现役体系（DSH / deepseek-v4-flash）与结构约束。
- [ ] **AC 编号去重**：`tests/test_real_dxf.py` 里第二套 AC 编号需重命名（属 `tests/`，
      DSH 会话可直接改，不再需要派单）。
- [x] **派单前置｜2026-09-05 随体系换代关闭**：原问题是「`dispatch_claude.sh` 派单前是否
      必须先启动 cc-switch」在文档与脚本注释里都零处提及。**派单体系已停用**（改 DSH 直接执行），
      该前置不复存在，`AGENTS.md` 的派单式已随换代删除。
- [ ] **spec 双文件同步靠人工**：`spec/ir.schema.json` 是运行时唯一被加载的权威定义，
      `spec/ir-schema.md` 是导读，两份逐字段同步目前没有自动化，也没有测试守。
      待你定：加一条「md 示例必须能通过 json schema 校验」的测试，还是接受人工同步。
- [ ] **文档并发改写无协调机制（2026-09-03 事故记述）**：当天三个互不知情的收尾会话并发改同一批
      7 个未提交文档（`.gitignore`、`AGENTS.md`、`KANBAN.md`、`README.md`、`docs/agent-spec.md`、
      `prompts/trae-work.md`、`spec/ir-schema.md`），同一事实一度出现三种口径（主房间顶点数、
      `.gitignore` 改动的交付范围、AC 编号两义的范围），最后靠人工审计逐条对齐。
      过程证据在会话记录里，不在本仓库，无法用 git 自证。现有防线只有 `AGENTS.md` 开发流程第 0 步
      （动手前跑 `git status`，工作区有别人未提交改动就停下问架构师）。
      待你定：是否要更硬的机制（文档改动也走看板卡，或同一时间只放一个文档会话）。

- [x] **良性并发实例 2026-09-08**：DSH 桌面版分支对话（与主对话互不知情）并发完成
  「家具/评估区/计算三通道真机探针 + standard-dialux-run v2」（commit d1a7b34），
  只动 SOP 文档 + KANBAN 第 17 点 + `build/probe_20260907_channels.txt`，与主对话改动错开，
  门禁 231 全绿无冲突。验证：动前 git status + 已提交状态 = 并发安全的最低保障。
  注意：git 作者名原为 Trae 时期残留 `Trae Work <traework@local>`（历史提交保留不改），
  2026-09-08 已改为 `cjh <cjh@local>`（仓库级），未来提交署名 cjh。
## 审查记录

- **2026-09-06 neat-freak（DSH）：知识收尾第三轮**，基线提交 `ca69fc9`（本轮改动未提交）。
  消除的失同步：
  1. **推翻「家具/灯具 AutomationId 全部 MISSING」的旧结论**：P3 条目第一条障碍
     （切不到家具页）已因发现导航层 `MenuGotoConstructionMode` 而解除；灯具布置工具、
     布置原语、目录按钮全部实测定位（详见「MVP3 待办」更新条目）。这是本轮最重要的
     事实修正——旧结论会让下一位接手者误以为家具/灯具通道不可行。
  2. **灯具库实核补新事实**：装机自带 0 个光度文件（旧记录「全盘 0 个」不精确——
     本机 `Documents\Zemax\Objects\Sources\` 下有 1 个 `.ldt` + 4 个 `.ies` 可作
     离线导入测试素材）；`ImportLuminaire` 菜单实测存在且 `en=True`，类型过滤器
     明确收 `*.uld;*.gldf;*.ldt;*.ies;*.cib;*.ltl`；但确认按钮 `BM_CLICK` 无效，
     记入「唯一硬钉子」。
  3. **桌面操控选型同步**：`AGENTS.md` / `README.md` 技术栈表从
     「`dsh-computer-use-win` 插件」改为「自研 `src/executor/uia/`」——插件仅是可选
     OCR 后端，真机验证过的驱动是我们自己的 `dialux_driver.ps1`。
  4. **试用期口径同步**：`AGENTS.md` 原文「试用期剩 3 天」与 KANBAN 已更正的
     「9 项 Pro 附加功能 2026-09-08 到期、主路径不受影响」矛盾 → 已改写为指向 KANBAN。
  5. **新计划文档入册**：`docs/plan-mvp3-luminaire.md`（灯具通道 P0/P1/P2 计划 +
     实测地形图 + 风险表），KANBAN MVP3 主路径条目引用之。
  遗留（沿用，未新增）：`prompts/` 4 份退役文档仍为删除候选，**未经架构师确认未删**；
  `requirements.txt` 仍未锁 ruff 版本；`catalog_match` 硬编码 `True` 语义未定；
  `ImportLuminaire` 对话框确认机制未通（P0，三种手段待试）。
- **2026-09-05 neat-freak（DSH）：知识收尾第二轮**，基线提交 `ca69fc9`（本轮改动未提交）。
  消除的失同步：
  1. 「门禁实测」lint 数字从过期的 **81 errors 改成实测 0 errors**（同一文件里原本存在
     81 与 0 两个矛盾数字，而顶部自称唯一权威）；`--no-respect-gitignore` 从记载的
     「225 条」重测为 **8 条且全部来自 `better-genshin-impact/` 参考项目**，本仓自有代码两口径均 0。
  2. **协作体系换代入档**：架构师 2026-09-05 口头定案停用 Hermes + claude 子员工 + cc-switch，
     改 DSH 桌面版直接执行 + deepseek-v4-flash。改写 `AGENTS.md`（工具分工表 / 开发流程 /
     铁律第 1 条 / 成本与配置）、`README.md`（技术栈表前三行）、`docs/agent-spec.md`
     （70 行整篇过期 → 缩成「权限边界 + 沿革」，不再维护第二份协作规范）。
  3. **两条测试原本把废弃体系钉死**：TR-7.3 断言 AGENTS.md 必须含「claude 子员工」、
     TR-7.4 断言 agent-spec.md 必须含「Hermes」。改为断言现役体系与结构约束
     （非删除、非放宽），见 `tests/test_project_hygiene.py`。
  4. 「现役实现边界」三条从「09-03 快照 + 注记」改写成现役答案（旧断言压成一行历史对照），
     `README.md` 技术栈表同步（STF 灯具段已开 / ODA 路径走 `src/core/env.py` / `--dwg` 不再崩）。
  5. 关闭 5 条已消除的遗留：铁律与实际执行不一致（随换代自然失效）、DWG 直读崩溃、
     `_meta.luminaires` 恒 0、ruff 门禁失真（AC-8 现在成立）、派单前置未定。
  6. MVP2 从「待验收」转「几何回环已验收」，证据链见 MVP2 章节；新增
     「computer use 通道」与「家具库 / 灯具库实核」两节固化真机实证。
  收尾后继续开发的结论：**STF 灯具段真机判定为「此路不通」**（DIALux 完全忽略 `NrLums`/`Lum{i}`，
  0 灯落地，证据链见「MVP3 待办」首条）→ MVP3 灯具落地正式改走 computer use 通道，
  同时暴露两个 IR 侧缺陷（灯具 z 全为 0、16 筒灯 + 12 线性灯未分类）已转新待办。
  遗留：`prompts/` 4 份退役文档是删除候选，**未经架构师确认未删**；`requirements.txt`
  仍未锁 ruff 版本；DIALux 试用期剩 3 天（**2026-09-05 已更正：只影响 9 项 Pro 附加功能，
  不影响 STF 导入 / 建模 / 存 `.evo`，口径见「家具库 / 灯具库实核」节**）。
- 2026-09-03 neat-freak（DSH）：知识收尾，基线提交 76b6bf4。结论：「门禁实测 / 现役几何口径 /
  现役实现边界 / 遗留与待决」四节为权威口径，其余文档只放指针；MVP2 维持「待验收」；
  遗留待决 12 条待你裁决，见上。
- 2026-09-01 neat-freak（Alice）：MVP1 通过（带 1 条测试壳编码遗留，已转 MVP2 P0 修复单）；agent-spec 勘误补齐
- 2026-09-02 code-reviewer（claude 子员工）审 t_7c5dc714「IR → STF 生成器」，两轮：
  - 第一轮：2 CRITICAL + 3 HIGH + 5 MEDIUM + 11 LOW
  - 第二轮复核结论：**「可以交付给架构师做 evo 真机验收」，0 新增 CRITICAL/HIGH**；另提 3 MEDIUM，已全修
  - 已修（代码/测试）：C2 绕向不再静默（默认保留 IR 原序 + 打日志，新增 `--ccw`）；
    H1 `project`/`id` 非法路径改抛 ValueError（含 unhashable id）；H2 新增 `--ceil-h` 让
    `--include-furniture` 真能用；H3 补 `-0.0`/零长边/NaN/大数/绕向等断言；
    M1 多楼层与非零 elevation 出 WARNING；M2 新增 `--validate` 复用 `src.validator`；
    M3 id 兜底加「无 ceil_h 且无 furniture 键」门槛 + 日志打 `name（id）`；M4 BOM/GBK/目标是目录 → exit 2；
    M5 README/architecture/KANBAN 同步；
    M-new-1 `--validate` 摘掉 luminaires（STF 不导灯具，灯具规则不该挡几何导出，已转 MVP3 backlog）；
    M-new-2 修掉 unhashable-id 假绿测试（改成落在真实分支 + 直接单测 `is_furniture_space`）；
    M-new-3 补 elevation 专属正/负向断言；
    LOW 1/2/3/5/6/8/9/10/11 顺手清（拆 `_parse_polygon`、错误消息区分类型/空值/NaN、`Prepared` 别名上移、
    `_resolve_project_name` 去重复、金文件用常量插值、跳过日志带名字、补「入参不被修改」测试）
  - 测试：22 → 70 条（tests/test_exporter_stf.py），全仓 pytest 102 全绿（原 32 未回归）
  - **遗留（唯一阻塞项）**：C1 闭合形态 + C2 CW 绕向需真机 evo 14.0 导入验证，代码层无法自证；
    4 种组合文件已预生成在 build/，验收结论回填 `src/exporter/stf.py` docstring 后 MVP2 才算 done
</content>

## 2026-09-04 git-project-analyzer 分析改进

基于两个参考项目（Mrite / BetterGI）的 `git-project-analyzer` 深度分析，以下改动已完成：

### 已完成的低成本项

- [x] `.gitignore`：加 Mrite/ / better-genshin-impact/ / git-project-analyzer/ / analysis-reports/（参考项目与分析产物不进版本控制）
- [x] `src/main.py:72-84` DWG 崩溃修复：只给 `--dwg` 不给 `--dwg-lighting` 时不再崩——改为复用已转换的 DXF（与 help 承诺一致）
- [x] `src/planner/join.py` `_meta.luminaires` 聚合计数回填（join_luminaires 末尾统计并写入 _meta）
- [x] `src/exporter/stf.py` 灯具段导出（MVP3 exporter 侧前置）：从 IR space["luminaires"] 读数据写 NrLums + Lum{i}=X Y Z symbol 段；格式暂为占位实现，待 evo 真机验证
- [x] `src/core/env.py` 运行时路径归一化（ODA/DIALux/OCR）：学 Mrite PATH 治理思路，统一入口 get_oda_path()，替代 dwg_to_dxf.py 里 DEFAULT_ODA 写死
- [x] `scripts/dwg_to_dxf.py`：改用 src.core.env.get_oda_path()，保留 resolve_oda_path() 兼容旧调用
- [x] `AGENTS.md`：新增"代码审查铁律"（学 BetterGI AGENTS.md 审查优先级清单）
- [x] ruff 81 → **0 errors**：集中治理 E702/E701/E741/E731/F401/F841/F541（不改 .gitignore 口径）
- [x] pytest：**147 passed / 0 failed**
- [x] 分析报告：analysis-reports/mrite/better-genshin-impact/dialux-compiler/APPLICATION-NOTES.md 已就位

### 未做（明确排除）
- executor 真动作：KeyMouseExecutor._locate_control 仍恒返 None（留给 MVP3.5 按 BetterGI 模式设计：输入模拟分档 + ISoloTask 调度 + 进程生命周期管理）
- KANBAN「遗留与待决」的 12 条架构师决策：本轮不碰
- spec/ir.schema.json 不变：是宪法

## 2026-09-10 复刻标本日志蒸馏（DSH neat-freak）

- GPT-6/Codex 09-10 会话「复刻现有功能」的完整 rollout 日志（44 MB，124 次工具调用）已定位并蒸馏：
  `build/reproduction_20260910/` 下 `codex_复刻执行清单.md`（9 阶段流水线 + 全部命令）与 `codex_完整对话记录.md`（git 忽略区）。
- 该标本揭示一条绕开 C2 画房间 / A1 内置目录家具的替代路线（STF 建壳 + 3DS 家具导入 + 阵列布灯 + 直改 .evo 校正），真机含家具计算跑通。
  详见 `docs/plan-from-scratch-modeling.md` 附B-1；生产代码本轮零改动。
- 结论：后续复刻用 DSH + deepseek-v4-flash 照清单执行即可，无需 GPT-6（会话中途已切 GPT-5 续跑成功，流水线本身是资产）。
