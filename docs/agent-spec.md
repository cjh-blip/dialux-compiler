# Agent 协作规范（补充文档）

> **协作体系真身在 `AGENTS.md`**（工具分工、开发流程、铁律）。本文件不复述，
> 只补两件 AGENTS.md 没有的东西：权限边界表 和 体系沿革。
>
> 2026-09-05 换代：Hermes + claude 子员工 + cc-switch 全部停用，改为 DSH 桌面版
> 顶层会话直接执行，模型 deepseek-v4-flash。换代前的完整规范见 git 历史（`ca69fc9` 及更早）。

## 1. 权限边界

| 主体 | 可读 | 可写 | 禁止 |
|------|------|------|------|
| 架构师（人） | 全部 | 全部 | — |
| DSH 顶层会话 | 整个仓库 | `src/`、`tests/`、`spec/`、`docs/`、`scripts/`、`KANBAN.md`、`AGENTS.md`、`README.md` | 未经明确要求不 `git commit`；不改 `spec/ir.schema.json`（宪法）；不放宽 ruff 配置 |
| DSH subagent | 整个仓库 | 派给它的范围 | 不自行 commit；结果回主会话由主会话裁决 |
| computer use 通道 | DIALux UI | 驱动 DIALux 建模/导入/保存 | 不动 DIALux 安装目录与 `ProgramData` 下的厂商包 |

补充约束：

- **`spec/ir.schema.json` 是宪法**（运行时唯一被加载的那份）；`spec/ir-schema.md` 只是导读，
  改导读不改宪法。
- **门禁数字不许在别处复述**：`KANBAN.md`「门禁实测」是唯一权威，本文件与 README 只放指针。
- **动文档或动代码前先跑 `git status`**：工作区有未提交改动时停下问架构师
  （起因见 `KANBAN.md`「遗留与待决」的 2026-09-03 文档并发改写事故）。

## 2. 体系沿革

| 时期 | 体系 | 状态 |
|---|---|---|
| ~2026-08 | Alice / Trae Work / ZCode / Codex / WorkBuddy | 已淘汰 |
| 2026-08-17 ~ 09-04 | Hermes v0.21 追踪 + `claude --agent` 子员工执行 + cc-switch 供模型 | 已停用 |
| 2026-09-05 起 | **DSH 桌面版直接执行 + deepseek-v4-flash**；桌面操控自研 `src/executor/uia/`（`dsh-computer-use-win` 仅是可选 OCR 后端） | **现役** |

停用体系遗留在磁盘上的东西（`D:\dev\scripts\dispatch_claude.sh`、`~/.claude/agents/`、
cc-switch 配置）仍然存在但不在链路里，**勿再引用**。

2026-09-03 曾记录一条治理缝隙：MVP2 两张看板卡实际由顶层会话执行，与当时「执行者必须是
claude 子员工」的铁律字面冲突。该铁律已于 2026-09-05 随换代废除，**缝隙自然消解**，
不再是遗留项。
