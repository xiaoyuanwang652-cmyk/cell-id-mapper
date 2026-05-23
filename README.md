# cell-id-mapper

[![测试](https://github.com/xiaoyuanwang652-cmyk/cell-id-mapper/actions/workflows/test.yml/badge.svg)](https://github.com/xiaoyuanwang652-cmyk/cell-id-mapper/actions)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

癌细胞系 ID 跨数据库映射工具，支持 **DepMap**、**GDSC (COSMIC)** 和 **Sanger (Cell Model Passports)** 三大数据库之间的标识符互转。

如果你在 DepMap 的 CRISPR 数据里看到 A549 叫 `ACH-000681`，在 GDSC 的药敏数据里又叫 COSMIC `905949`，在 Sanger 那边又变成 `SIDM00903`——这个工具就是帮你解决这个问题的。

## 为什么需要它

三大癌症基因组学资源对同一批细胞系使用了三套不同的 ID 体系，手动核对繁琐且容易出错。这个工具一行代码就能完成跨数据库 ID 互转。

## 快速开始

```bash
pip install cell-id-mapper
```

### 命令行

```bash
# 用任意一种 ID 查找
cell-id-mapper lookup A549
cell-id-mapper lookup ACH-000681
cell-id-mapper lookup 905949          # COSMIC ID

# 模糊搜索
cell-id-mapper search MCF

# ID 类型互转
cell-id-mapper convert A549 --from name --to cosmic

# 列出某个癌种的所有细胞系
cell-id-mapper lineage Breast

# 查看覆盖率统计
cell-id-mapper stats
```

### Python API

```python
from cell_id_mapper import load_mapper

mapper = load_mapper()

# 精确查找
cl = mapper.from_name("A549")
print(cl.depmap_id)   # ACH-000681
print(cl.cosmic_id)   # 905949
print(cl.sanger_id)   # SIDM00903
print(cl.lineage)     # Lung

# 便捷转换方法
mapper.ach_to_cosmic("ACH-000681")     # "905949"
mapper.name_to_ach("A549")             # "ACH-000681"
mapper.cosmic_to_name("905949")        # "A549"

# 模糊搜索
hits = mapper.search("colo")
for h in hits:
    print(h.cell_line_name, h.lineage)

# 按癌种或疾病筛选
lung_cells = mapper.by_lineage("Lung")
melanomas = mapper.by_disease("Melanoma")
```

## 数据来源

映射表由以下数据库合并、去重、过滤得到：

| 数据库 | ID 格式 | 示例 |
|--------|---------|------|
| [DepMap](https://depmap.org) | ACH-XXXXXX | `ACH-000681` |
| [GDSC / COSMIC](https://cancer.sanger.ac.uk/cosmic) | 纯数字 | `905949` |
| [Sanger Cell Model Passports](https://cellmodelpassports.sanger.ac.uk) | SIDMXXXXXX | `SIDM00903` |

内置 **2,200+ 条癌细胞系**，覆盖 37 个癌种。如需基于最新官方数据重构建：

```bash
# 1. 从 https://depmap.org/portal/download 下载 Model.csv
# 2. 从 https://cellmodelpassports.sanger.ac.uk/downloads 下载 model_list_*.csv
# 3. 把两个文件放到 data/ 文件夹，然后运行：
python scripts/build_bundled_data.py
```

## 项目结构

```
cell-id-mapper/
├── src/cell_id_mapper/
│   ├── __init__.py              # 包入口
│   ├── mapper.py                # 核心 CellLineMapper 类
│   ├── cli.py                   # 命令行接口
│   └── data/
│       └── mappings.csv         # 内置映射表
├── data/                        # 原始下载数据（不含 .csv）
│   └── .gitkeep
├── scripts/
│   └── build_bundled_data.py    # 从本地源文件重构建映射表
├── tests/
│   └── test_mapper.py           # 单元测试
├── .gitignore
├── pyproject.toml
├── LICENSE
└── README.md
```

## 环境要求

- Python 3.10+
- 无强制依赖（仅使用标准库）
- 可选：`pandas`、`openpyxl`（用于本地数据构建脚本）

## 许可证

MIT。详见 [LICENSE](LICENSE)。
