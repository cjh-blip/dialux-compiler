# 感知层设计 + 实施计划（BetterGI 模式移植）

> 版本：v1（2026-09-07）| 定案来源：三省六部对抗 + BetterGI 源码逐模式对比（架构师已确认）
> 原则：抄 BetterGI 的感知循环骨架，保我们的 UIA 执行层；先堆城堡用户删减

## 一句话

给工作台补上「开悟」的发动机：**每轮先识别 DIALux 处于什么状态（感知），再把状态广播给触发器（路由），触发器只在相关状态激活**——同 BetterGI 的 Tick 循环（截图 → WhichGameUi → 派触发器）。

## BetterGI 模式 → 我们的实现（对比定案）

| BetterGI 模式 | 我们的实施 | 状态 |
|---|---|---|
| Tick 循环（截图→CaptureContent） | Dispatcher 轮询 + **状态识别**（感知源） | 本轮实现 |
| `Bv.WhichGameUiForTriggers`（UI 类别判定） | **状态机**：idle/modeling/calculating/dialog/output | 本轮实现 |
| `ITaskTrigger.SupportedGameUiCategory` | `Trigger.supported_states`（只在相关状态激活） | 本轮实现 |
| `RecognitionObject`（6 种识别统一封装） | `recognition.py`：声明式识别对象（区域+方式+阈值） | 本轮实现 |
| `PostMessageSimulator`（后台键鼠） | UIA/Win32（已有，保我们的执行层） | 不动 |
| `MaskWindow` 悬浮日志 | overlay.py（已抄） | 已完成 |
| OneDragon / Task/Param/Config | flow.py / tasks/dialux/（已抄） | 已完成 |

## 架构（分层感知）

```
L0  UIA 控件执行（冻结，231 tests 资产）          ← 不动
L1  Win32 消息（文件对话框，已解决）              ← 不动
L2  窗口枚举 + 文本特征（弹窗拓扑分类）           ← 本轮：状态识别的主体
L3  截图 + OCR（未知弹窗全文/进度/伪色图）        ← PaddleOCR 实验，二期
```

## 实施步骤（本轮）

1. **`workbench/recognition.py`**：声明式识别对象（Mirrored after BetterGI RecognitionObject）
   - `UiState` 枚举（idle/modeling/calculating/dialog/output/unknown）
   - `recognize_state(ctx) -> UiState`：L2 感知（窗口枚举 + 标题/控件文本特征）
2. **`workbench/trigger.py`**：Trigger 加 `supported_states` 字段（None=任意状态激活）
3. **`workbench/dispatcher.py`**：Tick 先 `recognize_state` → 只派发 `supported_states` 匹配的触发器；状态变化时广播（`on_state_change`）
4. **`tasks/dialux/autosave_trigger.py`**：改为 `supported_states={"dialog"}`（只在弹窗状态激活）
5. **新 `tasks/dialux/calc_watch_trigger.py`**：计算监控触发器（supported_states={"calculating"}，轮询计算完成信号）
6. **测试**：状态识别 mock 测试 + 触发器路由测试 + 状态变化广播测试
7. **门禁** + 真机验证（DIALux 开着 demo_room.evo 识别状态）

## 验收标准（2026-09-09 真机验收 ✅）

- [x] `recognize_state` 对 DIALux 当前窗口能给出正确状态（真机验证：开着 demo_room.evo → IDLE，关闭 → NO_WINDOW）
- [x] 触发器只在匹配状态激活（真机路由：IDLE 探针 ticks=2、DIALOG 探针 ticks=0；autosave 挂 dialog 态）
- [x] 门禁全绿（244 passed + ruff 0，含 7 条感知层测试）
- [x] 三省结论 + BetterGI 对比表入档本文档

## 风险与止损

- 状态识别误判 → 触发器不激活（降级为现状行为，不比现在差）
- L3（PaddleOCR）实验：识别率 ≥95% 才排期，否则退 L2 强化

## 版本

- v1（2026-09-07）：三省对抗定案 + BetterGI 对比 + 实施计划

## 真机验收证据（2026-09-09）

| 场景 | 期望 | 实测 | 结果 |
|---|---|---|---|
| DIALux 开 demo_room.evo | IDLE | IDLE（枚举 2 窗口） | ✅ |
| 无弹窗时点 Save（无未保存更改） | 不误报 DIALOG | idle | ✅ |
| Dispatcher 真机路由 | IDLE 探针被派发、DIALOG 探针不派发 | 2 / 0 | ✅ |
| DIALux 关闭 | NO_WINDOW | no_window | ✅ |
