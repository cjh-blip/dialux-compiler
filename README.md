# DIALux 建模编译器 (方案 A)

把「模型直连 DIALux」改为 **数据驱动 + 规则引擎 + 可控自动化** 的建模流水线。

> 主链路：DWG/PDF/Excel → 解析器 → IR(JSON) → 规则引擎 → 动作计划 → 执行器 → .dlx/.evo + 计算报告
> 模型只做脏数据兜底，不参与主链路实时决策。

## 技术栈 (方案 A)

| 层 | 选型 |
| --- | --- |
| 开发执行 | **DSH 桌面版**（DeepSeek Harness）顶层会话，模型 deepseek-v4-flash；协作体系见 `AGENTS.md` |
| 桌面操控 | 自研 `src/executor/uia/`（PowerShell UIA + Win32 窗口消息），已在 evo 14.0 真机跑通「菜单导航 → 文件对话框 → 导入 → 保存」全自动建壳；见 `KANBAN.md`「computer use 通道」 |
| 看板 | `KANBAN.md`（人工维护，唯一现役状态板） |
| 解析 | Python + ezdxf / pandas / openpyxl（DXF + Excel 已实现）；pdfplumber 环境里有 0.11.4，但**不在 requirements.txt**、也没有任何代码 import，PDF 解析仍是空白 |
| 视觉 | OpenCV / PaddleOCR / onnxruntime（**MVP5 计划**，requirements.txt 里仍是注释行）。当前截图判读走 UIA 文本 + Windows OCR，**本机模型无图像输入** |
| 执行器 | `src/executor/kernel.py`：`execute_plan` 按 ActionPlan 派发 + 统一重试 + 进度回调（P2，2026-09-06）；`src/executor/uia/driver_plan.py`：`UiaDriver`（`create_space` 走 STF 批量、`place_luminaire` arrangement 真通道——`luminaire.ps1/py` 导入 IES + ArrangementFromSpace 排布，2026-09-07 产品化）；`--execute` 已接新链路。旧 `key_mouse.py` 保留为 MVP1 参考档，不再进主链路 |
| 工作台 | 通用自动化工作台（全抄 BetterGI 架构）：`src/workbench/`（Task/Trigger/Flow/Config/Dispatcher）+ `src/tasks/dialux/`（自动房间/自动布灯/自动报告/实时保存应答）。GUI 启动器 `launcher` 内部跑 Flow 一条龙；**不绑定 DIALux**，未来 Zemax/Transport 复用。2026-09-07 |
| 落地出口 | `src/exporter/stf.py` → STF：**只有房间几何真正落地**（evo 14.0 真机验收，顶点 11/11 回环）。灯具段虽按 IR 实写 `NrLums`，但 **2026-09-05 真机判定 DIALux 完全忽略该段，0 灯落地** → 灯具改走 computer use 通道；`NrStruct/NrFurns` 恒为 0。本仓不写 `.dlx`/`.evo`，`.evo` 由 DIALux 自己另存 |
| 版本化 | Git + spec/ 驱动 Agent |

> 历史：Alice / Trae Work / ZCode / Codex / WorkBuddy / Hermes / claude 子员工 / cc-switch
> 均已淘汰或停用，勿再引用旧协作体系（沿革见 `docs/agent-spec.md`）。

## 快速开始

```bash
# 实测环境（2026-09-05）：Python 3.11.15（D:\dev\anaconda3\python.exe）+ ezdxf 1.4.4。
# 门禁实测数字见 KANBAN.md「门禁实测」，本文件不复述。
# 本机 `python3` 指向 3.14 且没装 ezdxf，会在 import ezdxf 处报 ModuleNotFoundError；用 `python`。
pip install -r requirements.txt
python -m pytest tests/ -v
# 真实图纸解析（房间图 + 灯具图）。需先装 ODA File Converter：
# 路径解析走 src/core/env.py::get_oda_path()，按 环境变量 ODA_PATH → --oda → 默认安装位置
# 顺序查找，别改源码。
# 只给 --dwg 不给 --dwg-lighting 已不再崩（2026-09-04 修复，改为复用已转换的 DXF）。
python src/main.py --dwg 布局图.dwg --dwg-lighting 灯具图.dwg \
  --config tests/fixtures/sample_parse_config.json \
  --out build/mvp3_ir.json --preview
# 灯具挂载高度自动回填：2D 图没有高度，解析出的 z 全是 0，规则引擎按 ceil_h 与 mount 补。
# 默认 recessed（吸顶=ceil_h）；吊装/壁装可调，--overwrite-z 强制无视图纸已有 z 重算：
#   --pendant-drop 0.5   吊杆长度（米）
#   --wall-mount-h 2.2   壁装高度（米，距楼面）
# MVP2：IR → DIALux STF。evo 14.0 里 文件 → 导入 → STF 文件
# 房间几何已在真机验收（顶点坐标 11/11 回环命中）。
# 灯具段：2026-09-05 真机判定 DIALux **完全忽略** NrLums/Lum{i}，0 灯落地 → 灯具走 computer use。
python -m src.exporter.stf --validate build/mvp3_ir.json build/mvp3_out.stf
```

### 一键演示：DWG → DIALux 里存好 `.evo`（含放灯）

前提：DIALux evo 已经开着（这两条都是挂到运行中的进程，不负责冷启动）。

```bash
# 纯命令行版（保底路径，实测 9.91 s 跑完全程）
python scripts/demo_run.py
python scripts/demo_run.py --no-drive        # 只出 STF，不碰 DIALux
python scripts/demo_run.py --skip-parse      # 复用已有 IR，只跑落地

# 建壳 + 自动放灯（一条命令：解析 → 建房间 → 导入筒灯/线性灯型号 → 排布 → 存盘）
python scripts/demo_run.py --luminaires auto
python scripts/demo_run.py --luminaires point=build/ies/fixed/NPTLED351_NVC.IES \
    linear=build/ies/linear/opple_LEDPanelRc-S-Re295-30W-4000-WH-U19.ies

# 带界面版：贴在 DIALux 窗口右上角的半透明悬浮小部件，
# 六行步骤列表 + 真进度条（分母是确定的动作条数，不是假曲线）+ 停止按钮
python -m src.ui.overlay
```

### 打包成 exe（交付形态）

两种交付：
- **GUI 启动器**（推荐给用户，双击出窗口）：`scripts/launcher.spec` → `dist/launcher/launcher.exe`
- **命令行版**：`scripts/demo_run.spec` → `dist/demo_run/demo_run.exe`

```bash
# GUI 启动器（有窗口：启动按钮 + 「同时启动 DIALux」开关 + 配置 + 日志）
python -m PyInstaller scripts/launcher.spec --noconfirm --clean
# 命令行版
python -m PyInstaller scripts/demo_run.spec --noconfirm --clean
```

> spec 的 `ROOT` 通过 PyInstaller 内置 `SPECPATH` 自动探测仓库根（spec 在 `scripts/` 下），
> 换目录/换机打包无需改路径。GUI 启动器参考 BetterGI HomePage 交互（抄模式不抄代码）：
> 大启动按钮 + LinkedStart 开关（目标程序未运行则自动打开）。

**运行**：把 `布局图.dwg`、`灯具图.dwg`、`sample_parse_config.json`、`build/ies/`
放到 exe 同目录（GUI 启动器会自动探测这些文件，也可点「浏览」手选）。然后：

```bash
# GUI 版：双击 launcher.exe，勾「同时启动 DIALux」，点启动
# 命令行版（无 DIALux 先试 --no-drive；有 DIALux 一条命令建壳+放灯）
demo_run.exe --dwg 布局图.dwg --dwg-lighting 灯具图.dwg \
    --config sample_parse_config.json --luminaires auto
```

驱动层是 `src/executor/uia/`：**菜单走 UIA，文件对话框走 Win32 窗口消息**——
DIALux 的文件对话框对 UIA 暴露不出任何 pattern，只有 Win32 看得见它的控件。
踩坑细节与验收证据见 `KANBAN.md`「MVP3 演示交付」，计划文档 `docs/plan-mvp3-demo.md`。

## 目录结构

详见 `docs/architecture.md`。IR 权威定义是 `spec/ir.schema.json`（运行时唯一被加载的那份），
`spec/ir-schema.md` 是导读；协作规范见 `docs/agent-spec.md`。
计划与调研文档：`docs/plan-mvp3-luminaire.md`（灯具布置计划）、
`docs/plan-mvp3-demo-stage.md`（阶段性演示方案）、`docs/reference-dialux-ecosystem.md`（DIALux 生态资料清单）。
家具路线计划：`docs/plan-furniture-recognition-placement.md`（识别 IR + FurnitureTask + 单件真机闭环）。
标准流程文档：`docs/standard-dev-workflow.md`（软件开发七步链）、`docs/standard-dialux-run.md`（DIALux 运行 SOP，agent 可执行版）、
`docs/reference-standard-task-flow-v1.md`（通用标准任务流程六步链 v1，来源 cjh 与 Hanako）。

## 当前状态

唯一现役状态板是 `KANBAN.md`：MVP 进度、验收结论、门禁实测数字、几何口径（房间名/顶点数/面积）、
现役实现边界与遗留项都只记在那里，本文件不复述。
