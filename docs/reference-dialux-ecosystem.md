# DIALux 生态参考资料（2026-09-06 调研，2026-09-07 更新本地化）

> 目的：后续大量功能开发（灯具只是一个小点）的参考清单。
> 来源：GitHub 搜索 + DIAL 官方支持站 + web 搜索。外部资料未经本仓验证，
> 引用前按需自行核对版本与授权。
> 本地副本：2026-09-07 统一浅克隆到 `D:\dev\dialux-references\`（5 库，见第二节标注），
> 独立于本仓（主仓库 .gitignore 排除参考项目，避免污染）。

## 一、官方接口与格式（DIAL 权威）

| 主题 | 要点 | 来源 |
|---|---|---|
| STF 格式 | DIAL 官方交换格式，CAD ↔ DIALux 传房间几何 + **灯具位置**（"specified luminaire positions, keyword: refurbishment"）。**DIALux evo 的 STF export 仍是 "in preparation"** → 解释了本仓「STF 灯具段被 evo 忽略」：evo 的 STF 导入可能只实现了房间几何 | [STF Format - DIAL 支持站](https://evo.support-de.dial.de/support/solutions/articles/9000073197/) |
| CAD 数据交换 | STF/gbXML/IFC 三条路径；STF 由 DIAL 开发，免费提供接口文档（联系 bremecker@dial.de） | [Data exchange CAD ↔ DIALux](https://evo.support-en.dial.de/support/solutions/articles/9000073210-data-exchange-between-cad-programs-and-dialux) |
| GLDF | 开放灯具数据标准（DIAL 推动），`Gldf.Net.dll` 已装机；ImportLuminaire 收 `*.gldf` | [GLDF benefits - DIAL](https://www.dial.de/en-GB/news/what-are-the-benefits-of-gldf-for-you-as-a-planner) |
| DIALux 官方支持站 | 知识库/FAQ，接口文档入口 | [evo.support-de.dial.de](https://evo.support-de.dial.de/support/home) |

**对本仓的启示**：STF 灯具段被忽略可能有两条路可走——
(a) 联系 DIAL 要 STF 接口文档（官方免费提供），确认 evo 支持范围；
(b) 走 GLDF（开放标准）喂自有灯具数据，绕过厂商门禁的替代口子（KANBAN 已记）。

## 二、GitHub 高价值参考库（按相关度排序）

### 1. kmorin/STF-Exporter（⭐14，C#，MIT）— 最相关
Revit → DIALux 的 STF 导出插件。**我们 STF 生成器的现成对照**：
- 仓库：https://github.com/kmorin/STF-Exporter
- 📁 本地：`D:\dev\dialux-references\STF-Exporter`（2026-09-07 浅克隆）
- 价值：看它如何组织 STF 文本（房间/窗/门/灯具段），验证我们的字段写法；已维护到 2026-03。

### 2. luciodias/EvoParse（Python）— 验收工具直接可用
解析 DIALux EVO 项目文件（.dat/.evo，ISO-10303-21 STEP）为 Pydantic 模型。
- 仓库：https://github.com/luciodias/EvoParse
- 📁 本地：`D:\dev\dialux-references\EvoParse`（2026-09-07 浅克隆）
- 价值：**我们拆包验收（灯具坐标在 ProjectData.dat）可复用**，比手写 STEP 解析稳。
  主题：data-modeling / iso-10303-21 / step-file / lighting-design。

### 3. 123VincentB/eulumdat-py（Python，MIT）— 灯具文件生成
EULUMDAT (.ldt) 解析与写入。
- 仓库：https://github.com/123VincentB/eulumdat-py
- 📁 本地：`D:\dev\dialux-references\eulumdat-py`（2026-09-07 浅克隆）
- 价值：**生成/校验自有 .ldt** 的正规实现（当前我们手搓 dc_lite）；也支持 IES 相关。

### 4. moisesbritez92/dialux-mcp（Python）— 自动化通道参考
DIALux evo 的 MCP 服务。
- 仓库：https://github.com/moisesbritez92/dialux-mcp
- 📁 本地：`D:\dev\dialux-references\dialux-mcp`（2026-09-07 浅克隆）
- 价值：与我们「computer use 通道」同思路（程序驱动 DIALux），可对照其驱动方式；
  ⚠ 外部 MCP 服务，接入前审源码。

### 5. BHoM/DIALux_Toolkit（C#，BHoM 工程框架）— STF 互操作权威
BHoM 官方工具链与 DIALux 的 STF 互操作层（KANBAN 里 STF 格式逆向的来源）。
- 仓库：https://github.com/BHoM/DIALux_Toolkit
- 📁 本地：`D:\dev\dialux-references\DIALux_Toolkit`（2026-09-07 浅克隆）
- 价值：STF 段结构（[VERSION]/[PROJECT]/[ROOM.Rn]）的参考真身，验证我们 stf.py 的格式。

## 三、其它可看（star 低但主题相关）

- `Thebl3/hti-dialuxevo-manager`（C#，WPF）：管理共享盘上的 .evo 项目文件
- `VitalyKuzmin/dialux_material`（JS）：渲染 DIALux 材质
- GitHub 搜索 `dialux` 共 69 仓；搜索 `eulumdat` / `ldt parser` / `ies parser` 可再挖光度库。

## 四、后续功能开发的地图（灯具只是起点）

| 功能方向 | 可参考 | 备注 |
|---|---|---|
| 灯具精确落位 | STF 官方文档（灯具位置）、EvoParse（验证）、dialux-mcp | STF 支持灯具位置是官方口径 |
| 自有灯具数据 | GLDF（开放标准）、eulumdat-py | 绕厂商门禁的替代口子 |
| .evo 拆包/验收 | EvoParse | 替代手写 STEP 解析 |
| 计算/报告抽取（MVP4） | DIALux 官方文档 + DxPrintExport 系列（Pro，9-08 到期） | 到期后需另寻通道 |
| 视觉自愈（MVP5） | BetterGI（本地参考项目）+ dsh-computer-use-win OCR | 已记 KANBAN |

> 引用规则：本文件是「指针清单」，不是权威实现文档；具体集成前以官方文档与源码为准。

## 五、资料阅读结论（2026-09-06 调研；本地副本见第二节路径，2026-09-07 重新下载）

### STF-Exporter（kmorin，MIT）— 已读源码，关键验证
- 灯具段正确格式（Command.cs:290-309）：`LumN=name` / `LumN.Pos=X Y Z` / `LumN.Rot=0 0 0`，
  在 ROOM 段内、`NrLums` 之前；文件底部 `[FixtureName]` 块含 Manufacturer/Box/Flux/NrLamps/MountingType。
- **我们 stf.py 已按此修正**（旧 `Lum{i}=x y z symbol` 一行塞是错的）。
- **真机验证结论：格式修正后 evo 14.0 仍 0 灯具落地**（导入执行了，ProjectData +24B，
  LuminaireElement=0）。STF-Exporter 针对老 DIALux 4.x；官方文档注明 evo 的 STF export
  仍 "in preparation" → **evo STF 导入很可能只实现了房间几何**。STF 灯具段在 evo 14.0 确认此路不通。

### EvoParse（luciodias，Python）— 已读，评估可用
- 解析 .evo/.dat（ISO 10303-21 STEP）为 Pydantic v2 模型：scenes/luminaires/spaces/materials。
- **可替代我们手写 STEP 拆包验收**（目前我们手写正则解析 ProjectData.dat）。
- 依赖：Python 3.14+（本机 3.11）→ 需确认兼容性或作为参考实现。pip install evoparse。

### eulumdat-py（123VincentB，MIT）— 已读，评估可用
- EULUMDAT .ldt 读写：完整对称展开（ISYM 0-4）、头字段编辑、ISO-8859-1 保存、无外部依赖。
- **可替代手搓 dc_lite 生成/校验自有 .ldt**；ISO 17025 实验室开发，质量可信。
- 用途：给线性灯生成合规配光文件（只要有光度数据），或校验导入的 .ldt。

### dialux-mcp（moisesbritez92，Python）— 已读，思路对照
- 组合「STF 文件生成 + pywinauto UI 自动化」驱动 DIALux evo（5.13），无官方 API/CLI。
- **与我们的思路一致**（STF 导入 + 自动化），但它用 pywinauto，我们用 PowerShell UIA。
- 参考价值：工作流组织、西班牙语接口（es-ES）、环境变量配置；接入前审源码。

### 对后续开发的启示
1. STF 灯具段在 evo 无望 → 灯具精确落位只能走 computer use（ArrangementFromSpace 已通）
   或未来 evo 版本支持 STF export 后复用正确格式
2. 验收工具：评估引入 EvoParse 替代手写拆包（需先确认 py3.14 兼容或 fork 适配 3.11）
3. 自有灯具数据：eulumdat-py 可用于生成/校验 .ldt（配合 GLDF 开放标准绕厂商门禁）

## 六、合规灯具配光获取路径（2026-09-06 探索，待架构师定方向）

**目标**：12 盏线性灯（1555×300mm 面板）的合规配光文件（DIAL 生态会员厂商发布，非伪造）。

**已验证**：
- DIALux 软件内品牌库：855 个会员品牌，搜索 OPPLE → 命中「Opple 欧普照明」；
  选中后有 `ButtonInstallOfflineCataloge`（安装离线目录）/ `ButtonStartOnlineCataloge`（在线目录）
- **但这两个按钮点击后无 UIA 可见反应**——疑似在内嵌 Chromium 浏览器里操作，UIA 读不到，
  需要人工介入或对 DIALux 内嵌浏览器逆向（成本高）
- luminaires.dialux.com（DIAL 官方灯具库）：网页版可访问，但交互式搜索无公开 REST API，
  品牌页可读，产品搜索要 JS 交互
- NVC 新加坡站（nvc-lighting.com.sg）：28 个 IES 全是筒灯/泛光/投光，**无室内线性面板灯**
- OPPLE 官网下载中心（opplelighting.*）：TYPO3 JS 渲染，HTTP 抓不到列表
- GLDF 官方（globallightingdata/gldf）：只有 xsd schema，无现成示例文件

**结论**：合规线性灯配光的三条路，均需额外投入：
1. **软件内目录**（最合规）：品牌库选 OPPLE → 人工点「在线/离线目录」→ 搜线性灯。
   成本：需要人眼看屏操作一次，或逆向 DIALux 内嵌 Chromium。
2. **厂商官网挖掘**：OPPLE/PAK 中国官网的 TYPO3 API 逆向，或找带 JSON 的产品搜索。
   成本：中高，成功概率不确定。
3. **eulumdat-py 自生成**（低合规风险但非「厂商发布」）：用真实光度数据（实验室测量值）
   通过 eulumdat-py 生成 .ldt，厂商声明与数据一致才合规；当前**没有线性灯实测数据**，
   这条路实际不可行（没有数据源）。

**推荐**：① 若只为演示，先用 NPTLED351 放满 28 盏（位置分两批，配光暂用筒灯，如实标注），
合规线性配光列入 MVP3 后续；② 若必须合规线性灯，选软件内目录路径（需人工操作一次）。

## 七、NVC 中国官网下载中心挖掘（2026-09-06，Vue/Nuxt SSR）

- 入口：`https://product.nvc-lighting.com.cn/resource`（下载中心，37KB SSR 页）
- API 端点（从 Nuxt entry.js 提取）：`/seriesSelect`、`/seriesDetail`、`/resource`、
  `/search`、`/contentDetail`、`/modelDetail`（baseURL='dev'，完整 host 需从 JS 配置找）
- 直接 GET 返回 SSR HTML（不是 JSON API），需带参数与 token → 纯 HTTP 抓取成本高
- **结论**：NVC 官网有合规灯具数据，但自动抓取需逆向 Vue SSR 参数，均为高成本；
  软件内品牌库的「安装离线目录」若可用（人工点一次）是更低成本的合规路径

## 八、合规线性灯配光已交付（2026-09-07 实测，辅助会话）

> 本节是对第六节结论的实测更新；第六节原文保留作历史探索记录。

**结果**：24 个会员厂商线性灯 IES 已交付 `build/ies/linear/`（完整清单/来源/异常见
该目录 `_下载报告.md`）。OPPLE 16 个（`[MANUFAC] OPPLE` 全部有值）+ NVC 8 个
（NLI496 线性灯 4 个 MANUFAC=NVC；NPN 面板灯 4 个 MANUFAC 空/ETI，官网原样未改）。
会员核验：NVC/OPPLE 均在 `ManufacturerMatchingRules.xml` 在册。

**对第六节两条结论的更正**：
1. 「NVC 新加坡站 28 个 IES 全无线性面板灯」→ 不成立。该站下载中心实际有 121 个 IES，
   其中 LED Linear Light 分类下 NLI496 系列（15W/30W × 4000K/6500K）即室内线性灯，
   CDN 直链可批量下载；LED Panel Light 分类下 NPN450 系列为面板灯。
2. 「三条路均需额外投入」→ 已打通第四条路：**IES-Library 聚合库**
   （https://ieslibrary.com ，98 家厂商 9 万+ 文件，含 OPPLE 684 个）。
   目录 API `POST /browse/api/pageIes/data.json`（参数 page/pageSize/manufactur）可全量拉取；
   下载走 cHash 中转页两跳（脚本 `_redownload_opple2.py` 已封装）。文件为厂商原文件
   （MANUFAC/TESTLAB 保留），OPPLE 全部合规。拉取/校验脚本已留在 `build/ies/linear/`。

**尺寸备注**：库存线性灯长 1145~1499mm、宽 55~249mm，无严格 1555×300 同款；
Re295 系列（245×1145mm）与 L1563（67×1487mm）最接近需求口径，型号取舍待架构师定。
