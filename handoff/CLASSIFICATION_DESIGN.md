# 算子精度故障分类设计

2026-11-15，北京时间｜供 `fault_pattern` 讨论的阶段草案

## 项目能力目标

面向训练与推理，建立以正确性约定和实际执行链为依据的算子精度故障模式库。新故障进入时要得到可核对的诊断入口、候选机理、支持或排除状态、未知项和下一次取证。已确认机理应能转为可复现、可审计、可恢复的注入规格。先验证分类和诊断方法，再映射原 30、计算覆盖并补齐有证缺口。[P0–P1 审查原报告](<../算子精度故障模式库_P0-P1设计审查_20261115.md>)

## 已确认的材料范围

| 原始资产 | 当前能确认的内容 |
| --- | --- |
| 原 30 条 | 固定研究提交 `510601f887f8ad174335f617a9d7e2a808ff897f` 的 `inputs/cann30_original.txt` 经核验含 30 条记录、26 个去重标题，Git blob 为 `1a058471e563941935944a6405a44c03c9b85a08`。记录混有现象、触发、实现解释和责任位置。三条同名“浮点数累加序不当”分别涉及测试参考顺序、实际累加路径和形状改变后的分派。冻结的 `declared_details` 仍待定位。[原表边界逐条审查](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md>) |
| 原 API42 | 42 个 API 输入构造条件。以原定义的适用前提和事实证据判定并独立记录覆盖。[42 与 V4 原件清单](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/baseline/knowledge/originals.json>) |
| V4/55 与实施规划 | V4 含 6 个主题、31 个条件类及 55 种构造。E1–E5 记录执行方法。历史 55 项实施说明另登记 57 条代表、46 个去重案例与 0 项实际执行验证。构造、方案与执行验收使用各自的分母。[V4 原件](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/baseline/knowledge/precision_trigger_knowledge_v4.md>) · [55 项实施与复现说明](<../55项故障_实施与现象原理复现详细说明.md>) |

30 条记录和 55 种构造可通过同一案例的证据建立多对多关联。例如同一尾块触发可同时用于检查无效元素参与、尾部漏写或上游计划错误；同一有效域机理也可出现在不同 shape、dtype 或算子。每条关系要写明输入条件事实和独立的机理证据。原 API42、V4/55、执行方法和机制 ID 分别使用原有版本与命名。未评条件记 `NOT_ASSESSED`，机制证据不足记 `UNKNOWN`。[现有稀疏条件协议](<../fault-evidence-audit-codex-initial-public-release/work/update_check_16ce36a/snapshot/faultaudit/trigger_sparse.py>)

## 暂定的分类与诊断规则

分类以**在实际路径上可独立裁判的合同破坏动作**为单位。规则卡写入对象角色、应守关系、具体破坏、适用范围、近邻、反证和版本。个案另记症状和影响、触发、诊断入口、原因和责任边界、构建、事件家族与子问题。合同族可从接口与形状、计划与分派、有效域和布局、数值计算与类型、贡献集合与重数、时序及生命周期开始试跑。

判重时先查原事件、补丁和变体，再比较机理。对象角色、合同和破坏方式等价且同一观察可以区分时可合并。相邻解释有不同必要证据、干预预测或修复责任时应分别保留，版本或平台差异必要时作为子型。多个独立破坏动作各自挂证据，登记并存或因果关系。参考错误、合同允许差异、范围外及无法裁判分别登记。

诊断按调用/参考、Host 计划与实收、设备读算写、跨 rank 及消费边界转查。在计算段用独立局部参考比较 `actual` 与 `R(x_obs)`，再用 `R(x_obs)` 与 `R(x_ref)` 查上游传播。对每个必要谓词记录预期、实际、范围、事实锚点和 `TRUE/FALSE/UNKNOWN/CONFLICT`。支持需有区分证据。排除需看实际可观测的必要条件或可复算的路径反证。缺证时保留候选，并指出下一项具体观察能区分哪些预测。[定位与分类方法](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-first-acceptance-report.md>) · [事实与机理字段](<../fault-evidence-audit-codex-initial-public-release/work/update_check_16ce36a/snapshot/faultaudit/trigger_assessment.py>)

| 开发候选与已见子问题 | 可结构化的判据 | 待核边界 |
| --- | --- | --- |
| A 无效元素进入归约，回放 04 | 对照合同有效域、实收范围与实际消费坐标，用无效 padding 的单位元或 mask 干预验证结果关系。 | 缺对应构建及 lane 级输入；与上游范围错误、尾部漏写区分。 |
| B 已规约结果被重复计入，回放 12 | 用同组每 rank 的贡献身份区分 partial 与已复制的完整结果，比较第二次求和的预期及实际重数。 | 下游倍率是线索，需有数据血缘与同计划对照；合法分层归约是近邻。 |
| C 块级归约参与轮次错配，回放 07 | 以 CTA、collective、逻辑任务和轮次为键，核实应到集合与实际到达。 | 12288 宽度的分轮和干预有公开复验，缺逐线程时序。 |
| D 本轮共享槽读完前被复写，回放 08 | 核同一共享分配的地址交叠与代次，验证本轮消费结束到下一轮写入的依赖。 | 等轮次加尾屏障的复验有据；缺精确覆盖轨迹。07/08 同属一个事件家族。 |

A–D 已有自然语言候选和可利用的已见证据，现阶段仍使用开发规则卡。新案可按场景提出多项候选；当前实现提供通用结构和引用校验。[判据候选](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/rule-candidates.md>) · [证据索引](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/case-evidence-index.md>) · [源版本和联合判卷](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/source-and-acceptance-review.md>)

## 待验证与可进入后续的设计

- **分类有效性。** 将已知根因的事后分类和未知根因的诊断分别评估。前者提供已查明的破坏动作和因果证据，隐藏旧分类。后者只给当时可见症状及预设取证预算，修订、归因和答案封存到判卷。按事件、补丁和派生案例整组划分，使用未见家族做独立留出，统计正确机理、定位、误强归因、合理弃权、多机理漏报和取证成本。既有 16 个已见子问题属于开发材料。
- **原 30 映射。** 用评估后的机制版本建立旧源行到新模式版本的多对多边，标同机制、部分、有据差异、未知或超域。原记录分母 30，独立机制和事件按证据去重，诊断能力及注入能力按实际验收单元另列。正式逐条比较依赖原 30 的完整冻结定义与来源明细。
- **注入保真。** 从高到低记录实际原平台根因复现、机理等价注入、错误状态模拟、症状代理。沿同一链路记录触发、目标合同、注入点、健康/故障对照、恢复及作用范围。每种能力只计入其已验证的等级与平台范围。

候选的版本边界、试跑与验收范围见 [P0–P1 审查原报告](<../算子精度故障模式库_P0-P1设计审查_20261115.md>)。项目检出和源件身份见 [工程状态](./PROJECT_STATE.md)。
