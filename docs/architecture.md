# 架构设计

## 一、数据流 (编译器隐喻)

```
DWG / PDF / Excel
   ↓ Parser
IR (JSON): 几何 + 灯具 + 材质/反射比
   ↓ Planner (规则引擎)
ActionPlan (JSONL): DIALux 操作序列
   ↓ Executor
  A. DIALux 程序化接口 (优先)
  B. 键鼠重放 (兜底)
  C. 人工确认点
   ↓
.dlx/.evo + 计算报告
   ↓ Validator
照度 / 均匀度 / 功率密度 → 不达标则回写 Planner 重排
```

## 二、IR Schema (中间表示)

统一契约，所有模块围绕它协作。完整定义见 `spec/ir-schema.md`。

核心实体：`Project → Storey → Space(房间) → Luminaire(灯具)`。
几何统一为**米制、右手系、统一原点**；灯具坐标必须落在所属 Space 多边形内（校验层负责）。

## 三、模块划分

| 模块 | 职责 | 入口 |
| --- | --- | --- |
| parser_dxf | 抽多段线(房间)、LINE+ARC 拼接、墙线环 pass + 房间环平滑、CIRCLE/矩形灯具（并按图元判 `kind`）、图层/标注 | src/parser/dxf.py |
| parser_xlsx | 灯具表字段标准化 | src/parser/xlsx.py |
| planner | IR → ActionPlan，领域规则代码化 | src/planner/core.py |
| planner_join | 灯具按坐标归入 space，搬运 `kind`/`dims` | src/planner/join.py |
| planner_mount | 挂载高度回填：2D 图无高度，按 `ceil_h` × `mount` 补灯具 `z` | src/planner/mount.py |
| executor | 执行动作计划：`kernel.py` 遍历 ActionPlan 派发 + 统一重试 + 进度回调（P2）；旧 `key_mouse.py` A/B/C 三档为 MVP1 参考 | src/executor/ |
| executor_uia | computer use 落地：`driver_plan.py`（UiaDriver：create_space 走 STF 批量、place_luminaire arrangement 真通道）+ `driver.py`（run_import 导入 STF 存盘）+ `luminaire.ps1/py`（导入 IES + ArrangementFromSpace 放灯，2026-09-07）+ `autosave.ps1`（保存确认框自动应答）。菜单走 UIA，文件对话框走 Win32 窗口消息（对话框对 UIA 暴露不出 pattern） | src/executor/uia/ |
| exporter | IR → 外部工具可导入格式（DIALux STF，**只有房间几何真正落地**，灯具段被 evo 忽略） | src/exporter/stf.py |
| validator | 几何/灯具/结果校验（7 条规则，编号不连续，见 `validate_ir` docstring） | src/validator/ |
| workbench | 通用自动化工作台（全抄 BetterGI 架构）：`task.py`（任务抽象）、`trigger.py`（实时触发器 ITaskTrigger 模式）、`flow.py`（一条龙 OneDragon 模式：顺序+开关+断点）、`config.py`（配置持久化）、`dispatcher.py`（触发器调度器：周期轮询+优先级+独占）。**不绑定具体软件**，未来 Zemax/Transport 复用。 | src/workbench/ |
| tasks | 各软件的具体任务（workbench 的实现）：`dialux/room_task`（自动房间布置）、`dialux/luminaires_task`（自动布灯）、`dialux/report_task`（自动报告，MVP4 占位）、`dialux/autosave_trigger`（实时保存应答）。 | src/tasks/ |
| ui | 两个 PySide6 前端：`launcher.py`（GUI 启动器：启动按钮 + 同时启动 DIALux 开关 + 配置 + 日志，参考 BetterGI HomePage；2026-09-07 起内部跑 workbench Flow 一条龙）+ `overlay.py`（贴 DIALux 窗口的悬浮进度小部件：九行步骤 + 实时日志 + 停止） | src/ui/ |

### 3.1 房间环 vs 家具环（贴墙柜「柜子变墙」修复）

真实图里贴墙家具的顶边直接借用墙线，两者共享端点。环搜索走到共享端点时可以拐进柜子轮廓，
于是柜子的凸台/凹槽被并进房间多边形，DIALux 里就长出多余墙段。parser 用三道机制处理：

| 机制 | 位置 | 作用 |
| --- | --- | --- |
| 墙线环 pass（`ParseConfig.wall_ring_pass`） | `extract_rooms` 分支 B2 | 额外跑一轮 `split_at_t_junctions=False` 的环搜索：墙线不被家具端点切断，直接拼出真实墙围轮廓；只收面积 > 20 m² 的房间候选 |
| 锯齿择优（`ring_preference_key`） | `dedup_rooms` + `parse_dxf` 房间去重 | 面积相近的重复候选里，优先墙线环 → 再比 <0.2m 短边少 → 最后比顶点多 |
| 房间环平滑（`ParseConfig.smooth_room_rings`） | `parse_dxf` | 兜底：填平面积 < `notch_max_area_m2`（默认 0.5 m²，与 validator 规则 2 下限一致）且「往房间里凹」的绕行，再合并共线断点 |

家具环**不做任何平滑**（家具恰恰就是那些凹槽）。平滑只吃「填平后面积变大」的凹槽 ——
向外凸的小台、两端落在不同墙线上的转角台阶、大于阈值的真实壁龛都保留。
残留锯齿写进 `_meta.rooms_with_sawtooth` 并打 WARNING。

已知边界：柜子一侧正好贴到转角或隔墙时，凹槽退化成转角台阶，几何上与真实转角不可区分，
按设计不动（见 `tests/test_chain_geometry.py::test_notch_flush_against_corner_is_known_limitation`）。

## 四、MVP 路线

| 阶段 | 目标 | 验收 |
| --- | --- | --- |
| MVP1 | DWG → 房间多边形预览 | 真实图纸抽出房间 JSON，肉眼对齐 |
| MVP2 | IR → DIALux 建空房间 | 只建几何，不放灯 |
| MVP3 | 灯具表 → 已有房间上布灯 | 坐标正确，型号匹配 |
| MVP4 | 计算 + 报告抽取 | 计算触发+UIA 读照度已真机验证（2026-09-08，见 standard-dialux-run.md Step 9/10）；报告抽取未做 |
| MVP5 | 视觉自愈 + 异常处理 | 弹窗识别、重试、日志 |

## 五、坐标系与单位

- 输入单位从 DWG 读取，统一换算为**米**。
- 全局原点由图纸外框或用户指定；所有实体做仿射变换对齐。
- DIALux 场景单位：米，Z 轴向上。
