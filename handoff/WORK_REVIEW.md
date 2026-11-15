# Work 检查与验收记录

2026-11-15，北京时间｜已完成检查和待查证据

## 本 Work 已完成的检查

| 检查 | 实际结果及出处 |
| --- | --- |
| 工作目录与 Git | 核验工程根 `D:\project\精度` 可访问，确认两个本地工作树的分支、提交、未提交状态及远端。GitHub 只读核对仓库可见性和分支引用，保留本地跟踪缓存与远端当前值的区别。[工程状态](./PROJECT_STATE.md) |
| 指定研究版本 | 核对项目内 29 个对象库，完整 `510601f887f8ad174335f617a9d7e2a808ff897f` 未在本地对象库定位。对 0.1.21 快照的 50 个核心 Python 文件、4 个测试、原 42/V4 的 3 件资料做哈希对读。P0 报告列出范围。[P0–P1 审查原报告](<../算子精度故障模式库_P0-P1设计审查_20261115.md>) · [固定提交](https://github.com/spike677/fault-evidence-audit/commit/510601f887f8ad174335f617a9d7e2a808ff897f) |
| 原 30 与冻结件 | 校验固定提交的原表 `inputs/cann30_original.txt`，9,532 字节，SHA-256 `1f7e8dda1358dfc306c074c3022e2564124a4a4cb08847f9eaecfae5dcdd41e2`。原表中 30 条尚待正式映射。查到数据库记录生成代码、验证代码和两份合成 pilot 状态。实际冻结的声明定义产物待定位。[原 30 边界审查](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md>) · [冻结产物的生成和保存](<../fault-evidence-audit-codex-initial-public-release/work/update_check_16ce36a/snapshot/faultaudit/trigger_workflow.py>) |
| 诊断链与候选 | 静态核查 `ConditionFact`、`Detail`、`declared_comparison`、`CandidateProposal`、`DesignCard`、`precision-bridge` 与相关测试。事实、版本、范围和引用可校验。A–D 专用判定器与专属回归待实现和验收。Bridge 产物明确将设备执行记为 `NOT_RUN`。[声明比较门槛](<../fault-evidence-audit-codex-initial-public-release/work/update_check_16ce36a/snapshot/faultaudit/trigger_assessment.py>) · [候选状态](<../fault-evidence-audit-codex-initial-public-release/work/update_check_16ce36a/snapshot/faultaudit/trigger_sparse.py>) · [Bridge 验收输出](<../fault-evidence-audit-codex-initial-public-release/work/update_check_16ce36a/snapshot/faultaudit/precision_gate.py>) |
| 参考方法 | 对读下载的 Ascend 模式卡、CANNBot、`all_in_one`、`fault_review` 和局部合同检查代码。可复用已见条件和裁决流程，先核入参、参考、输出清单、实际分派和近邻反证。`fault_review` 复算为 1,184 条推理编目含 1 个指针、221 条训练编目，按编目单位计。[本地开源对照](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/open-source-comparison.md>) · [编目与跨来源去重](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/fault-review-catalog-audit.md>) |
| 交接件核对 | 读回 P0 原报告及其本地证据引用，核对本轮新增的四份交接件与原报告的状态、版本和路径一致。[P0–P1 审查原报告](<../算子精度故障模式库_P0-P1设计审查_20261115.md>) |

## 既有验收证据及可计入范围

| 记录 | 已有结果 | 当前可支持的能力 |
| --- | --- | --- |
| 0.1.3 流程验收 | 文档记录 138 项离线回归，以及 17 个合成 Codex 任务的 31 项验收检查。 | 导入、取证结构、任务交接与门禁。合成任务通过的结论只涵盖其测试对象。[0.1.3 验收记录](<../fault-evidence-audit-codex-initial-public-release/VALIDATION.md>) |
| 0.1.21 选定回归 | 父提交 `16ce36aa427d0ccc7d6b3d93d59d33d28907ceb8` 的保存记录为 103 项通过，范围为选定离线回归。 | 按记录验收覆盖的结构化流程，选定日志与源码哈希分别可复查。[选定回归结果](<../fault-evidence-audit-codex-initial-public-release/work/update_check_16ce36a/selected_regression.json>) |
| 两组已见桌面回放 | 16 个子问题、14 个事件家族。固定路线组、可转查组各请求 30 次，分别有 28 和 29 次回应，有合同违约及机理证据的子问题数分别为 9 和 12。 | 开发阶段取证路线有操作性，可用于修正规则。参与者看过开发材料，部分回应含修订，两个组得到材料的时点有差异。07/08 和 13/14 各共享家族。[桌面验收第 45 行起](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-first-acceptance-report.md>) · [共同起点](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/full-entry.md>) |
| 比较器与上游对照 | 既有 CANNBot 比较器八项合成实跑。预期输出两侧均缺的用例仍可能退出 0。部分 A–D 证据含作者或独立上游设备对照。 | 说明完整输出清单和真正适用的比较算法需要审查。A–D 的证据强度逐项记录，上游版本和路径决定可解释范围。[比较器运行记录](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/comparator-checks.md>) · [源版本及联合判卷](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/source-and-acceptance-review.md>) |

本轮是本地只读项目审查、哈希核对和交接整理。上表测试及设备复验均沿用已有记录，本轮没有新增测试或设备运行结果。

## 未解决事项

1. 找到真实原 30 的冻结 `declared_details` 和 `trigger_baselines`，核对 `baseline_id`、`index_hash`、目录范围、源行到模式 ID 的映射及逐项明细。GitHub 的固定原表可以继续用于研究核对。
2. 开发规则尚需用 P1 正反例和缺证场景逐谓词校准。C、D 保留同一家族关系，自身裁决分别挂证据。
3. 未见家族留出评估、设备诊断验证、30 条的正式覆盖统计及注入恢复验收均待执行。先在同预算下验证事后分类与未知根因诊断。[验证和执行步骤](./NEXT_TASKS.md)

## 2026-11-15 本地续作

已从同名 `fault_pattern` 的启动目录续查 `D:\project\精度`。目标差异、A–D 现状、其他故障方向的判据、正式原库对照的缺口及下一阶段依赖见 [本轮目标与能力续审](./WORK_REVIEW_P1续作_20261115.md)。
