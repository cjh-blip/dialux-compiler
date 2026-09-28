# DIALux 运行标准流程 — Agent 可执行版

> 版本：v1（2026-09-07）| 用途：供 computer use agent 自动化执行 DIALux evo 建模与布灯
> 参考：既有手动操作 SOP `DIALux_evo_操作SOP_Agent可执行版.md`（人/agent 手动版）+
> 本项目已验证的真实链路（解析器 + STF 批量导入 + UIA 驱动）
> 区别：手动 SOP 是「在 DIALux 里手动描点」，本流程是「解析器自动建模 + UIA 自动驱动」

## 一句话

从 DWG 图纸到 DIALux 里建好房间、布好灯、算出桌面照度的一条自动流水线：
**解析 → STF 导入 → 布灯 → 家具 → 桌面评估区 → 计算 → 读结果**，
建壳+布灯由 `demo_run.py --luminaires auto` 一键完成；家具/评估/计算是新探明的
UIA 通道（2026-09-07 真机探针，见 `build/probe_20260907_channels.txt`），实现中。

## 流程总览

```
启动 DIALux（launcher 可自动开）
  │
  ├─ Step 1: 解析 DWG → IR（src/main.py，自动，非 DIALux 内操作）
  ├─ Step 2: IR → STF 房间壳（src.exporter.stf，自动）
  ├─ Step 3: STF 批量导入 DIALux 建房间（UIA：菜单 → 文件对话框 → 确认）
  ├─ Step 4: 导入灯具型号（IES，会员厂商）→ 切工具 → 选原型
  ├─ Step 5: ArrangementFromSpace 自动排布（两批：筒灯 + 线性灯）
  ├─ Step 6: 家具建模（Cuboid 积木 / DrawExtrusionFurniture 拉伸，桌轮廓来自 IR）
  ├─ Step 7: 桌面评估区（工作面高度 0.75m，家具位置驱动）
  ├─ Step 8: 运行计算（CalculationButtonStart）
  └─ Step 9: 读结果（照度/均匀度/UGR；拆包或 PDF，探路中）
```

## 分步操作

### Step 1: 解析 DWG → IR

**[执行]** `python scripts/demo_run.py`（或 launcher 点启动，内部跑同链路）

**[操作]**
1. 解析器读 `布局图.dwg`（房间）+ `灯具图.dwg`（灯具）
2. 自动抽房间轮廓、家具轮廓（22 件，数据层）、灯具（28 盏）

**[参数]**
- 图纸：`布局图.dwg` / `灯具图.dwg`（exe 版放 exe 同目录）
- 解析配置：`tests/fixtures/sample_parse_config.json`

**[验证]**
- `build/demo_ir.json` 生成，`_meta` 显示 rooms=1 furniture=22 luminaires=28

### Step 2: IR → STF 房间壳

**[执行]** `python -m src.exporter.stf --validate build/demo_ir.json build/demo_room.stf`

**[操作]**
- 房间几何（多边形顶点）→ STF `[ROOM.Rn]` 段
- 家具伪 space（name 以「家具_」开头）默认跳过，不建假房间

**[验证]**
- `build/demo_room.stf` 生成；日志「1 个房间，共 17 个顶点」

### Step 3: STF 批量导入 DIALux 建房间

**[执行]** UIA 驱动（`src/executor/uia/driver.py::run_import`）

**[操作]**
1. 挂到 DIALux 进程（HwndWrapper[DIALux_x64]）
2. 菜单 文件 → 导入 → STF
3. 文件对话框：SetWindowText 填路径 → BM_CLICK 确认（对话框对 UIA 不暴露 pattern，走 Win32）
4. 等 DIALux 重建场景 → 保存 .evo

**[验证]**
- 日志 STEP 全 OK；DIALux 标题回到工程名
- `.evo` 拆包：`Project/ProjectData/ProjectData.dat` 有房间（灯具不在这，见 Step 6）

### Step 4: 导入灯具型号

**[执行]** `src/executor/uia/luminaire.ps1`（ImportLuminaire 通道）

**[操作]**
1. 菜单 文件 → 导入 → 灯具（ImportLuminaire）
2. 文件对话框：按文件名找 ListItem → `SelectionItemPattern.Select()` → `InvokePattern.Invoke()`
   （双击语义；`BM_CLICK` 对 IFileDialog 无效）
3. 检查 paywall：出现 `ButtonBuyNow` = 非会员厂商被挡 → 换合规文件

**[参数 — 关键约束]**
- **IES/LDT 第 1 行厂商名必须是 DIAL 会员**（本机 `ManufacturerMatchingRules.xml` 449 家）
- 非会员（如 ZEMAX/自造名）→ 「解锁非会员」付费墙，0 灯具落地
- 已验证合规：`build/ies/fixed/NPTLED351_NVC.IES`（NVC）、
  `build/ies/linear/opple_LEDPanelRc-S-Re295-30W-4000-WH-U19.ies`（OPPLE）

**[验证]**
- 无 paywall；`CatalogListBox` 出现该型号

### Step 5: 自动排布（ArrangementFromSpace）

**[执行]** `luminaire.ps1` 继续（切工具 → 选原型 → 排布）

**[操作]**
1. 切到灯具布置工具（MenuGotoConstructionMode → MenuGotoShowLuminaireArrangementTool）
2. 打开灯具目录（LuminaireCatalogButton）→ `CatalogListBox` 选中目标型号
   （**厂商前缀坑**：文件名 `opple_LEDPanelRc-...` 匹配条目 `LEDPanelRc-...`，脚本已处理）
3. `aid_ArrangementFromSpace` Invoke 一次 → 自动按空间排布

**[⚠️ 已知坑]**
- **只 Invoke 一次**：重复触发会叠多套排布（曾叠到 7 套/88 盏）
- 排布是 DIALux 自动网格（非图纸毫米级原位）——落位口径已定「自动排布」
- `ElementCountX/Y` 可改但重触发会被 DIALux 重算回默认（4×3）

**[验证]**
- `ArrangementObjectName` 显示如「20 x Opple LEDPanelRc-S-Re295...」

### Step 6: 保存 + 拆包验收

**[执行]** luminaire.ps1 自动保存 + agent 拆包

**[操作]**
1. Save（`autosave.ps1` 自动应答「保存确认弹窗」：Yes/No + Edit 特征 → 点「是」）
2. `.evo` 是 zip → 解 `Project/ProjectData/ProjectData.dat`（ISO 10303-21 STEP 文本）

**[验证 — 关键事实]**
- 灯具在 `ProjectData.dat`，**不是** `ScenegraphScene`
- `LuminaireElement` = 灯具数 × 2（每盏 2 个引用）；`PrototypeDefinitionData` = 原型数
- 两批灯：NVC NPTLED 12 盏（4×3）+ OPPLE Re295 20 盏（4×5）= 32 盏，产品 {NVC, OPPLE}

### Step 7: 家具建模（2026-09-08 单件闭环已通，批量实现中）

**[需求]** 图纸中的图案 = 桌子；需求是**算桌面照度**，所以家具是评估区的前置
（决定评估区位置与工作面高度），不是视觉增强。

**[执行]** UIA：`MenuGotoShowFurnitureTool`（家具与物件 (O)）
- 首件路线：`aid_DrawPoint` 创建一个选中的 Cuboid，再写 `CuboidWidth/Length/Height`
  三边 Edit（可写）→ 写 `PositionVectorControl_X/Y/Z`、`RotationVectorControl_*` 和对象名
- 后续精确几何：`aid_DrawExtrusionFurniture`（拉伸物件）——用 IR 家具轮廓多边形拉伸成立体
- 桌轮廓来源：IR 22 件家具（`build/mvp3_ir.json`，polygon 多边形）

**[⚠️ 已知]**
- `aid_DrawPoint` 的屏幕点击只负责创建临时选中对象，不承担世界坐标精度；对象创建后
  `PositionVectorControl_X/Y/Z` 数值控件出现，精确坐标通过 UIA 回写
- 家具工具需先选空间（`ToolPartNoSpace` 提示「未选择空间」才可用）
- **「家具=空间」路线 2026-09-08 最终判死（架构师看图确认）**：UIA ListItem 双击导入
  确实成功（Space=23、LINEARC_* 全在 probe_furniture.evo），但架构师 3D 视图发现
  **三重缺陷**：① 22 件家具各成一栋**独立建筑物**（STF 语义 ROOM=建筑，非家具对象）；
  ② 拆包 CoordSys3D 原点分布证实**家具建筑全堆在 (0,0)**——STF 绝对坐标被 DIALux
  当作每栋建筑的相对坐标，图纸位置丢失（灯具不受影响：后导入走房间内排布，坐标正确）；
  ③ 中文名「家具_」乱码成「溜踩佂」。→ 家具正确路线：FurnitureTool 家具对象
  （Cuboid 尺寸可写）或直写 .evo（在正确建筑内插 Furniture 实体，待验证）。
  **教训**：STF 多 ROOM 段 ≠ 多空间同建筑；导入成功 ≠ 位置正确，必须 3D 视图人眼验收。

**[验证]**
- 单件真机：`build/probe_furniture_single.evo`，UIA 完成 FurnitureTool → Cuboid 尺寸 →
  `aid_DrawPoint` → PositionVector 回写 → Save。
- `.evo` 拆包 `Project/ProjectData/ProjectData.dat`：`FurnitureElement=1`，对象名
  `PROBE_FURNITURE_1`，`CoordSys3D=(2.0,1.5,0.0)`；UIA 写入尺寸为 `2.0×1.0×0.75m`。
- 证据截图：`build/furniture_saved_screen.png`。批量 22 件、重开工程和三维误差扫描仍待做。

### Step 8: 桌面评估区/工作面（探通入口，实现中）

**[需求]** 每张桌子一个评估区，工作面高度 = 桌面（SOP：会议桌 0.75m / 办公桌 0.85m）。

**[执行]** UIA：`MenuGotoShowSpaceTool`（工作面 (S) = 评估区/工作面）
- 先选中房间（`WorkspaceSelectionComboBox` / 项目树）
- 再建评估区（`aid_AdjustSpaceToWalls` 等，en 依赖已选空间）

**[验证]**
- 评估区出现在项目树；工作面高度属性 = 桌面高度

### Step 9: 运行计算（✅ 2026-09-08 真机验证）

**[执行]** UIA：`CalculationButtonStart` Invoke → 轮询 `CalculationCommandText`
（计算中变「取消」，变回「计算」= 完成；32 盏灯实测 <1 分钟）

**[验证 — 真机证据]**
- 点击后标题出现 `*`、出现「计算进度」面板
- 完成后 `Results/Group_*/Dataillumqt0.rsl`（照度网格 1-2MB）落盘

### Step 9.5: 计算元件/评估区工具（2026-09-08 探明）

**[工具]** `MenuGotoShowCalculationObjectTool`（计算元件 (C)）——评估区正确入口：
- `aid_NewRectCalculationObject`（矩形）/ `aid_NewPolygonalCalculationObject`（多边形）/
  `aid_NewPointCalculationObject`（单点）——三种计算元件，**均为画布绘制语义**
- 子 Tab：`WorkplaneTool`（工作面）/ `TaskAreaTool`（作业区）/ `ActivityAreaTool`（活动区）
- `HeightOffset_PerpendicularIllum`（高度偏移）+ `GridPointCountX/Y` / `GridPointDistanceX/Y`
  （网格密度，选中元件后启用）
- **无坐标输入框**：桌面精确评估区 = 画布点击（唯一剩余脆点）或直写 .evo（待验证）

**[已有结果的含义]** 实测读数是 DIALux 默认评估面（房间级）产出——「算出照度」
不依赖手动评估区；桌面精确照度才需要自建计算元件。

### Step 10: 读结果（✅ 2026-09-08 真机验证 — UIA 直读，无需解析二进制）

**[执行]** ResultsMonitor 工具（计算后激活）：
- `ResultsMonitorSurfaceResultAverage` = 平均照度（实测读出）
- `ResultsMonitorSurfaceUniformityAverage` = 均匀度（实测）
- `ResultsMonitorList` = 逐面结果列表

**[对照验收]** 目标 ≥750lx ✓（照度超标因自动排布偏密）；均匀度不达标 ✗
（自动网格排布的固有均匀性问题，不是读数问题——精调布灯后复算）

**[⚠️ 备选]** 结果也在 `Project/Results/Group_*/Dataillumqt0.rsl`（boost 序列化二进制，
可扫 float 网格 10~20000lx），但 UIA 直读足够，不必解析。

## 一键执行

```bash
# 源码版（DIALux 开着时）
python scripts/demo_run.py --luminaires auto          # 建壳 + 放两批灯（已验证）
# （家具→评估区→计算：实现中，接好后并入 demo_run 或 Flow 一条龙）

# exe 版（图纸/config/ies 放 exe 同目录）
demo_run.exe --dwg 布局图.dwg --dwg-lighting 灯具图.dwg \
    --config sample_parse_config.json --luminaires auto

# GUI 启动器（推荐）：双击 launcher.exe → 勾「同时启动 DIALux」→ 启动
# 悬浮窗（overlay.py）实时显示每步：解析→STF→导入→布灯→家具→评估→计算→保存
```

## 与手动 SOP 的映射

| 手动 SOP | 本流程（自动） |
|---|---|
| Step 2 导入 DWG 做底图 | 解析器直接抽 IR，不导入 DIALux |
| Step 3.1-3.3 多边形工具描房间 | STF 批量导入（坐标来自 DWG 精确提取） |
| Step 3.5 阶梯座位 / Step 4 门窗 | ❌ 未做（剧院场景才需要） |
| Step 5 材质/反射率 | ⚠️ 待做（SOP 默认值：天棚0.75/墙0.5/地0.2，随计算一起） |
| Step 6.1-6.2 灯具目录/放置 | ✅ 自动（IES 导入 + ArrangementFromSpace） |
| Step 6.3 灯光场景 | ❌ 未做（调光/分区） |
| **家具建模（需求方新增）** | **🔄 探通（Cuboid 可写 + DrawExtrusionFurniture 拉伸，桌面轮廓来自 IR）** |
| Step 7 评估区/工作面/计算 | **🔄 入口确认（SpaceTool 工作面 + CalculationButtonStart；评估区按桌面 0.75m）** |
| Step 8 结果/报表 | ⚠️ 待定（拆包 ProjectData vs 报表 PDF 抽取，选路中） |

## 版本记录

- v2（2026-09-07）：补家具建模 + 桌面评估区 + 计算三通道（真机探针
  `build/probe_20260907_channels.txt`）；家具从「视觉增强」升为「评估区前置」
- v1（2026-09-07）：定案，基于真机验证链路（放灯产品化 + exe 交付后）
