# 算子精度故障诊断原型 0.1.1 与首轮受控评估

2026-11-15，北京时间。Work 启动目录是 `C:\Users\86152\Documents\ChatGPT\fault_pattern`。本轮读取、开发和评估实际使用 `D:\project\精度`，原型在 `D:\project\精度\diagnosis_mvp`。研究基准沿用 `510601f887f8ad174335f617a9d7e2a808ff897f` 的固定材料与已核对的 `16ce36aa427d0ccc7d6b3d93d59d33d28907ceb8` 源码快照。本轮复核的 0.1.3 发布工作树 `9d947633` 与 CANN25 `edb8c4f` 均干净，两处均缺 510601f 提交对象。原型版本由自身哈希固定，FaultAudit 接入待实施。[基线与证据核对](<D:/project/精度/handoff/WORK_REVIEW_P1续作_20261115.md>) · [发布检出](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/publish/github-v013-net>) · [CANN25 检出](<D:/project/精度/CANN25_review>) · [当前版本冻结清单](<D:/project/精度/diagnosis_mvp/freeze_v0_1_1.json>)

本轮接入 11 个局部判据和一条可逐步请求事实的诊断流程。当前 0.1.1 的 17 项回归通过。首轮用 0.1.0 先冻结并封存受控样本，再执行预测和计分。事后分类判对 **14/14 子问题、13/13 家族**。辅助诊断在每案最多两次请求下，可转查路线完整判对 **13/14**，固定首路线完整判对 **10/14**。真实未见事件的独立效果评估待取得合格盲样。[判据回归](<D:/project/精度/diagnosis_mvp/test_diagnose.py>) · [评估回归](<D:/project/精度/diagnosis_mvp/test_evaluate.py>) · [逐案计分](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/score.json>)

## 1. 参考方法与实际能力改动

状态依次为已阅读、已提取、已采用、已接入、已回归、已有独立效果证据。表内“已回归”含此前各阶段，“受控对照”指本轮封存的合成对照。真实数据的独立效果证据尚缺。[39 个来源及原有取舍](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/open-source-comparison.md:19>)

| 本地参考与方法 | 改变的决策、输入与输出 | 本轮位置、验证与状态 |
| --- | --- | --- |
| StableHLO `8117f94` 的明确约定及约束，FP-B16 `6c47a3a` 的路径范围 | 入诊先核构建、版本及适用约定。输入目标构建、合同来源与适用性，输出 `APPLICABLE`、`OUT_OF_SCOPE` 或 `UNKNOWN`。有冲突或跨调用的事实暂停判定。 | **已回归**。RMSNorm 报告期合同、后续勘误及跨构建事实有反例。[StableHLO 规范](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/contracts/openxla/stablehlo/docs/spec.md:165>) · [FP-B16](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/gitcode_patterns/ascend-op-fault-patterns/patterns/FP-B/FP-B16.md:6>) · [作用域](<D:/project/精度/diagnosis_mvp/diagnose.py:267>) · [判据回归](<D:/project/精度/diagnosis_mvp/test_diagnose.py>) |
| `conv-debug-tools@a625867` 的设备计划和消费者范围对照 | 把有据失配放到生成、传递或消费的相邻边界。输入同调用、同单位的预期、生成、收到与使用范围，输出每对边界的支持、排除或未知。 | **已回归**。Conv3D 归到消费，缺主机直接记录转移未知。另构造只错生成及只错传递的对照。[Conv3D 复盘与证据强度](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/source-and-acceptance-review.md:9>) · [范围判据](<D:/project/精度/diagnosis_mvp/diagnose.py:60>) · [判据回归](<D:/project/精度/diagnosis_mvp/test_diagnose.py>) |
| `all_in_one@2a2df54` 的逐段误差分析 | 先比 `actual` 与 `R(x_obs)` 再比 `R(x_obs)` 与 `R(x_ref)`。输入本段观测、同一参考在实际和健康输入上的结果、映射和状态身份、dtype 和容差。输出局部偏差与上游传播的组合。 | **已回归**。正反例覆盖局部、传播和参考错配。受控事后分类 3/3、诊断每路 2/2 的数值阶段判对。源文件是固定 Git blob `243b8f81453da88b0f18e87425aba904919366fe`，`references/diagnosis/progressive-error-analysis.md` 第 47–48 行。[本地参考仓](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/task0_upstream/yeswecann--all_in_one.git>) · [两段比较](<D:/project/精度/diagnosis_mvp/diagnose.py:359>) · [逐案计分](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/score.json>) |
| `CANNBot@eab9495` 的产物校验与比较器对照 | 先核输出清单和两侧产物身份、shape、dtype，再按合同做同字节序的原始字节比较或显式容差比较。缺项输出 `INCOMPLETE`，错配输出 `INCOMPATIBLE`。比较结论和机理裁决各有证据。 | **已回归**。复测“两边均缺第二输出”和正负零，覆盖放行及阻断。受控例 C13 缺次输出时保留原诊断未知。[原比较器与反例](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/comparator-checks.md:7>) · [产物门禁](<D:/project/精度/diagnosis_mvp/diagnose.py:335>) · [判据回归](<D:/project/精度/diagnosis_mvp/test_diagnose.py>) |
| `ascend-op-issue-analysis@3c7db95` 的竞争假设、最小干预，`all_in_one` 的定向观察 | 以有区分力的请求代替只按首功能查。输入候选路线、尚缺字段与已有观察，输出优先字段、可区分的机理和逐次回执。固定路线组共享判据、数据和预算。 | **已回归，已有受控对照**。一条观察能完成的谓词优先，其次是覆盖的候选数，再按路线顺序。真实环境的取证成本与干预由执行方验证。[竞争假设手册](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/gitcode_patterns/ascend-op-issue-analysis/references/rootcause-playbook.md:209>) · [请求策略](<D:/project/精度/diagnosis_mvp/diagnose.py:381>) · [相同预算执行](<D:/project/精度/diagnosis_mvp/evaluate.py:121>) · [逐案计分](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/score.json>) |
| `fault_review@b78b2a2` 的事件标识和来源去重 | 来源指针用于合并取样家族。输入事件、关联补丁和回移、缺陷源码与带答案材料的规范身份，输出独立家族归属。同一身份跨家族、同一家族跨评估集或已登记开发资料重合时拒收。 | **已回归**。校验事件家族与共享答案等键。身份抽取和同源核对由样本整理者负责。[编目解析](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/fault_review_b78b2a2/parse_reference.txt:66>) · [编目使用审查](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/fault-review-catalog-audit.md:14>) · [家族校验](<D:/project/精度/diagnosis_mvp/evaluate.py:70>) · [评估回归](<D:/project/精度/diagnosis_mvp/test_evaluate.py>) |
| FP-B16 的阳性、近邻和反例，`lean_kernel_verify@92a4b6f` 的参与角色与 phase | 使用事实相符的排除路径，记录多机制、缺证与不可比较。输入地址、贡献身份、参与轮次，或同时具备地址范围、代际和顺序的读写，输出每条局部谓词结果。 | **已回归**。同值错位、错轮与共享槽早写、不同槽及无法建立共同顺序均有对照。[FP-B16 区分观察](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/gitcode_patterns/ascend-op-fault-patterns/patterns/FP-B/FP-B16.md:14>) · [Barrier 阶段约束](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/contracts/facebookresearch/lean_kernel_verify/lean/KV/Spec/Barrier.lean:9>) · [局部判据](<D:/project/精度/diagnosis_mvp/diagnose.py:203>) · [判据回归](<D:/project/精度/diagnosis_mvp/test_diagnose.py>) |

**已提取、留作候选。** DLC_fBug 的归纳和余项回判可服务于后续模式评审。互斥主类与按频次取种子会压缩罕见和复合机理，因此本版接入的是逐谓词并列，分类名称由当前合同校准。编目主题和症状聚类保留在检索层。ONNX 和 StableHLO 的具体算子约定需先确认目标框架中的版本和适用范围。Lean、GPUVerify、Warp 等留待可获取平台观测或专项验证时选用。CANN 专项工具、CATLASS、PyPTO 家族与数值故障数据用于找路径、样本及反例。平台适配、自动取证与完整外部分类迁移待另外验收。[DLC_fBug 原件](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/gpu/sssssh1228/DLC_fBug/pattern_definition.json:27>) · [各项目留用范围](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/open-source-comparison.md:19>)

FaultAudit 快照已有事实、引用与作用域基础。接入时应复用其事实身份、可信范围和报告结构，并分别验收引用存在与证据确实支持谓词。原型采用 Python 标准库，按显式字段执行局部语义。现有 FaultAudit 的 103 项离线回归和原型的 17 项回归各有自己的范围。[现行证据结构](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/update_check_16ce36a/snapshot/faultaudit/trigger_assessment.py:46>) · [既有接入方案](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/classification-integration-plan.md:23>)

## 2. 六组候选合同的覆盖与边界

机制身份以**生效约定、被破坏的操作关系、可区分证据**为核心。症状、输入条件、诊断方向、责任位置、事件与版本作为独立字段保存。两案局部破坏关系和决定性对照一致才归并。同症状下若破坏关系或干预点不同就拆开。多机制逐条保留结果并追踪可能的上下游关系。每条排除都限定于该次调用、该合同与已见事实。原 42 输入条件、V4/55 的构造及原 30 记录沿原字段独立保存。[现有分类设计](<D:/project/精度/handoff/CLASSIFICATION_DESIGN.md>) · [六族与判据](<D:/project/精度/diagnosis_mvp/diagnose.py:203>)

| 候选合同族及入口 | 已接入的区分判据 | 排除与未知 | 近邻与待补 |
| --- | --- | --- | --- |
| 接口与形状。参数默认值、哨兵、形状或参数绑定变化 | `INTERFACE_CONTRACT` 比较同一语义字段的预期和实际。输入规范化参数、形状或属性绑定。 | 字段一致时排除此局部违约。版本、入口分支或规范化字段无法核实时保留未知。 | 调用参数进入下游前变义属于此边界。语义正确后范围出错转查计划。广播和动态 shape 关系仍需专项谓词。 |
| 计划与分派。阈值、设备或分支变化 | `PLAN_GENERATION`、`PLAN_TRANSFER`、`PLAN_CONSUMPTION` 分别检查预期、生成、收到、已消费的相邻范围。 | 相邻同单位范围一致，能排除该交接的范围失配。缺任一端或单位不兼容保留未知。 | 保留首个有据失配与继发差异。当前范围只覆盖半开一维区间，策略选路、等价多维切分和动态回退待验证。 |
| 有效域与布局。视图、stride、地址偏移或尾域变化 | `ADDRESS_MAPPING` 比对给定合法逻辑坐标的仿射映射和同调用实际地址；无效元素是否产生贡献由成员判据核验。 | 地址相符只排除被测点的位置错误。越域坐标、无实际地址或合同适用性不明记未知。 | 正确值落错位与正确位置值错依独立观察区分。跨坐标的覆盖、别名所有权、打包及非仿射映射待补。 |
| 数值与类型。局部超差、级联偏差或参考不一致 | `LOCAL_NUMERIC_DEVIATION` 比实际输出与 `R(x_obs)`，再用 `R(x_ref)` 报传播状态。指定同 dtype、适用参考、映射、状态和容差。 | 局部相符仅排除该判据下的局部残差。参考不适用、漂移、非有限值或不可比时保留未知。 | 可把上游传播与局部新增残差分开。错误 cast、舍入/溢出、NaN 协议与并行运算顺序需单独定位。 |
| 贡献职责。归约、scatter 或过滤成员异常 | `UNEXPECTED_CONTRIBUTION`、`REPEATED_CONTRIBUTION`、`MISSING_CONTRIBUTION` 比对预期和实际身份多重集。 | 身份及次数在所测分组内一致时相应谓词排除。只见数值、身份或来源不可追溯时保留未知。 | 缺成员、额外成员和已知成员重复可独立成立。尾元素边界和计划消费可在更早处同时违约。权重、合并语义及应参与的分组仍需扩展。 |
| 时序与生命周期。偶现、跨轮或共享缓存相关 | `COLLECTIVE_PARTICIPATION` 比角色与轮次多重集。`SHARED_SLOT_EARLY_REUSE` 查同分配、区间交叠、后代写和同序读完成。 | 同分配区间不交叠可排除该对读写的早复用。有交叠但跨时钟无法建立顺序时未知。 | 错参与轮与正确参与者下的早写可同时出现。栅栏完备性、一般 happens-before、异步生命周期与设备探针待补。 |

A 用带有效域来源的贡献 ID 验证无效元素确实形成贡献。B 用标记为已经归约的部分结果 ID 验证它再次被消费。C 核同一集合组的实际参与者和逻辑轮次。D 需实际共享分配、相交字节区间、代际和可比较的读完与覆盖顺序。原型能检查这些字段关系。历史 A–D 候选仍需逐案确认真实观测、工具接入及适用范围。[A–D 原候选规则](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/rule-candidates.md>) · [判据回归](<D:/project/精度/diagnosis_mvp/test_diagnose.py>)

## 3. 开发回归的停止条件与复跑

```powershell
Set-Location -LiteralPath 'D:\project\精度\diagnosis_mvp'
python -B -X utf8 -m unittest discover -s . -v
```

`diagnose.py` 的命令行接受一个个案 JSON 对象。下列命令从已有集合读取首个开发个案，复核当前版本，再用已揭盲的同一批样本复跑回归。

```powershell
python -B -X utf8 -c "from diagnose import diagnose, read_json; print(diagnose(read_json('development.json')['cases'][0]))"
python -B -X utf8 .\evaluate.py freeze
python -B -X utf8 .\prepare_holdout.py
python -B -X utf8 .\evaluate.py predict .\controlled_regression_v0_1_1
python -B -X utf8 .\evaluate.py score .\controlled_regression_v0_1_1 --answer-key .\controlled_regression_v0_1_1\answers\answer_key.json
```

每案以 `case_id`、`family_id`、`build`、`call_id`、有序 `routes`、版本 `contract` 和 `observations` 表示。每项观察含事实 ID、字段、同一 build/call、来源、证据种类和值。输出逐谓词裁决、匹配证据、输入哈希以及下一观察字段。原型检查已提供事实和声明的参考资格。使用者需从原始日志、源码或测量整理字段并核验语义。原型只在合同已适用时自动请求机制字段。合同为未知时，执行者先补目标构建、能力文档和实际入口。输出缺项时按 `missing_outputs` 补采对应产物。事实冲突或参考不适用时先重验同一调用、映射及来源。支持结果允许带并列未知。[个案执行](<D:/project/精度/diagnosis_mvp/diagnose.py:405>) · [开发用例](<D:/project/精度/diagnosis_mvp/development.json>)

| 开发回归 | 本轮通过的停止条件 | 证据边界和反例 |
| --- | --- | --- |
| Conv3D | 用 arch35 CANN 9.3.0 的设备 Tiling 报告值 12 与非切分 B 消费的源码复算 13，支持 `PLAN_CONSUMPTION`。生成和传递保留未知。 | 实际逐元素消费 trace 待补。只错 Host 生成、只在传递改变范围各有不同的阳性控制。[计划与消费的原证据](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/source-and-acceptance-review.md:9>) |
| RMSNorm | 报告期允许非连续 `rstdOut`。相对逻辑地址 4、实际落位 1，支持 `ADDRESS_MAPPING`。 | 地址落位一致时局部排除。后续 `b4db407` 文档适用边界另行核，历史写入者和修复结果待证。[报告期与后续文档](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/case-evidence-index.md:12>) |
| FlashInfer | 相同值的 contiguous/stride-2 差异保留为观察线索。产品分支合同与精确读地址缺证时给 `UNKNOWN`。 | 用有效合同、正确地址和仅缺地址的独立夹具检验排除/未知。首错作用点待实际 trace。[FlashInfer 固定路径和设备复验](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/case-evidence-index.md:26>) |
| EmbeddingBag | 历史 `None/-1` 语义被送成末行索引，旧路径与实际 head 的属性误读各自支持 `INTERFACE_CONTRACT`。 | N=3 走静态反事实，显式 padding 0 正常保留作对照。原框架桥接、其它负值及修订运行效果待证。旧版和 head 同一开发家族。[N24 静态链与修复范围](<D:/project/精度/CANN25_25_review_reports/N24.md:18>) |

首版 15 项通过，覆盖 5 个档案夹具、近邻与证据门禁、封存分组和预算测试。首版冻结时间 18:00:45，样本封存 18:02:57，预测记录 18:02:58。冻结清单 SHA-256 `93a78e5530062a627e051aee721c23715c3b1a0f16b9d13d81a41be8dc47072b`。同路径复跑校验已有输出与重新生成的字节一致。预测在拒绝读取答案文件的审计钩子下复跑通过。[首版冻结清单](<D:/project/精度/diagnosis_mvp/frozen_v0_1_0/freeze.json>) · [封存清单](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/public/seal.json>) · [带取证记录的预测](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/predictions.json>) · [判据回归](<D:/project/精度/diagnosis_mvp/test_diagnose.py>) · [评估回归](<D:/project/精度/diagnosis_mvp/test_evaluate.py>)

复核时，首版的极端浮点差值和容差同时溢出会漏检，布尔值也会通过输出维度检查。0.1.1 在浮点中间量溢出时按有理数比较，并要求两侧产物维度是整数。新增两项回归将通过数提高到 17，首轮结果原样封存。对同输入、观察和答案的再运行逐案得分一致，作为修订后回归。当前冻结清单 SHA-256 `e20d350e8535ec195f3e8a5115801ab30206d791aac4284441861e3348a232f7`。 [当前判据](<D:/project/精度/diagnosis_mvp/diagnose.py:98>) · [两项边界回归](<D:/project/精度/diagnosis_mvp/test_diagnose.py:109>) · [修订后得分](<D:/project/精度/diagnosis_mvp/controlled_regression_v0_1_1/score.json>)

## 4. 先冻结后评估

首轮样本由原型作者在 0.1.0 冻结后用单独的准备程序生成，范围是可控合成情境。准备程序无诊断代码依赖。它先按事件与带答案材料的身份分组，再封存评估输入、可请求的观察和独立存放的答案。预测只交付当前观察给判据，评分阶段才读取答案。声明的补丁、回移、共享源和答案键跨组重合会中止运行。流程隔离已复测。实际历史材料的同源检查、人工整理独立性及设备取证条件仍需独立验收。[样本准备程序](<D:/project/精度/diagnosis_mvp/frozen_v0_1_0/prepare_holdout.py>) · [封存输入](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/public/inputs.json>) · [观察包](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/public/packets.json>) · [预测](<D:/project/精度/diagnosis_mvp/evaluate.py:146>) · [评分](<D:/project/精度/diagnosis_mvp/evaluate.py:235>)

事后分类提供已经确认的局部观察，隐藏机理标签，预算为 0。辅助诊断只提供症状、经整理的初始字段和候选路线，每案最多两次请求，每次成本 1，包括没有回应的请求。两诊断组使用相同的局部判据、初始信息、观察池和成本。完整正确要求裁决状态和机理集合同时匹配。误强归因按出现额外机理的有归因案例数计。正确弃权使用预先判为未知的分母。过度弃权数以该轮有预定确定裁决的案例为分母，部分归因漏判另计。[带取证记录的预测](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/predictions.json>) · [逐案计分](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/score.json>)

| 指标 | 事后分类 | 可转查诊断 | 固定首路线诊断 |
| --- | ---: | ---: | ---: |
| 完整正确子问题 | 14/14 | 13/14 | 10/14 |
| 完整正确家族 | 13/13 | 13/14 | 10/14 |
| 可归因案例完整正确 | 10/10 | 6/7 | 3/7 |
| 确定的排除或合同外判对 | 2/2 | 3/3 | 3/3 |
| 误强归因 / 有归因 | 0/10 | 0/6 | 0/4 |
| 正确弃权 / 应弃权 | 2/2 | 4/4 | 4/4 |
| 可判而弃权 / 可判 | 0/12 | 1/10 | 3/10 |
| 漏掉的机理标签 | 0 | 1 | 4 |
| 请求及获得回应 | 0/0 | 23 次请求，18 次有回应 | 21 次请求，15 次有回应 |
| 首次请求命中预登记的决定性字段 | 无请求 | 9/13 | 7/13 |

可转查新增判对地址 D01、接口 D03、重复贡献 D05，并补齐 D06 的第二个机制。D14 的两条接口观察在预算内可取得，可转查先耗一次请求排除贡献近邻，固定路线用掉两次请求查出了接口违约。用到的代价是合成环境中的等成本请求次数。结果支持继续检验取证优先级，提升幅度只适用于此批场景。输出门禁和局部误差分析各有回归证据，未对它们分别做有无方法的历史对照。[逐案计分](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/score.json>) · [带取证记录的预测](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/predictions.json>)

首轮失败归属集中在诊断步骤，固定路线 4 案、可转查 1 案。预期未知中，C11 是判据表达范围，D11 缺观察能力，D09 缺适用参考，C13、D08、D10 缺足够可比证据。下一轮应优先验证两个已定位的流程缺口。多字段假设需估计补齐所需的连续请求预算。未知合同时需能请求合同、版本和路径材料。把改动作为新版本开发，另封未见家族再比较。[逐案计分](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/score.json>)

### P2 真实历史盲样放行条件

已见 16 个子问题、14 个家族的桌面回放保持开发用。早期 7/14 与 10/14 还有获件时点、先前阅读与共享答案材料的影响。已核本地 AIFaultBench 目录有索引及一份原始条目，索引只给事件和修订等元数据。GPU 数值问题 CSV 把 Root Cause、Symptom 和 Fixing Strategy 放在同一行。555 份资料中的机理完整性仍为 `NOT_ASSESSED`。这些来源可供筛选，当前可核的本地材料中尚未发现已封存的合格独立评估包。[既有桌面回放](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-first-acceptance-report.md:45>) · [AIFaultBench 索引](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/expanded_empirical/mehilshah/AIFaultBench/index.csv:1>) · [GPU 数值问题数据](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/gpu/GPU-Program-Bug-Study/Comprehensive-Study-on-GPU-Program-Numerical-Issues.github.io/NumericalBugDataset.csv:1>) · [555 完整性统计](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/evidence_gap_recheck_16ce36a/audit_summary.json:50>)

首批历史包由独立整理者提交。按事件、补丁与回移、共同缺陷源码和答案泄漏的连通关系建家族，将所有先前开发读过的家族和共享材料写进排除清单。事后分类包保留版本、路径及已经证实的破坏动作，裁决标签放答案包。诊断包保留故障当时能够看到的材料及按成本开放的同构建观察，修复和事后归因由裁判保存。入组前确认每个阳性和近邻有原件支持，证据不足的样本预先登记弃权理由。使用单独目录和预先固定的预算、计费及分母，验证预测完成和哈希后再揭盲。引擎的家族校验依赖提交的身份键，实际历史源的完整排除清单是本轮到 P2 的依赖。首轮评估器计每次请求为 1。真实观察代价若采用分级权重，需在揭盲前登记成本并冻结相应版本。[家族校验和封存入口](<D:/project/精度/diagnosis_mvp/evaluate.py:70>) · [现有独立验证计划](<D:/project/精度/handoff/WORK_REVIEW_P1续作_20261115.md>)

原 30 正式映射需取得冻结的原件及 `declared_details`。现阶段可独立推进 P2。P2 之后使用通过评估的机理体系做多对多映射，分别计算原记录、独立机理和经验证的诊断/注入能力。按实际覆盖缺口筛证，再产出有版本、对照、复位与验收信号的注入规格。[原 30 原文及边界](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md:3>) · [已有后续依赖](<D:/project/精度/handoff/NEXT_TASKS.md>)

### 复核文件

- 当前版本的 [诊断入口](<D:/project/精度/diagnosis_mvp/diagnose.py>)、[开发夹具](<D:/project/精度/diagnosis_mvp/development.json>)、[判据测试](<D:/project/精度/diagnosis_mvp/test_diagnose.py>)、[评估工具](<D:/project/精度/diagnosis_mvp/evaluate.py>)、[评估测试](<D:/project/精度/diagnosis_mvp/test_evaluate.py>)、[修订后复跑准备程序](<D:/project/精度/diagnosis_mvp/prepare_holdout.py>)、[冻结清单](<D:/project/精度/diagnosis_mvp/freeze_v0_1_1.json>)及[修订后记录](<D:/project/精度/diagnosis_mvp/controlled_regression_v0_1_1>)。
- 首轮的 [冻结代码与清单](<D:/project/精度/diagnosis_mvp/frozen_v0_1_0>)、[样本封存](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/public/seal.json>)、[首次预测](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/predictions.json>)、[首轮计分](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/score.json>)、[独立存放的答案](<D:/project/精度/diagnosis_mvp/controlled_holdout_v1/answers/answer_key.json>)。复跑首轮应调用 `frozen_v0_1_0` 内的评估工具，并指向 `controlled_holdout_v1`。
