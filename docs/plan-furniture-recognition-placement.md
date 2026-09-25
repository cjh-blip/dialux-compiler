# 家具识别与 DIALux 放置实施计划

> 对应设计：[2026-09-08-furniture-recognition-and-placement-design.md](superpowers/specs/2026-09-08-furniture-recognition-and-placement-design.md)
> 状态：执行中（2026-09-08：单件真机已通过；22 件批量因文件管理器/多 DIALux 状态暂停）
> 目标：先完成 1 件家具的识别与 DIALux Cuboid 真机闭环，再扩展到 22 件。

## 1. 成功标准

1. 当前 208 DWG/DXF 解析仍得到 1 个真实房间、22 件家具。
2. 每件家具输出可追溯的 IR：`id`、`room_id`、`polygon`、`bbox`、`area_m2`、`kind`、
   `height_m`、`rotation`、`confidence`、`source_layer`、`source_entity`。
3. 新增的 `FurnitureTask` 能在已打开的 DIALux 工程中创建 1 件 Cuboid，并报告可行动失败原因。
4. 单件家具中心/尺寸误差 ≤ 10 mm，高度误差 ≤ 1 mm；`.evo` 拆包确认对象是
   `FurnitureElement`，不是额外 ROOM/建筑；重开工程后对象仍存在。
5. 离线测试、全量 pytest、ruff 均通过；真机证据留在 `build/`（该目录继续被忽略）。

## 2. 文件范围

### 修改

- `src/parser/dxf.py`：家具候选、去重、房间归属、来源字段和默认高度。
- `spec/ir.schema.json`：声明家具对象字段及 `space.furniture` 结构。
- `spec/ir-schema.md`：同步 IR 导读与兼容说明。
- `src/tasks/dialux/__init__.py`：导出 `FurnitureTask`。
- `src/ui/launcher.py`：在房间与灯具之间接入可显式开关的家具步骤。
- `tests/test_real_dxf.py`、`tests/test_chain_geometry.py`：更新真实基线断言（只在字段契约改变时）。
- `tests/test_driver_plan.py` 或对应新测试文件：补充家具通道的注入测试。

### 新建

- `src/executor/uia/furniture.py`：家具 UIA 通道；封装工具切换、空间选择、Cuboid 尺寸/高度写入、
  命名、位置策略和事件结果。
- `src/executor/uia/furniture.ps1`：只放 UIA/Win32 低层动作，使用 ASCII 参数和结构化事件输出；
  不把业务坐标、家具 id 或中文文本硬编码在脚本中。
- `src/tasks/dialux/furniture_task.py`：工作台任务，负责读取 IR、选择首个/批量家具、取消检查、
  失败即停和用户可读结果。
- `tests/test_furniture_ir.py`：家具字段、房间归属、去重、置信度和反例测试。
- `tests/test_furniture_task.py`：Task 离线测试，所有真机调用通过依赖注入替换。
- 必要时新增 `src/executor/uia/coordinate_map.py` 与对应测试：屏幕像素到米制坐标的校准，
  仅当 UIA 没有可写 X/Y/Z 控件时创建，不提前抽象。

## 3. 执行步骤

### Step 0：工作区与基线

- 运行 `git status --short --branch`，若出现他人未提交改动，停止并报告。
- 运行当前真实家具测试：
  `D:\dev\anaconda3\python.exe -m pytest tests/test_real_dxf.py -q`
- 记录基线：当前应为 13 passed（该文件）及全仓 231 passed 的最近门禁数字；实际输出以本次命令为准。

### Step 1：先写家具 IR 红测（TDD）

- 在 `tests/test_furniture_ir.py` 先写失败测试：
  - 真实样本输出 22 件家具；
  - 每件有 polygon/bbox/area；
  - `room_id` 指向真实房间；
  - 来源字段存在；
  - 低置信度候选保留；
  - 小房间、柱子、墙垛、重复环、开放线等反例不被静默当成家具。
- 运行该测试，确认失败原因是字段/行为缺失而非测试错误。
- 只实现最小 parser 变化使红测转绿：保留现有 208 的 22 件基线，增加显式字段和确定性归属。
- 归属优先使用家具中心点/多边形包含关系；无唯一包含房间时保留候选并降低 `confidence`，
  不再无条件挂到最大房间。
- 运行家具测试和真实 DXF 测试。

### Step 2：同步 schema 与预览契约

- 在 `spec/ir.schema.json` 为 `space.furniture.items` 增加字段定义和单位说明，保持已有额外字段兼容。
- 在 `spec/ir-schema.md` 写清：家具不再依赖伪 space 名称；伪 space 仅为旧预览兼容层。
- 为 schema 增加最小合法/非法 fixture，验证 polygon、正尺寸、confidence 范围和 `room_id`。
- 运行 schema/validator 相关测试，确认灯具和房间既有契约不回归。

### Step 3：先做 UIA 只读探针，再写放置动作

- 在真实 DIALux 副本工程上探测选中一个家具后的控件树：
  `MenuGotoShowFurnitureTool`、空间选择控件、Cuboid 三边 Edit、名称控件、位置/旋转控件。
- 优先确认是否存在可写数值 X/Y/Z；把 AutomationId、支持的 Pattern、成功判据写入探针日志。
- 若没有数值坐标控件，才设计 `coordinate_map.py`：以已知房间边界和视口截图/窗口矩形校准米制映射，
  不能在家具业务代码里散落屏幕常量。
- 低层 PowerShell 输出事件至少包含 `step`、`ok`、`detail`、必要的控件 AutomationId；
  进程必须等待并在失败时返回明确错误。

### Step 4：FurnitureTask 离线实现（TDD）

- 先在 `tests/test_furniture_task.py` 写红测：
  - 只取一个家具时调用顺序正确；
  - 缺 room_id、polygon、尺寸或高度非法时失败；
  - 注入的 UIA 函数失败时返回包含家具 id 和阶段的中文错误；
  - 取消信号在批量循环中生效；
  - 一件失败后停止，不静默跳过后续家具。
- 新建 `FurnitureTask`，输入只来自 `TaskContext` 的 IR/params，不重新解析图纸。
- 首个版本支持 `limit=1` 或显式 `furniture_id`，默认不开启批量真机，防止误放 22 件。
- 为 UIA 调用提供依赖注入；离线测试不得启动 DIALux、点击桌面或写真实工程。
- 测试转绿后再做小范围重构，保持 TaskResult 语义与现有 RoomTask/LuminairesTask 一致。

### Step 5：接入 Flow 与 GUI

- 在 `src/ui/launcher.py` 增加家具开关/参数，默认关闭或仅允许显式单件探针，避免改变现有演示行为。
- Flow 顺序固定为 `RoomTask -> FurnitureTask -> LuminairesTask -> ReportTask`；家具失败时不得继续布灯/报告。
- 日志显示家具 id、尺寸、目标房间、当前步骤和停止原因；不能用“完成”掩盖只生成了半成品。
- 补工作台顺序/失败即停/禁用步骤测试。

### Step 6：单件真机闭环（已完成）

- 复制 `build/demo_room.evo` 为独立探针工程，任何实验不覆盖正式演示工程。
- 用当前 IR 选择一件 `LINEARC_*` 家具，默认高度 0.75 m，先验证 Cuboid。
- 依次验收：DIALux 3D 位置、尺寸和高度；保存；关闭/重开；`.evo` 解包查看
  `Project/ProjectData/ProjectData.dat` 中的 `FurnitureElement` 和位置关系。
- 记录误差和判定结果到 `build/`，不把临时工程或截图加入源码提交。
- 若 UIA 数值坐标不存在且校准点击连续三次仍不能达到 ±10 mm，停止该路线，另开 `.evo` STEP 结构计划；
  不在本计划内直接写专有格式。

### Step 7：扩展到 22 件（暂停，待清理运行态后继续）

- 单件通过后去掉 `limit=1`，仍按 IR id 顺序逐件执行。
- 每件成功必须有独立事件；首个失败立即停止并报告已完成/未完成 id。
- 真机保存并重开后，拆包统计 `FurnitureElement` 数量与 IR 数量一致，且没有新增 ROOM 建筑。
- 仅在 22 件稳定后，创建下一张“桌面计算面”计划，不在本计划中混入评估区实现。

## 4. 测试命令

开发循环：

```powershell
D:\dev\anaconda3\python.exe -m pytest tests/test_furniture_ir.py tests/test_furniture_task.py -q
D:\dev\anaconda3\python.exe -m pytest tests/test_real_dxf.py tests/test_driver_plan.py tests/test_workbench.py -q
```

全量门禁：

```powershell
D:\dev\anaconda3\python.exe -m pytest tests/ -q
D:\dev\anaconda3\python.exe -m ruff check .
```

真机证据：

- 单件探针工程保存为 `build/probe_furniture_single.evo`。
- 结构检查对象为 `Project/ProjectData/ProjectData.dat`，重点统计 `FurnitureElement`，
  不能只看 `ScenegraphScene`。
- 以三维视图确认位置，以 STEP/重开工程确认持久化；两者缺一不可。

## 5. 提交节奏

- `test(furniture): add IR contract and adversarial cases`
- `feat(parser): emit traceable furniture records`
- `test(furniture): cover task failure and cancellation`
- `feat(uia): add single cuboid furniture channel`
- `feat(workbench): wire FurnitureTask behind explicit switch`
- `docs: record single-furniture real-machine evidence`

每个提交前运行相关测试；最终提交前必须运行全量 pytest、ruff、工作区状态检查，并把真实验收结论回写
`KANBAN.md`。
