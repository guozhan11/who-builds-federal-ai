# Tableau 操作指南：Proposal 的三个 Prototype

三张图用了三种不同的图形，都只读 `data/processed/` 里的两个表：

| Prototype | 图形 | 数据文件 | 核心变量 |
|---|---|---|---|
| 1 · AI 类型 × 开发阶段 | 100% 堆叠条形图 | `ai_use_cases.csv` | `year`, `stage`, `classification`, `record_id` |
| 2 · 各部门自研还是外购 | 点图（每个部门两个点） | `ai_use_cases.csv` | `year`, `stage`, `build`, `agency`, `record_id` |
| 3 · 技术人员的月度招聘 | 折线图 | `workforce.csv` | `measure`, `period`, `department_code`, `occupation`, `n` |

R 预览图在 `proposal/figures/` 下，代码在 `proposal/prototype_previews.Rmd`，可以对照着做。Proposal 的作业说明写了 prototype 不要求达到发表质量，所以标题、配色、排序做对就够了，字体和间距不用抠。

每一节最后都有一张**核对表**，是用 R 从同一个 CSV 算出来的。Tableau 里的数字应该完全一致；对不上的话，通常是筛选条件漏了一个。

---

## 0. 准备工作（三张图通用）

1. **连接数据。** Tableau → Connect → To a File → Text file，先选 `ai_use_cases.csv`。做 Prototype 3 时，再新建一个数据源（Data → New Data Source）连 `workforce.csv`。两个数据源之间**不要建关系**，项目里 OMB 和 OPM 本来就不合并。
2. **检查字段类型。** 在 Data Source 页面：
   - `ai_use_cases.csv`：`year` 应为 Number (whole)。其余都是 String。
   - `workforce.csv`：`n` 应为 Number (whole)；`period` 也会被识别成数字（比如 202501），保持数字就行，筛选时用范围更方便。`department_code` 等都是 String。
3. **空值。** CSV 里的空单元格在 Tableau 里显示为 `Null`，筛选时把 Null 排除即可。
4. **颜色**（和整个项目的配色系统一致）：

   | 用途 | Hex |
   |---|---|
   | AI、外购、延迟辞职（主色） | `#eb6834` |
   | 深橙（Deployed） | `#b8461c` |
   | 浅橙（Pre-deployment） | `#f5b08f` |
   | 人员、自研、退休 | `#2a78d6` |
   | 浅蓝（Quit） | `#9ec5f4` |
   | 紫（裁员 RIF） | `#4a3aa7` |
   | 灰（合作开发、其他） | `#c9c7c0` |

   设置方法：点 Color legend 右上角 ▼ → Edit Colors → 逐项点选 → Choose Color → 输入 Hex。

5. **计数用哪个字段。**
   - `ai_use_cases.csv` 一行就是一个用例，用 `CNT([record_id])` 计数。
   - `workforce.csv` 一行**不是**一个人，而是一个人数，必须用 `SUM([n])`。用 CNT 会算错。

---

## Prototype 1 · 哪类 AI 走到了部署？

**问题：** 2025 年的在用 AI 用例里，不同技术类型分别处在哪个开发阶段？
**图形：** 横向 100% 堆叠条形图。

### 筛选（Filters）

把以下字段拖到 Filters：

| 字段 | 设置 |
|---|---|
| `year` | 选 2025 |
| `stage` | 只勾 Pre-deployment、Pilot、Deployed（排除 Retired 和 Null） |
| `classification` | 只勾 Agentic AI、Classical ML、Computer Vision、Generative AI、NLP（排除 Other、Reinforcement Learning 和 Null；Reinforcement Learning 只有 12 个在用用例，样本太小） |

### 计算字段（Analysis → Create Calculated Field）

**Deployed share**（用于排序）：
```
SUM(IF [stage] = "Deployed" THEN 1 ELSE 0 END) / COUNT([record_id])
```

**Type label**（在类型名后面加上用例数）：
```
[classification] + "  (" + STR({FIXED [classification] : COUNT([record_id])}) + ")"
```
> FIXED 计算会忽略普通筛选，所以要在 Filters 里右键 `year` 和 `stage` → **Add to Context**，让它们先生效。否则括号里的数字会偏大。

### 搭图

1. **Rows：** `Type label`
2. **Columns：** `CNT(record_id)` → 右键 → Quick Table Calculation → **Percent of Total** → 再右键 → Edit Table Calculation → Compute Using 选 **Specific Dimensions**，只勾 `stage`。这样每一行加起来是 100%。
3. **Marks** 选 Bar；把 `stage` 拖到 **Color**。
4. **颜色：** Pre-deployment `#f5b08f`，Pilot `#eb6834`，Deployed `#b8461c`。在 Color legend 里拖动排序，调成 Pre-deployment → Pilot → Deployed，这样条形从左到右是由浅到深。
5. **标签：** 按住 Ctrl（Mac 是 Option），把 Columns 上的百分比胶囊拖到 **Label** 复制一份。右键 Label 胶囊 → Format → Numbers → Percentage，0 位小数。
6. **排序：** Rows 上的 `Type label` → 右键 → Sort → Sort By **Field** → `Deployed share` → Descending。计算机视觉应该排在最上面，Agentic AI 在最下面。
7. **标题：** "Agentic AI is furthest from deployment; computer vision is closest"。副标题写：Share of 2025 federal AI use cases at each stage, by type of AI. Number of use cases in parentheses.

### 核对表（每行加总 = 100%）

| 类型 | 用例数 | Pre-deployment | Pilot | Deployed |
|---|---|---|---|---|
| Computer Vision | 291 | 34% | 10% | 56% |
| NLP | 452 | 42% | 13% | 44% |
| Classical ML | 1,112 | 53% | 14% | 33% |
| Generative AI | 853 | 52% | 18% | 30% |
| Agentic AI | 117 | 68% | 15% | 17% |

---

## Prototype 2 · 点图：各部门的 AI 是买的还是自己做的？

**问题：** 在试点和已部署的 AI 里，各部门外购和自研的比例分别是多少？
**图形：** 点图，每个部门一行两个点：橙色是外购比例，蓝色是自研比例，中间用灰线连起来（也叫 dumbbell 图）。两点之间的距离就是差距；剩下的部分是"合作开发"。

### 为什么只看试点和已部署

OMB 只要求试点（Pilot）和已部署（Deployed）的用例填 `contracting_usage`，也就是 CSV 里的 `build`。算上其他阶段，大部分会是空值。这一点要写进图注。

### 筛选

| 字段 | 设置 | 是否 Add to Context |
|---|---|---|
| `year` | 2025 | 是 |
| `stage` | 只勾 Pilot、Deployed | 是 |
| `build` | 排除 Null（一共排除 36 个） | 是 |
| `agency` | **Condition** 选项卡 → By formula：`COUNT([record_id]) >= 20` | 否 |

最后一行只保留有 20 个以上用例的部门。因为前三个筛选都已 Add to Context，这里数的是"2025 年试点加已部署、且填了 build 的用例"。

### 计算字段

**Vendor share**：
```
SUM(IF [build] = "Vendor" THEN 1 ELSE 0 END) / COUNT([record_id])
```

**In-house share**：
```
SUM(IF [build] = "In-house" THEN 1 ELSE 0 END) / COUNT([record_id])
```

**Agency label**：
```
[agency] + "  (" + STR({FIXED [agency] : COUNT([record_id])}) + ")"
```

**Overall vendor share**（全部部门的平均值，用作参考线）：
```
{FIXED : SUM(IF [build] = "Vendor" THEN 1 ELSE 0 END) / COUNT([record_id])}
```
> FIXED 在部门的 Condition 筛选之前计算，所以这里算的是全部 1,444 个用例的外购比例，而不是只算 20 个用例以上的部门。

### 搭图

1. **Rows：** `Agency label`
2. **Columns：** 把 `Measure Values` 拖到 Columns。Tableau 会自动加一个 `Measure Names` 筛选，在里面只保留 `Vendor share` 和 `In-house share`。
3. **Marks** 选 **Circle**；把 `Measure Names` 拖到 **Color**。颜色：Vendor share `#eb6834`，In-house share `#2a78d6`。点可以调大一些：Size 拉到大约 2/3。
4. **连接线（可选，但能让图更好读）：**
   - 再拖一次 `Measure Values` 到 Columns，Columns 上会出现第二个 `Measure Values` 胶囊。
   - 在 Marks 区切到第二个 `Measure Values` 的卡片，把 Marks 类型改成 **Line**，把 `Measure Names` 拖到 **Path**，颜色设为灰色 `#e6e5e0`，线加粗一些。
   - 右键 Columns 上第二个胶囊 → **Dual Axis**，再右键顶部的轴 → **Synchronize Axis** → Hide Header。
   - 如果线盖住了点：右键顶部轴 → Move marks to back。
5. **坐标轴：** 右键底部轴 → Edit Axis → Fixed，范围 0 到 1；格式设为百分比，0 位小数。轴标题写 "Share of the agency's pilot and deployed AI use cases"。
6. **排序：** `Agency label` → Sort → By Field → `Vendor share` → Descending。DOJ 在最上，NASA 在最下。
7. **参考线：** Analytics 面板 → 把 **Reference Line** 拖到 Vendor 那条轴 → Scope 选 Entire Table → Value 选 `Overall vendor share`（Average）→ Label 选 Custom，写 "All agencies: <Value> bought"。线型设为橙色虚线。R 预览图是把"All agencies"做成单独一行，在 Tableau 里用参考线更简单，两种做法都可以。
8. **标题：** "Some agencies buy most of their AI; others build most of it"。

### 核对表

全部部门（1,444 个用例）：外购 38%，自研 35%，合作开发 27%。

| 部门 | 用例数 | 外购 | 自研 |
|---|---|---|---|
| DOJ | 188 | 81% | 7% |
| VA | 159 | 67% | 19% |
| SSA | 31 | 48% | 32% |
| DOE | 176 | 44% | 28% |
| DHS | 118 | 37% | 19% |
| SEC | 25 | 32% | 20% |
| TREAS | 48 | 27% | 40% |
| HHS | 255 | 20% | 32% |
| STATE | 28 | 18% | 29% |
| DOL | 23 | 13% | 52% |
| USDA | 86 | 13% | 60% |
| DOI | 129 | 11% | 84% |
| FRB | 23 | 9% | 91% |
| NASA | 47 | 2% | 87% |

---

## Prototype 3 · 折线图：机构还在招技术人员吗？

**问题：** 2025 年 1 月以后，联邦机构每月招多少技术和数据类员工？
**图形：** 折线图，横轴是月份（2024 年 1 月到 2026 年 7 月），纵轴是每月入职人数，外加一条 2024 年月均值的虚线。
**数据源：** `workforce.csv`

### 筛选

| 字段 | 设置 | 是否 Add to Context |
|---|---|---|
| `measure` | 只勾 hires | 是 |
| `department_code` | 排除 DOD（Exclude） | 是 |
| `occupation` | 排除 Other（保留六个技术序列：IT management、Data science、Computer science、Statistics、Mathematical statistics、Operations research） | 是 |

> 为什么排除 DoD：国防部有几个下属单位没有提交 2026 年 6–7 月的数据，保留它会让最后两个月的数字偏低。

### 计算字段

**Month**（`period` 是 202401 这样的数字，直接当横轴会让 202412 和 202501 之间出现一段空白，所以先转成日期）：
```
DATEPARSE("yyyyMM", STR([period]))
```

**Average 2024**（参考线用）：
```
{FIXED : SUM(IF YEAR([Month]) = 2024 THEN [n] END)} / 12
```

### 搭图

1. **Columns：** `Month` → 右键 → 选下面那组里的 **Month**（连续的绿色胶囊，不是离散的蓝色胶囊）。
2. **Rows：** `SUM(n)`。注意是 SUM，不是 CNT。
3. **Marks** 选 **Line**；颜色 `#2a78d6`。想显示每个月的点的话：Color → Markers 选中间那个带点的样式。
4. **参考线：** Analytics → Reference Line 拖到纵轴 → Scope：Entire Table → Value：`Average 2024`（Average）→ Label：Custom "2024 average: <Value> a month"，灰色虚线。
5. **（可选）2025 年 1 月 20 日的竖线：** Analytics → Reference Line 拖到横轴 → Value 选 Constant，填 2025-01-20，灰色点线。
6. **标注：** 右键 2025 年 9 月附近的点 → Annotate → Area，写 "Feb 2025–Apr 2026: 49 a month"。
7. **纵轴：** 从 0 开始；轴标题 "Employees hired per month"。横轴隐藏标题。
8. **标题：** "Hiring of federal technical staff fell by about 90% for more than a year"。

### 核对表（每月入职人数，六个技术序列，不含 DoD）

| 月份 | 人数 | 月份 | 人数 | 月份 | 人数 |
|---|---|---|---|---|---|
| 2024-01 | 576 | 2024-12 | 592 | 2025-11 | 48 |
| 2024-02 | 436 | 2025-01 | 594 | 2025-12 | 39 |
| 2024-03 | 401 | 2025-02 | 57 | 2026-01 | 40 |
| 2024-04 | 357 | 2025-03 | 40 | 2026-02 | 64 |
| 2024-05 | 357 | 2025-04 | 32 | 2026-03 | 77 |
| 2024-06 | 491 | 2025-05 | 39 | 2026-04 | 110 |
| 2024-07 | 440 | 2025-06 | 50 | 2026-05 | 242 |
| 2024-08 | 556 | 2025-07 | 32 | 2026-06 | 449 |
| 2024-09 | 489 | 2025-08 | 35 | 2026-07 | 402 |
| 2024-10 | 447 | 2025-09 | 59 | | |
| 2024-11 | 431 | 2025-10 | 16 | | |

2024 年月均 464 人；2025 年 2 月至 2026 年 4 月月均 49 人。

---

## 提交前

- 三张图都放进同一个 workbook（Prototype 1 和 2 用 `ai_use_cases.csv`，Prototype 3 用 `workforce.csv`），另存为 **Packaged Workbook（.twbx）**，文件名 `proposal/prototypes.twbx`。.twbx 会把数据一起打包，老师打开时不用另找 CSV。
- 每个 worksheet 的标题、坐标轴名称都用平实的英文，不要留字段名（比如不要出现 `CNT(record_id)`）。坐标轴标题可以右键 → Edit Axis 改，或者直接隐藏。
- 在 Tableau 里算出的数字和上面的核对表逐一对照，再写进 proposal。
