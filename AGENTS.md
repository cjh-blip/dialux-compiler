# AGENTS.md — Dialux Compiler 项目

## 项目目标
将 DWG/PDF/Excel 图纸通过解析→IR→规则引擎→执行器，自动在 DIALux evo 中完成建模。
参考：Mrite（数据驱动）+ BetterGI（视觉操控桌面）。

## 工具分工（2026-09-05 换代：Hermes / claude 子员工 / cc-switch 全部停用）

架构师 2026-09-05 口头定案：「接下来就都用 DSH 桌面版进行开发，claude 跟 hermes 就不用了，
现在都用 deepseek-v4-flash」。以下是现役分工。

| 角色 | 工具 | 职责 | 边界 |
|------|------|------|------|
| 架构师/验收者 | 你（人） | 定 spec、审任务、验收、Git commit | 唯一决策者 |
| 开发执行 | **DSH 桌面版**顶层会话（DeepSeek Harness） | 读写代码、跑门禁、改文档、驱动 DIALux | 直接执行，不再转包 |
| 并行拆分 | DSH `subagent` / `subagent_fork` / `workflow` | 独立子任务、扇出调研 | 结果回主会话，不自行 commit |
| 模型 | **deepseek-v4-flash**（`agent-default-model`） | 全链路 | 配置在 `~/.dsh/settings.yaml` |
| 桌面操控 | 自研 `src/executor/uia/`（PowerShell UIA + Win32 窗口消息；`dialux_driver.ps1` 是唯一真机验证过的驱动） | 驱动 DIALux evo | 见 `KANBAN.md`「computer use 通道」；`dsh-computer-use-win` 插件仅是可选 OCR 后端 |
| 看板 | `KANBAN.md`（人工维护） | 状态流转、验收留痕 | 只追踪不承载执行 |

> 历史体系（**勿再引用**）：Hermes v0.21 + kanban 派单、`claude --agent` 子员工执行、
> 角色库 `~/.claude/agents/`、cc-switch v3.20.1 供模型、`dispatch_claude.sh` 派单脚本、
> Alice / Trae Work / ZCode / Codex / WorkBuddy。这些文件和脚本在磁盘上仍存在但已不在链路里。
> 换代前的规则文本见 git 历史（`ca69fc9` 及更早）。

## 开发流程（2026-09-05 换代版）

0. 动文档或动代码前先跑 `git status`：工作区若有别人的未提交改动，停下问架构师，不在别人的
   半成品上叠改（起因是 2026-09-03 的文档并发改写事故，记述见 `KANBAN.md`「遗留与待决」）
1. 你写 spec（输入/输出/验收标准）或口头给目标
2. DSH 会话直接执行；需要并行或隔离上下文时用 `subagent` / `workflow` 拆分
3. 门禁全绿（`pytest` + `ruff`，数字见 `KANBAN.md`「门禁实测」）
4. 真实图纸 / DIALux 真机验证 → 按 AC rubric 打分（AC 编号定义见 `KANBAN.md`「需求 ID 溯源」，
   引用时必须写清是哪份任务书的 AC-N —— 编号空间已被复用）
5. 回写 `KANBAN.md` done/blocked（必须挂审查意见），你 review 后继续迭代


## 验证与状态入口

- 状态板（唯一现役）：`KANBAN.md`。MVP 进度、验收结论、门禁实测数字、几何口径、遗留项只记在那里；
  本文件与 `README.md` 只放指针，不复述数字。
- 跑起来 / 真实图纸复现：见 `README.md` 快速开始。
- 架构：`docs/architecture.md` 有全层表；**通用工作台**（全抄 BetterGI 架构）在
  `src/workbench/`（Task/Trigger/Flow/Config/Dispatcher）+ `src/tasks/<app>/`（具体软件任务，
  当前 `dialux/`；不绑定 DIALux，Zemax/Transport 复用同骨架）。GUI 启动器 `launcher` 内部跑 Flow 一条龙。
- 门禁命令（解释器用 `D:\dev\anaconda3\python.exe`，本机无 venv）：`python -m pytest tests/ -q`
  与 `python -m ruff check .`；实测结果见 `KANBAN.md`「门禁实测」。
- ruff 条数绑定 ruff 版本与 `.gitignore` 忽略面（ruff 默认尊重 .gitignore），任一变化数字就变；
  仓库无 ruff 配置文件。禁止靠加宽 ruff 配置把门禁做绿，改写选项见 `KANBAN.md`「遗留与待决」。
- IR 权威定义是 `spec/ir.schema.json`（运行时唯一被加载的那份）；`spec/ir-schema.md` 是它的导读。

## 铁律

- **DSH 会话直接执行**（2026-09-05 换代）：不再有「执行者必须是 claude 子员工」的限制，
  也不再区分「总控」与「执行者」。DSH 顶层会话就是执行者；`subagent` 只用于并行与上下文隔离。
- **看板只做追踪**，不承载执行
- **IR schema 是宪法**，解析器/规则引擎/执行器全部围绕它
- **一次只做 1 个 MVP**，不跳步
- **测试是验收标准**，pytest 全绿 ≠ 功能正确，真实图纸 / DIALux 真机验证才算数
- 简单任务直跑，高风险任务进闭环（拆解 → 执行 → 审查 → 验收）

## MVP 路线

| MVP | 内容 | 验收 | 状态 |
|-----|------|------|------|
| 1 | DWG → 房间多边形预览 | 真实图纸抽出房间 JSON，肉眼对齐 | ✅ 已验收 |
| 2 | IR → DIALux 建空房间 | 只建几何，不放灯 | ✅ 几何回环已验收（2026-09-05） |
| 3 | 灯具表 → 在已有房间上布灯 | 坐标正确，型号匹配 | 进行中（P0 已破：会员门禁判据 + ListItem accept；放灯链路已产品化：`demo_run --luminaires auto` 一条命令建壳+放两批灯 + GUI 启动器 `launcher.exe`（BetterGI 式：启动按钮+同时启动 DIALux 开关），2026-09-07 真机验证；落位口径已定=自动排布（非图纸毫米级原位），见 `KANBAN.md` + `docs/plan-mvp3-luminaire.md`） |
| 4 | 计算 + 报告抽取 | 自动计算，抽照度/功率密度 | 未开始 |
| 5 | 视觉自愈 + 异常处理 | 弹窗识别、重试、日志 | 未开始 |

进度细节与验收证据只在 `KANBAN.md`，本表只给状态词。

## 成本与配置

- 模型：**deepseek-v4-flash**，配置在 `~/.dsh/settings.yaml` 的 `agent-default-model`。
- **本会话无图像输入能力**：`settings.yaml` 里三个 provider 的模型全声明 `input: [ text ]`，
  截图判读靠 UIA 文本 + Windows OCR，不靠视觉模型。要开视觉需在 settings.yaml 里加
  `input: [ text, image ]` 的模型条目。
- DIALux evo 14.0 的 **9 项 Pro 附加功能 2026-09-08 到期**（`DxImportLuminaire` 等，
  清单见 `KANBAN.md`「家具库 / 灯具库实核」）；**STF 导入 / 基础建模 / 存 `.evo` 不在名单里**，
  主路径不受影响。

## 代码审查铁律

> 借鉴 BetterGI AGENTS.md 的审查优先级清单，做高风险改动时统一自查。
> 审查顺序：崩溃 > 死锁/资源泄漏/数据竞争 > 错误处理 > 风格。

### 1. 稳定性与资源
- **子进程必须等待/清理**：调用 ODA/DIALux/OCR 等外部进程时，必须 `subprocess.run(..., timeout=...)` 或 `Popen` + `wait`；退出时杀进程树（参考 Mrite 的 process-manager.js）。
- **文件/流必须释放**：`with open(...)`, `with tempfile.TemporaryDirectory()`；`Mat/Bitmap/Stream` 式资源在 dialux 主要是图片/DXF 文档，同样 `with` 或显式 `close()`。
- **临时目录必须清理**：`tempfile.TemporaryDirectory` 或 `try/finally: shutil.rmtree(..., ignore_errors=True)`。

### 2. 并发与状态
- **全局可变状态禁止偷偷改**：截图对象、键鼠状态、DIALux COM 句柄等共享资源必须显式加锁或走单线程；BetterGI 的 `PostMessage/SendInput` 共享状态冲突是前车之鉴。
- **CancellationToken 思维**：长任务函数应接受可选的取消信号（未来 MVP5 的 `cancel_event`），循环内定期检查，避免键鼠长任务停不下来。
- **单位/坐标必须显式**：米 vs 毫米、Z 轴方向、全局原点在改动几何/导出代码时必须写清楚注释；禁止隐式混用。

### 3. 错误处理
- **裸异常禁止直接抛给用户**：外部 API/子进程/DIALux 弹窗错误应翻译成"中文 + 可行动作"，参考 Mrite 的 `normalizeTaskErrorMessage`。
- **编码问题（GBK vs UTF-8）**：Windows 中文环境下子进程输出、文件读写必须显式声明 `encoding="utf-8", errors="replace"`，这是 test_smoke 编码 bug 的教训。
- **None/空值必须有兜底**：`KeyMouseExecutor._locate_control` 这类控件定位函数，找不到时要么返回明确的 `None` 让上层走降级，要么抛明确异常，不能静默失败。

### 4. 风格与可维护（ruff 不放宽）
- **E702（多语句一行）**：拆成多行。
- **F401（未用 import）**：删掉或加 `# noqa: F401` 并注释原因。
- **E741（l/O/I 变量名）**：改成 `length`/`idx` 等可读名字。
- **F541（f-string 无占位符）**：改普通字符串或加占位符。
- **禁止靠放宽 ruff 配置把门禁做绿**。
