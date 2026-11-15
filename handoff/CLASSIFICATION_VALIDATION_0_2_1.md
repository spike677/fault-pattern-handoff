# 0.2.1 验证准备与资料分流

实际工程目录为 `D:\project\精度\fault-pattern-handoff`。本轮基于 `f0b6c46ade3739d098aef2017c5881498a1fdcf9`，工作分支为 `codex/mechanism-classification-pilot`。候选模式为目录 0.2 的七条，判定与评分使用 0.2.1。

## A　七条真实未见验收准备

已核对候选代码、目录、评分器和执行提示的哈希。重新运行本地分类回归，29 项通过。正式评估的模型及工具配置按独立执行环境中实际可见的信息冻结，内部部署 ID 不可见时如实记录。当前未取得独立整理者封存的 A 包和隔离见证，尚无真实样本得分。[候选哈希](../classification/validation_0_2_1/candidate_freeze.json) · [执行提示](../classification/validation_0_2_1/PROMPT.md) · [角色、封存及验收命令](../classification/validation_0_2_1/READINESS.md)

## B　元数据分流与缺口

| 素材 | 本地核查 |
| --- | --- |
| `fault_review` 固定编目 | 1,184 条推理编目，含一个跨库指针，另有 221 条训练编目。1,157 个标准来源引用，21 个被多条目共用。14 条有明确可归属的同源键，13 条能直接对齐已审材料。 |
| 555 份审计记录 | 546 个明确 Issue 键，539 条记录带 528 个关联 PR 键。539 条存在活动引用缺口，555 条的机理完整性仍为 `NOT_ASSESSED`。 |
| 合并清单 | 仅以有明确归属的键做机械归并，共 1,945 组，含 7 个多记录组。当前未找到精确跨库同键；1,390 条缺少可用的明确归属键。源文档中的广义引用和变体关系只作为复核提示。 |
| 开发暴露 | 39 条记录、36 个机械组与已见开发键或具名审查记录对齐，进入开发用途。其余 1,920 条待独立整理，暂存核身份和暴露状态。12 个组带已暴露材料的引用提示，供整理者逐案复核。 |

指针作为索引保存。归并组用于阻止按单条记录拆分，独立事件家族由整理者按原件和同源关系核实。未匹配到开发暴露键的材料需继续核对。当前七条留出池与后续版本保留池的正式分配均待独立整理。[编目元数据](../classification/pools_0_2_1/fault_review_inventory.json) · [555 元数据](../classification/pools_0_2_1/audit_555_inventory.json) · [分流状态](../classification/pools_0_2_1/pool_status.json)

独立整理者先核事件、PR、回移、共享缺陷源码及带答案材料的关联，再给家族登记一种用途。开发扩展池供修订使用，当前留出池服务 0.2.1，保留池供新增模式后的验证。与已见材料有答案共享的连通组归入开发。缺少共同身份确认的记录先保留待查。最终用途、队列及 B 由整理者保管，真实 A 只在冻结后交执行者。555 的材料状态可辅助补证排序，实际叶级正例和缺证配额仍需按可见材料核定。

同时利用已见材料形成四类覆盖记录。数值表示与计算、控制传播与分支、一般地址计算、同步与生命周期列为优先研究方向。每个候选标明独立动作、作用范围、与既有模式的近邻区别及需要的验证。看到真实失败后先判是读件、定义、规则实现、证据还是计分的问题。只有已证实的目录缺口进入扩展提议。目录扩展后使用原测试回归并保留新的未见家族验收。[全局机理缺口与分批准则](../classification/pools_0_2_1/MECHANISM_GAPS.md)

## 复跑元数据核验

在交接仓根目录运行。两个来源的重建均已通过逐字节校验。合并脚本仅接受索引与暴露键，按明确的同源键传播已见标记。

```powershell
python -B -X utf8 classification/pools_0_2_1/build_fault_review_inventory.py --project-root 'D:\project\精度' --check
python -B -X utf8 classification/pools_0_2_1/build_audit_555_inventory.py --check
python -B -X utf8 classification/pools_0_2_1/build_pool.py --exposures classification/development_lineage.json classification/pools_0_2_1/fault_review_inventory.json classification/pools_0_2_1/audit_555_inventory.json
```
