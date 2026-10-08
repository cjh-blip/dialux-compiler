# 软件知识库（照明链的"外部记忆"）

> 建立：2026-10-08 ｜ 起因：智能体不了解 DIALux 操作细节，且会话结束后不记得

## 一、这套东西解决什么

照明项目的软件开发（optiflow / dialux-compiler）由智能体执行，但有两处硬伤：

1. **软件操作知识不在智能体脑子里。** DIALux evo 的按钮叫什么、菜单在哪、某个动作的前置条件是什么，模型没学过，只能猜。
2. **会话一结束就忘。** 上一轮试出来的操作路径，下一轮重新摸索。

这两件事的解法不是"让模型记住"，而是**把知识写进仓库，让它每轮都能查到**。

会话记忆会丢，仓库里的文件不会。知识跟着仓库走，就跟着补丁一起被带到 Windows 侧，谁执行都能读同一份。这是唯一稳的做法。

## 二、目录

```
03_软件知识库/
├── DIALux_evo_官方KB_EN/      DIALux 官方支持站英文知识库（203 篇）
│   ├── README.md              分类索引（分类 -> 文章）
│   ├── articles/              203 篇 Markdown，一篇一文件
│   └── _raw_index.json        抓取清单（标题/分类/来源 URL/更新日期）
└── _crawler/
    ├── crawl_dialux_kb.py     抓取脚本，可重跑更新
    └── last_home_snapshot.html  抓取时的站点首页快照
```

## 三、怎么用

**给智能体用**：让它先读 `DIALux_evo_官方KB_EN/README.md` 定位分类，再打开对应 articles 文件。文件里带来源 URL，需要核对时能回原站。

**给人用**：按分类浏览，Calculation、Construction、Import/Export 这几类最接近日常操作。

**更新**：重跑 `_crawler/crawl_dialux_kb.py <输出目录>`，脚本会重新发现文章并覆盖。抓取有 0.35 秒间隔，203 篇约 3 分钟。

## 四、与我们有直接关系的六篇（先看这几篇）

| 文章 | 为什么重要 |
|:--|:--|
| **STF format - Data exchange DIALux** | 整个机读链的格式根据。文中提到 DIAL 可免费提供 STF 接口文档，联系人 `Bremecker@dial.de`，这是拿格式规范的正门 |
| Why is a building created for each room after the STF import? | 直接对应我们 STF 导入时遇到的建筑层级问题 |
| How does the luminaire replacing work? | 与链上"更换该类型的所有灯具"这一步的操作依据 |
| UGR / Planning with the UGR Method | UGR 的口径与算法前提，报表取不到 UGR 时的对照材料 |
| Result tool（results overview） | 结果面板的字段含义，和结果包 schema 的字段对得上 |
| Calculation method in evo | 计算内核怎么算，判断结果可信度的底料 |

## 五、边界说明

- 来源是**官方英文支持站**，不是论坛二手内容，可信度较高，但仍属"官方答疑"性质，不是规范文本；涉标准限值一律回到 GB/T 或 EN 原文
- 抓取时点 2026-10-08，站方后续会更新文章
- 中文站（dialux.com 中文页、dialux.net.cn）另有内容，本轮未抓，需要再说

## 六、待办

- [ ] 补抓中文官方内容与官方教育课程（含可下载视频、项目文件、图纸）
- [ ] 决定是否纳入 dialux-compiler 仓库的 docs/，让 Windows 侧智能体随仓库同步（需 cjh 拍板后再推）
- [ ] STF 接口文档可向 DIAL 索取，是否发邮件由 cjh 定
