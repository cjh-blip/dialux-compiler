# MVP3 阶段性展示方案（空间换时间）

> 2026-09-06 架构师定调：先展示已有结果，换取后续开发时间。
> 灯具只是 DIALux 自动化的一个小点，后续还有大量功能要开发。

## 一、已有可展示成果（全部真机验证过）

| # | 成果 | 证据 | 演示方式 |
|---|------|------|---------|
| 1 | **DWG → DIALux 建房间壳全自动**（保底路径） | 9.91 s 全程，STF 字节一致 + 顶点 11/11 回环 | `python scripts/demo_run.py` |
| 2 | **灯具原型导入成功**（真实会员厂商 NVC IES） | 无 paywall，CatalogListBox 有 NPTLED351 | 悬浮部件/真机 |
| 3 | **灯具自动排布落盘**（1 套 12 盏，房间中心） | 拆包 LuminaireElement=24 / FieldArrPos=12 | 真机 demo_room.evo |
| 4 | **执行器内核 P2**（ActionPlan 驱动） | 真实图 55 条全派发、28 盏 stub 收集、进度 0→100% | `--execute` CLI |
| 5 | **保存弹窗自动应答**（BetterGI 思路 UIA 版） | 门禁 221 passed + ruff 0 | 自动，无需演示 |

## 二、演示叙事（给评审看的一页）

1. **输入**：两张 DWG（房间图 + 灯具图，照实房间画的）
2. **解析**：28 盏灯具（16 筒灯 + 12 线性灯）坐标/类型全提取，挂载高度回填 2.8m
3. **建壳**：一条命令，DIALux 里房间建好并存 .evo
4. **放灯**：导入真实 NVC 灯具型号 → 自动排布进房间（当前 12 盏演示；28 盏两批放是下一步）
5. **承诺**：灯具精确坐标 / 照度计算 / 报告导出 = 后续开发时间换来的功能

## 三、「空间换时间」的策略含义

- **现在交付**：房间壳 + 灯具进房（位置由 DIALux 算，均匀分布）——已是「能看、能跑、可录屏」的形态
- **换取的时间**：落位口径（精确图纸坐标）、线性灯配光文件、照度计算、报告导出、
  视觉自愈（MVP5）、家具占位（P3）都是后续待开发
- **口径**：演示时如实说「灯具已进房、位置是 DIALux 自动排布（非图纸精确原位）」，
  不夸大；型号是真实 NVC 光数据（非伪造）

## 四、演示清单（10 分钟内）

```bash
# 1. 解析 + 建壳 + 放灯（保底路径）
python scripts/demo_run.py

# 2. 悬浮小部件（贴 DIALux 窗口，显示进度）
python -m src.ui.overlay

# 3. ActionPlan 驱动（55 条动作全派发）
python src/main.py --dwg 布局图.dwg --dwg-lighting 灯具图.dwg \
  --config tests/fixtures/sample_parse_config.json \
  --out build/demo_ir.json --execute

# 4. 拆包验收（灯具在 ProjectData.dat）
python -c "import zipfile; z=zipfile.ZipFile('build/demo_room.evo'); \
  d=z.read('Project/ProjectData/ProjectData.dat').decode('utf-8','replace'); \
  print('LuminaireElement=', d.count('LuminaireElement'))"
```

## 五、演示执行清单（2026-09-07 更新，全项已真机验证）

### 三段式演示（评审前照此走）

| 段 | 内容 | 工具/命令 | 状态 |
|----|------|----------|------|
| ① | DWG → DIALux 建房间壳（全自动） | `python scripts/demo_run.py`（9.91s 实测） | ✅ 可现场真跑 |
| ② | 12 盏 NVC 筒灯在房间里 | 打开 `build/demo_room.evo`（已放好 12 盏） | ✅ 已就位 |
| ③ | 线性灯文件+导入已通（收尾尾巴） | `build/ies/linear/` 24 个 IES；OPPLE Re295 导入已验证 | ✅ 已验证 |

### 现场检查清单（演示前 5 分钟过一遍）

1. [ ] DIALux 已启动、demo_room.evo 已加载（12 盏 NVC）
2. [ ] `python scripts/demo_run.py` 能跑完（解析 2.6s + STF 0.5s + 落地）
3. [ ] `build/ies/linear/` 24 个 IES 在（opening `_下载报告.md` 一页讲清）
4. [ ] OPPLE Re295 已在 CatalogListBox（`LEDPanelRc-S-Re295-30W-4000-WH-U19`）
5. [ ] 说话口径：灯具位置是 DIALux 自动排布（非图纸精确原位），型号是真实会员厂商光数据
6. [ ] 不承诺：28 盏全放、精确图纸坐标、家具进 DIALux（都是后续）

### 录屏

- 工具：Xbox Game Bar（Win+G）
- 录 ①② 两段全程（每段 1-2 分钟），存 `build/demo_screenrecord/`
- ③ 作为 PPT 一页讲，不录

### 风险与兜底（都实测过）

- 演示前若 DIALux 弹「首次使用向导」：勾「不再显示此页」+ Next→Finish（见 p31 解法）
- 若 demo_run 导入卡住：等 15s 标题不变判失败，属已知边界（对话框残留用 autosave 自动应答）
- 线性灯若评审追问现场放：已可导入，但**不现场放**（避免第二套排布叠加风险，说明「下一步就好」）
