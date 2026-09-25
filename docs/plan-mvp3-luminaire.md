# MVP3 计划：把灯具真正放进 DIALux

> 六步链第 ④ 步产物 | 2026-09-06 上午定案 | 执行层遵循 karpathy-guidelines
> 前置：① 素材已做（真机实测，见下）；② grill 已定案 4 条；③ 三省未走（没到难以决断的程度）

## 零、这份计划要解决的那一件事

现在的交付物只有房间壳。**28 个灯具解析出来了、算出高度了、进了 IR、也进了 ActionPlan，
但一个都没进 DIALux。** 原因早已查明：STF 的灯具段被 DIALux evo 14 完全忽略
（实测灯具坐标 0/8 命中，同一次扫描房间顶点 4/4 命中，对照组证明扫描法有效）。
所以灯具只能走 computer use 通道。这份计划就是把那条通道打通。

## 一、①素材：真机实测拿到的地形图（2026-09-06）

### 1.1 找到了之前一直没找到的「导航层」

之前我判断「家具/灯具的 AutomationId 全部 MISSING、这条路走不通」——**那个判断是错的**。
它们不是不存在，是**没被激活的工具页不会出现在 UIA 树里**。入口在顶层菜单「切换到」
（`MenuGotoConstructionMode`），展开后 14 个 `MenuItem` 全部 `Invoke` 可用：

| AutomationId | 用途 |
| --- | --- |
| `MenuGotoShowLuminaireArrangementTool` | **灯具布置工具**（本计划主入口） |
| `MenuGotoShowLuminaireCatalogPopup` | 灯具目录弹窗 |
| `MenuGotoShowFurnitureTool` | 家具工具（P3 用） |
| `MenuGotoShowCalculationObjectTool` | 计算对象（工作面） |
| `MenuGotoShowSpaceTool` / `…StoreyTool` / `…MaterialTool` / `…ProjectTreeTool` 等 | 其余工具页 |

激活灯具布置工具后，工具页整批换成 `Lighting.*` / `Luminaires.*` 系列：
`LuminaireArrangementTool`、`LampTool`、`LightSceneTool`、`FilterTool`、
`MaintenanceFactorTool`、`EnergyPerformanceTool`、`EmergencyLightingLuminaireArrangementTool`。

### 1.2 布置原语齐全，但全部灰着

灯具布置工具激活后出现这批按钮，**都支持 `Invoke`，但 `IsEnabled=False`**：

| AutomationId | 语义 | 对应我们的数据 |
| --- | --- | --- |
| `aid_DrawPoint` | 放单个灯具 | 16 个 `kind=point` 筒灯 |
| `aid_DrawLine` | 放一条灯带 | 12 个 `kind=linear` 线形灯 |
| `aid_ArrangementFromSpace` | 按房间自动排网格 | 兜底方案 |
| `aid_DrawRectangle` / `Polygon` / `Circle` | 区域排布 | 暂不用 |
| `aid_StartChangePrototypeSelected` / `…All` | 换型号 | 暂不用 |

灰的原因很明确：**没有「当前灯具型号」（prototype）**。目录里空的，就没东西可放。

### 1.3 目录按钮是 Toggle 不是 Invoke

`LuminaireCatalogButton`、`BrandCatalogButton` 支持的是 `TogglePattern`
（我第一次按 `Invoke` 调，报「不支持的模式」）。Toggle 开之后主窗口后代数
269 → 302，出现 `CatalogListBox`（`Selection` + `ItemContainer`），
但 **children = 0**——它是「本项目已用灯具」列表，新项目里本来就是空的。

### 1.4 DIALux 装机自带零个灯具

全盘扫过：安装目录里 `*.ldt / *.ies / *.uld / *.gldf / *.ldc` **各 0 个**。
用户数据区只有 `LoginCache.xml`、`BrandUsage.xml`、`ChromiumCache`——
**灯具目录是纯在线的**，要网络要登录。所以 grill Q1 选的「本地目录挑一个通用型号」
**前提不成立**，本地没有目录可挑。这条得改。

### 1.5 但离线导入这条路是通的（格式清单已实测）

`File → Import` 展开后有 9 项，其中：

```
ImportDrawing  ImportIfc  ImportStf  ImportDlx4  ImportLuminaire
ImportDaylightsystem  ImportFurniture  ImportProjectImage  ImportLayout
```

`ImportLuminaire` **存在且 en=True**。把它的类型过滤器（控件 1136）用
`CB_GETLBTEXT` 读出来，8 个条目：

```
[0] 所有灯具文件 (*.uld;*.gldf;*.ldt;*.ies;*.cib;*.ltl)
[1] ULD (*.uld)      [2] GLDF (*.gldf)   [3] Eulumdat (*.ldt)
[4] IES (*.ies)      [5] TM14 (*.cib)    [6] LTLI (*.ltl)   [7] 所有文件
```

**`.ldt`（EULUMDAT）和 `.ies` 都收。**这两个都是公开的纯文本光度格式，
我们可以自己生成——不依赖在线目录，不依赖 `DxImportLuminaire` 是否到期。

### 1.6 硬障碍已破解（2026-09-06 续会话实测定论，覆盖本节旧内容）

旧结论「对话框确认点不动 / BM_CLICK 无效」只说对了一半。真相分两层：

**第一层（机制）**：`BM_CLICK` 对 DirectUI/IFileDialog 确实无效，但**有效 accept 找到了**：
在对话框的 UIA 树里按文件名找 `ListItem` → `SelectionItemPattern.Select()`
→ `InvokePattern.Invoke()`（双击语义），对话框正常关闭并进入导入流程。
对照实验（`ImportDrawing`，非 Pro 门控）用同一 accept 流程干净通过 → 机制没问题。

**第二层（授权，真凶）**：accept 之后免费版弹「解锁非会员」付费墙
（窗口含 `ButtonBuyNow` / `ButtonGoToDialuxPro` / `ButtonClose`，标题=解锁非会员），
0 灯具落地。判别实验（probe `p27` / `p28`，同一份 ZEMAX 光数据只改第 1 行厂商名）：

| 第 1 行厂商名 | 结果 |
|---|---|
| `DC-MINIMAL-LDT` / `ZEMAX`（非会员） | **paywall，CatalogListBox=0** |
| `PHILIPS` / `OPPLE`（DIAL 会员） | **导入成功，CatalogListBox=1** |

→ **门禁判据 = LDT/IES 第 1 行厂商名是否属于 DIAL 会员名单**
（本机 `ManufacturerMatchingRules.xml` 有 449 厂商 + 别名映射，可复用）。
关 paywall：`ButtonClose` Invoke，无则 `WM_CLOSE`。

**遗留（交付前处理）**：验证用的 `philips_member.LDT` / `opple_member.LDT` 是
ZEMAX 光数据改第 1 行，仅证明门禁判据。正式交付应下载真实会员厂商公开
LDT/IES，或明确按「占位型号」标注，不许拿改名文件当真数据交付。

## 二、②grill 定案（4 条，用户已按推荐确认）

| # | 问题 | 定案 | 备注 |
| --- | --- | --- | --- |
| Q1 | 灯具型号从哪来 | 本地离线，28 个共用一个型号 | **三轮实测修正**：① 本地无目录 →「自生成 EULUMDAT」；② 自生成撞会员门禁（厂商名非 DIAL 会员）→ **用真实会员厂商公开 LDT/IES**（OPPLE/NVC/PAK/PHILIPS 官网有公开光度文件；门禁判据见 P0）；③ **2026-09-06 架构师定调：分两批放、放不一样的型号**——批 1 十六盏筒灯（Ø152mm）用 `build/ies/fixed/NPTLED351_NVC.IES`（已验证可导入）；批 2 十二盏线性灯（1555×300mm）**缺合规线性配光文件**（已下载 NVC 样本全是筒灯/泛光），三条获取路见 `docs/reference-dialux-ecosystem.md` 第六节，演示口径待架构师从三选一（先 12 盏 / 28 盏线性灯暂借筒灯型号 / 人工下载合规线性灯 IES） |
| Q2 | 坐标怎么送 | 先实测有没有数值坐标输入框 | **2026-09-06 已答**：`DrawPoint` 无数值框（要像素点视口，脆）；**`ArrangementFromSpace` 有整套数值 Edit**（位置 X/Y/Z、数量 X/Y、安装高度、多边形点表格） |
| Q3 | 架构改多少 | 只补「执行器抽象」一层，照 BGI 三层切法 | 见第三节 |
| Q4 | 停在哪 | 28 个灯具进 DIALux + 存盘 + 拆包验收坐标 | 不跑照度计算、不导报告、不做家具。**2026-09-06 修订待定**：落位口径=图纸原位逐盏 vs 规则网格自动排，由架构师定（见 KANBAN MVP3 条目第 7 点） |

## 三、架构：先纠正一个框架，再抄一个真东西

### 3.1 前端/后端/数据库/API 这套框架在我们这儿只对一半

那是 Web/App 的分法。我们是**本地桌面工具**，逐项对一下：

| 通用分层 | 我们的对应物 | 状态 |
| --- | --- | --- |
| 前端 | `src/ui/overlay.py` 悬浮部件 + `scripts/demo_run.py` CLI | ✅ 已有，两个前端共用一个核 |
| 后端 | `src/parser` → `src/planner` → `src/executor` → `src/exporter` | ✅ 已有 |
| 数据库 | **没有，而且现在确实缺**：灯具型号库、494 个 `.m3d` 家具尺寸索引 | ⚠️ 缺，但按 Q4 本轮不建（避免过早抽象） |
| API | 不是 HTTP。我们的接口是 **`spec/ir.schema.json` + ActionPlan 契约** | ✅ 已有，IR 就是宪法 |
| 服务器/基础设施 | 不需要。「基础设施」是本机的 DIALux 进程 + ODA 转换器 | — 不适用 |
| 测试与运维 | `pytest` 199 + `ruff` 门禁；桌面工具不需要监控告警 | ✅ 已有 |

**结论：不缺骨架，缺的是一层「执行器抽象」和一个「数据层」。** 本轮只补前者。

### 3.2 真正的架构缺陷：计划和执行是两条不相干的线

现在 `build_action_plan` 产出 **55 条动作**（`place_luminaire`×28、`create_space`×23、
其余各 1），而 `dialux_driver.ps1` 干的是**硬编码的 11 步导入**。
**这 55 条动作从来没有被执行过一条。** 进度条上的 6 行也是手写死的，
跟 ActionPlan 没有关系。

这不是洁癖问题，这是**灯具进不去的直接原因**——放 28 个灯具本质上就是
执行 28 条 `place_luminaire`，没有「执行 ActionPlan」这个机制，就没地方放它们。

### 3.3 抄 BGI 的三层切法（GitHub 上成熟的桌面自动化项目，2160 文件）

BGI 的分层（`better-genshin-impact/`，已在本地，**GPL-3.0 只抄方案不抄代码**）：

| BGI | 干什么 | 我们抄成什么 |
| --- | --- | --- |
| `Fischless.WindowsInput/`、`Fischless.GameCapture/` | 「操作目标程序」的能力抽成**独立工程**，一个接口后面挂 3 个截图后端可换 | `src/executor/uia/` 保持独立，只暴露「找元素/点/填/等」这几个原语，不含任何 DIALux 业务语义 |
| `GameTask/<任务名>/` = `XxxTask.cs` + `XxxConfig.cs` + `XxxTaskParam.cs` | 每个自动化任务一个文件夹，自带参数和配置 | 每个 action type 一个 handler：`place_luminaire` / `create_space` / … 各自声明需要的参数 |
| `GameTask/Common/` = `TaskControl.cs`、`Job/`、`StateMachine/`、`Exceptions/`、`NewRetry.cs` | 任务内核：重试、状态机、异常 | `src/executor/kernel.py`：遍历 ActionPlan、派发 handler、统一重试、统一进度上报 |
| `Model/` | 数据契约 | 已有：IR schema + ActionPlan |
| `View/` + `ViewModel/` | UI 与任务解耦 | 已有：`src/ui/overlay.py` |

**最值得抄的一条**：BGI 把重试（`NewRetry.cs`）放在内核里，不放在每个任务里。
我昨天在 `.ps1` 里手写了个 3 次菜单重试——那正是应该上提到内核的东西。

## 四、执行计划

### P0 打通「离线灯具型号进项目」（**2026-09-06 已破：真凶是会员门禁，不是对话框机制**）

1. ~~**step**：造最小 EULUMDAT `.ldt`~~ → 已造 `build/dc_lite_28_1.ldt`，但第 1 行厂商名
   用了自造的 `DC-MINIMAL-LDT`，**天然撞会员门禁**。正确做法：第 1 行写会员厂商名
   （或下载真实会员厂商公开文件）。
2. ~~**step**：换掉确认机制~~ → 已定：ListItem `Select()` + `Invoke()`（双击语义）。
3. **step（新增结论）**：免费版只放行 DIAL 会员厂商灯具；非会员弹「解锁非会员」付费墙。
   对照 ImportDrawing 证明机制干净 → 授权问题，不是机制问题。
4. **step**：存盘拆包 → 原型进工程后 `ProjectData.dat` 35→463 KB、xml 105→166 KB
   （灯具型号+光数据入工程）；`ScenegraphScene` 不变（原型≠放置）。

**卡住的退路**：~~`aid_ArrangementFromSpace` 也需要 prototype，同样被卡~~ → 已失效：
原型进项目后它已 `en=True`（见 P1）。

### P1 坐标机制（**2026-09-06 真机收尾：自动排布通道已通，精确图纸坐标未达**）

1. **step**：~~有了 prototype 之后 Invoke aid_DrawPoint~~ → 实测 DrawPoint 无数值框
   （提示「在 CAD 视窗单击/拖放」→ 像素坐标路线，脆）。
   **改用 `aid_ArrangementFromSpace`**：激活后出现整套可写 ToolPart（2026-09-06 dump）：
   - `ToolPartFieldArrangementPosition`：`PolygonPosition_X` / `_Y` / `_Z`（米）
   - `ToolPartFieldArrangement`：`ElementCountX` / `ElementCountY` + 对齐 radio
   - `ToolPartMountingHeight`：`MountingHeight_Value` / `LightPointHeight_Value`（米）
   - `ToolPartSpaceAssignment`：`GlobalSpaceComboBox`（选空间）
   - `ToolPartFieldArrangementPolyLine`：多边形点 `PART_Input` 表格（x/y/z/°，**只读**）
2. **step（实测结论）**：`ElementCountX/Y` 可写，但**每次 Invoke ArrangementFromSpace 都
   叠一套排布**，且 DIALux 按房间自动重算网格（改 4×4 后 re-invoke 跳回 4×3=12 盏）。
   DIALux 网格 =「均匀铺满房间」（间距=房间尺寸/列数），图纸 =「固定间距」（筒灯
   3.336/2.044m）。**两者不同，不能靠参数精确复现图纸坐标**。PART_Input 多边形表格只读，
   无法数值改区域。
   → **verify（已达成）**：干净流程「重开 demo_room → 导入 NVC 真实 IES → 切工具 →
   Invoke 恰好 1 次 → Save」，拆包 1 套排布 / 12 盏 / 原点 (5.95, 4.39)。灯具绝对坐标 =
   `LuminaireArrangement.CoordSys3D` 原点 + 每盏 `CoordSys3D` 局部偏移（ProjectData.dat）。
3. **step（收尾口径）**：退 `aid_ArrangementFromSpace` 自动排已通——灯具在房间里均匀分布，
   架构师口头确认可作 MVP3 演示交付，**如实说明「非图纸原位精确坐标」**。若精确图纸坐标
   必须，需 DrawPoint 像素路线或直写 .evo（P1 之后另议）。
   → **verify**：`.evo` 拆包灯具实体数量 = 排布盏数（12），坐标对齐房间中心原点。

### P2 执行器内核（**2026-09-06 完成**，与 P1 并行不冲突）

1. **step**：`src/executor/kernel.py`：`execute_plan(actions, driver, on_step)`，
   按 `type` 派发到 handler，统一重试（重试策略上提，不留在 `.ps1` 里）
   → **verify**：9 条单测——55 条动作全部被派发；未知 type 报错不静默跳过
   （`NotImplementedError` 上抛；`halt_on_unknown=False` 才跳过并记 ok=False）
2. **step**：`src/executor/uia/driver_plan.py`：`UiaDriver` 实现 Driver 协议，
   `create_space` 走 STF 批量通道（首个触发 `ir_to_stf` + `run_import`，后续幂等；
   全家具伪 space 时幂等 OK），`place_luminaire` 走 UIA 真通道
   （**2026-09-07 产品化**：`luminaire.ps1` + `luminaire.py` 导入 IES + ArrangementFromSpace
   排布；`luminaire_channel="arrangement"` 为现役，`"stub"` 保留离线安全）
   → **verify**：10 条单测（注入假 import_fn / place_fn 不碰真机）；`demo_run.py` 行为不变
3. **step**：`src/main.py --execute` 改接 `execute_plan(plan, UiaDriver(ir))`；
   真实图实测 55 条全派发、28 盏 stub 收集、进度 0→100%
   → **verify**：`test_progress_contract` 扩「计划驱动的进度」；门禁 224 passed + ruff 0

**P2.5 放灯链路 + exe 交付（2026-09-07 完成）**：
- `demo_run.py --luminaires auto`：一条命令建壳 + 自动放两批灯（point→NPTLED 筒灯、
  linear→OPPLE Re295 线性灯），真机 exit=0，`arr=20 x Opple Re295` 验证厂商前缀匹配。
- PyInstaller 打包 `dist/demo_run/demo_run.exe`（~11MB，含 .ps1 + spec/ir.schema.json 为
  datas；进程内调用不依赖外部 python；validator/schema 路径 PyInstaller 兼容）。
- exe 需同目录放图纸 + config + `build/ies/`。打包说明见 README。

遗留：`overlay.py` 的 6 行视觉进度仍是管线阶段表（解析/STF/挂接/导入/保存），
未改成逐条 ActionPlan 显示——灯具 UIA 通道已通，UI 视觉进度改造可排期做。

### P3 收尾（⑥ neat-freak）

`KANBAN.md` 记实测数字与审查意见；纠正「家具/灯具 AutomationId 不存在」那条错误结论；
删掉本轮探针脚本。

## 五、风险（2026-09-06 更新：前两条已消化）

| 风险 | 影响 | 处置 | 状态 |
| --- | --- | --- | --- |
| ~~`ImportLuminaire` 确认机制三种手段全失败~~ | P0 死 | 机制已通（ListItem Select+Invoke） | ✅ 已消 |
| ~~`DxImportLuminaire` 2026-09-08 到期~~ | 离线导入路关闭 | 到期只影响 Pro 附加功能；**免费版会员灯具路径不受 Dx 许可门控**（实测导入成功） | ✅ 已消（注意 09-08 后需复测） |
| 非会员厂商文件被付费墙挡 | 自造 LDT 进不去 | 用真实会员厂商公开 LDT/IES（Q1 已定） | ⚠️ 现行约束 |
| 找不到数值坐标输入框 | 灯具位置不是图纸原位 | `ArrangementFromSpace` 有数值 Edit；落位口径待架构师定 | ⚠️ 见 KANBAN |
| 执行器重构碰坏已通的建壳 | 保底演示翻车 | 保底路径有 199 条门禁 + 连跑 3 次的验收，改完必须重跑一遍 | — |
| 28 个灯具逐个走 UIA 太慢 | 演示时长不可接受 | 先测单个耗时再乘 28；超 60 s 就改用 `aid_DrawLine` 合并线形灯 | — |

## 六、不做什么

照度计算、导出报告（`DxPrintExport*` 全是 Pro 且 9-08 到期）、家具占位（P3 推后）、
真实厂商型号匹配、`.m3d` 家具尺寸索引、前端/后端/数据库那套 Web 式重构。
