# IR Schema 导读 (中间表示契约)

> **权威定义是 `spec/ir.schema.json`**（JSON Schema draft-07，`$id`
> `https://dialux-compiler.local/ir-schema.v0.1.json`），也是运行时唯一被加载来校验的那份
> （`src/validator/__init__.py::load_schema` → `validate_ir`）。
> 本文件是它的导读：示例、必填清单、校验规则说明。两者不一致时以 json 为准，并按 json 修本文件。
> 版本: 0.1。所有 Parser 输出必须可序列化为该结构；Planner 只消费该结构。
> 坐标系：米制、右手系、Z 向上；角度单位度。

## 结构示例（字段与 spec/ir.schema.json 对齐）

```json
{
  "schema_version": "0.1",
  "project": {
    "name": "string",
    "source": {"dwg": "path", "xlsx": "path"},
    "units": "m"
  },
  "storeys": [
    {
      "level": 3,
      "elevation": 0.0,
      "name": "3F",
      "spaces": [
        {
          "id": "OpenOffice-01",
          "name": "string",
          "polygon": [[0, 0], [10, 0], [10, 8], [0, 8], [0, 0]],
          "elevation": 0.0,
          "ceil_h": 2.8,
          "floor_reflect": 0.2,
          "wall_reflect": 0.5,
          "ceil_reflect": 0.7,
          "openings": [
            {"type": "window", "polygon": [[0, 0], [1.5, 0], [1.5, 1.5]],
             "height": 1.5, "transmittance": 0.7}
          ],
          "luminaires": [
            {
              "symbol": "LED-PNL-600",
              "catalog_match": true,
              "x": 5.0, "y": 4.0, "z": 2.79,
              "kind": "area",
              "dims": {"w_mm": 600.0, "h_mm": 600.0},
              "mount": "recessed",
              "params": {"power": 36, "flux": 3600, "CCT": 4000}
            }
          ]
        }
      ]
    }
  ],
  "_meta": {"rooms": 1, "luminaires": 0, "rooms_closed": 1, "dxf_units": "cm"}
}
```

## 必填字段（json schema 的 `required`）

| 对象 | required |
|---|---|
| 根 | `schema_version`、`project`、`storeys` |
| `project` | `name`、`source`、`units` |
| `Storey` | `level`、`spaces` |
| `Space` | `id`、`polygon`、`luminaires`（**空房间也必须写 `"luminaires": []`**） |
| `Luminaire` | `symbol`、`x`、`y`、`z`、`catalog_match` |

> `catalog_match` 语义（2026-09-07 架构师定，保持现状）：**解析期占位**——join.py 无条件
> 写 `True`，不代表已与真实灯具表比对过。MVP3「型号匹配」验收不得拿这 28 个 `true` 当
> 已匹配证据；真实比对是后续功能。
| `Opening` | 无 required |

## 关键约束（都写死在 json 里，导读别写反）

- `schema_version` 必须匹配 `^0\.1(\.\d+)?$`；`project.units` 枚举 `m/mm/cm/inch`。
- `Point2` = 2~3 个 number（允许带 z）；`Polygon` = `minItems: 3` —— **示例里不要只给 2 个点**。
- 闭合点算在顶点数里：`[[0,0],[10,0],[10,8],[0,8],[0,0]]` 是 5 个点 / 4 个唯一顶点。
- `ceil_h` 是 `exclusiveMinimum: 0`；`elevation` 无下限。
- **反射比挂在 `Space`**（`floor_reflect`/`wall_reflect`/`ceil_reflect`，各 0~1）；`Storey` 上
  只有 `level`/`elevation`/`name`/`spaces`，**没有反射比字段**。
- `Opening` 的字段是 `type`/`polygon`/`height`/`transmittance`（0~1），**没有** `wall_segment`、`sill`。
- `Luminaire` 的 `mount` 枚举 `recessed/surface/pendant/wall/floor/other`；`params`、`attrs` 是自由 object。
- **`Luminaire.kind`**（2026-09-05 加）枚举 `point/linear/area/unknown`，由解析器按 DXF 图元显式声明，
  **下游禁止靠 `symbol` 前缀反推**：`point`←CIRCLE，`linear`←长宽比 ≥3 的 RECT，`area`←长宽比 <3 的 RECT，
  `unknown`←INSERT 块引用（块名不携带几何）。分类函数 `src/parser/dxf.py::classify_rect_luminaire`。
- **`Luminaire.dims`**（2026-09-05 加）是选型尺寸，**单位毫米**：`point` 给 `radius_mm`，
  `linear`/`area` 给 `w_mm`+`h_mm`。由 `src/planner/join.py::_dims_from_attrs` 从 parser 的 `attrs`
  搬运并圆到 3 位小数。此前 `attrs` 在 join 阶段被整个丢掉，选型拿不到尺寸。
- **`Luminaire.z` 是安装高度**（米，楼面为 0）。2D DWG 没有高度，解析器一律写 0，
  由 `src/planner/mount.py::assign_mount_heights` 按 `space.ceil_h` × `mount` 回填。
  `z=0` 表示尚未回填，validator 规则 7 会报。
- 各级 `additionalProperties` 都是 `true`，所以未声明的扩展键能通过校验。现役产物里就有几个：
  `space.furniture`（家具几何列表，元素包含 `id`、`room_id`、`polygon`、`bbox`、`area_m2`、
  `kind`、`height_m`、`rotation`、`confidence`，以及可选来源字段，
  `src/exporter/stf.py` 校验前 pop 掉）、
  `_meta.furniture` / `_meta.room_notches_removed` / `_meta.rooms_with_sawtooth`。
  注意 `origin` **不是** IR 键：它是 `ParseConfig` 的字段（`src/parser/dxf.py:91`，用于坐标平移），
  parser 写进 `project` 的只有 `name`/`source`/`units`。
- `_meta` 显式声明的只有 `rooms`/`luminaires`/`rooms_closed`/`dxf_units`（均为 `integer ≥ 0`
  或 string）。`_meta.luminaires` 的回填缺陷已于 2026-09-04 修复
  （`src/planner/join.py` 末尾按 `storeys[*].spaces[*].luminaires` 求和）。
- **`Space` 上没有 `kind` 字段**（`Luminaire` 上有，别混）：家具记录的 `kind` 位于
  `space.furniture[]`，旧家具伪 space 仍靠 `name` 前缀 `家具_` 识别（`stf.py::FURNITURE_NAME_PREFIX`），
  仅作为预览兼容层，执行层不应把它们当房间。

## 校验规则 (validator)

> 2026-09-05 实核（规则 ≠ 实现，引用前先看这几条）：
> - 默认执行的是 jsonschema 校验 + 规则 **1、2、3、4、5、7、8**（编号不连续，权威表在
>   `validate_ir` 的 docstring 里）。
> - 规则 2 的「不自交」**未实现**：`_rule2_area_range` 只查面积区间，bowtie 自交多边形按 |面积| 非零放过。
> - 规则 6 由可选函数 `validate_with_luminaire_xlsx(ir, specs_by_symbol)` 提供，需额外传入 xlsx
>   规格字典，因此不在单参数的 `validate_ir` 里；**全仓仍没有任何调用者**，见
>   `KANBAN.md`「遗留与待决」。

1. `polygon` 至少 3 个顶点，允许闭合容差 (首尾距离 < 1mm 视为闭合)。
2. 多边形不自交；面积 > 0 且在合理区间 (0.5 ~ 10000 m²)。
3. 所有 `luminaire` 坐标必须落在所属 `space.polygon` 内 (含边界)。
4. `mount=recessed` 时 `z <= ceil_h`；`mount=surface` 时 `z <= ceil_h + 0.3`。
5. `catalog_match=false` 必须标记，交人工确认，禁止静默继续。
6. 灯具 `params.power/flux` 与 xlsx 表一致；不一致以 xlsx 为准并告警（**零调用者**，见上）。
7. 吊顶类灯具（`mount` ∈ `recessed/surface/pendant`）的 `z` 不得停留在 0 ——
   `LUM_MOUNT_Z_UNSET`（ERROR）。规则 4 只查上溢，z=0 曾静默通过。
8. `kind` 与 `dims` 必须自洽：`point` 要有 `radius_mm`，`linear`/`area` 要有 `w_mm`+`h_mm` ——
   `LUM_KIND_DIMS_MISMATCH`（WARNING）。`kind` 缺失时不报（可选字段）。
