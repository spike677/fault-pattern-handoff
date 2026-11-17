# MECH-v0.5 公开开发目录

本次公开发布来自本地审计提交 `5740b3513cc898e002ccba1283e1533234341596`，公开父提交为 `1cb47b7331458fe837cde25f02aad6dfe0af3f76`。只发布代码、定义、合成回归和聚合复验摘要；原件、答案、原始答卷、真实案例与标签的关联以及 F 预筛材料均由本地保管。

目录有 **45 个定义入口：原九条、31 个新增开发定义、5 个禁用分类的研究条目**。原九条模式字典保持不变；新增定义登记为 `development_knowledge`，不代表正式泛化准入，也不构成 45 个互斥根因。

- [本轮 Work / Codex 成果与成绩](V05_PUBLIC_SUMMARY.md)
- [45 条模式定义](MODES.md) · [机器目录](catalog.json) · [父类关系](parent_hierarchy.json)
- [73 条身份迁移关系](mode_id_migration.csv) · [91 组近邻比较](overlap_exclusion_matrix.csv)
- [外部知识条目](external/knowledge_items.json) · [整数地址定义与边界](reviews/integer_address_range/MODE_CARD.json)
- [公开文件清单与验证记录](PUBLIC_VALIDATION.json)

`history/normalized_mode_cards/` 的 53 个公开文件是历史身份和条件定义的索引，完整规范化证据卡保留在本地；不能把这些索引视作历史案例答案。外部 87 条知识保留经过审查的定义、条件及公开上游卡片链接，移除了原文和案例答案关系。检索共 185 个文档，命中仅提供候选，不构成证据。

## 公开复算

Python 3.10 或更新版本；仅使用标准库。以下从仓库根目录执行。Windows 初次克隆请使用 `git -c core.autocrlf=false clone --branch codex/mech-v04-stability-delivery https://github.com/spike677/fault-pattern-handoff.git`，然后在克隆目录设置 `git config core.autocrlf false`；历史冻结检查依赖文件原字节，不能用更改预期哈希来处理换行符差异。

```powershell
python -B -X utf8 classification/mech_v05/verify_public.py
python -B -X utf8 -m unittest discover -s diagnosis_mvp -p "test_*.py"
python -B -X utf8 classification/reliability_v044/public_controls.py --verify
```

从 `classification` 目录执行：

```powershell
python -B -X utf8 -m unittest test_mech_v05 test_reliability_v04 test_reliability_scoring test_reviewed_static
python -B -X utf8 -m mech_v05.cli validate-catalog
python -B -X utf8 -m mech_v05.cli search "整数地址表示范围不足" --limit 5
```

上述公开测试为 55 项分类回归（含本次 18 项）和 17 项历史兼容回归。既有算术控制为 18 个整数控制、5 个方差控制、7 条方差断言，均不计模型准确率。全量历史分类发现式测试还依赖 9 个未公开 fixture；本次在仓库外按原哈希恢复后运行 180 项分类和 17 项兼容测试，全部通过。公开仓库不能独立复算私有材料的逐案分数。

## 本地分类入口

从 `classification` 目录执行，将自己的材料和答卷保存在仓库外：

```powershell
python -B -X utf8 -m mech_v05.cli prepare <material.json> <request_directory>
python -B -X utf8 -m mech_v05.cli validate-readback <material.json> <readback.json>
python -B -X utf8 -m mech_v05.cli classify <material.json> <readback.json> <result.json>
python -B -X utf8 -m mech_v05.cli archive <material.json> <readback.json> <result.json> <archive_directory>
```

`prepare` 生成读件请求和响应结构，不调用模型；需另行获得有原件引证的答卷。分类保留机理、具体动作、因果角色和完整案件范围的区别。归档复算结果并检查已有内容，不自动上传，也不自动扩充目录。机器目录是本次审核后的版本化快照；依赖私有证据的目录构建脚本不在公开发布范围。

公开版移除了证据元数据，可能改变检索排名和读件提示。本次确认的是相同已有答卷在公开规则下的 48 个输出一致（仅目录元数据哈希变化）；本地四轮模型成绩并非公开删减版提示的一次新模型测评。全部模式的真实正反覆盖、稳定多动作分类、严格 F 和实际 GPU 执行仍未完成。
