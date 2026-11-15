# 机理覆盖和扩展缺口

基于 `f0b6c46ade3739d098aef2017c5881498a1fdcf9`，本图仅使用项目已见开发材料。模式目录为 `0.2`，裁决和分类单轨协议为 `0.2.1`。下列缺口用于资料分流与后续版本排序。真实未见样本由独立整理者分配和封存。覆盖、候选缺口、上位方向和证据不足各有独立口径，行数不计入模式数量或评估分母。[版本与证据清单](<D:/project/精度/fault-pattern-handoff/classification/revision_manifest_0_2_1.json>)

## 1. 现有模式覆盖

表中证据范围只描述对应开发视图。4 个已见原件重读视图覆盖 P1、P2、L2、C2，来自 3 个事件家族。L1、C1、C3 在开发判决中有已见材料，原件重读结果待扩展。真实未见覆盖待首轮评估。[原件重读结果](<D:/project/精度/fault-pattern-handoff/handoff/CLASSIFICATION_PILOT_0_2_1.md:18>)

| 机理引用 | 已见证据和判定边界 |
| --- | --- |
| `MECH-v0.2:P1` 参数来源绑定错误 | N24 修订版固定源码从非等价的布尔属性槽取 padding 字段。同一事件的旧、修订版作为近邻对照。[N24 双版本原件](<D:/project/精度/fault-pattern-handoff/classification/development.md:9>) |
| `MECH-v0.2:P2` 特殊参数状态解释错误 | N24 旧版固定源码正确读 padding 属性，再把表示未指定的 `-1` 规范化成末行索引。裁决限于固定宿主动作，后续过滤效果按实际证据单列。[N24 旧版证据](<D:/project/精度/fault-pattern-handoff/classification/development.md:9>) |
| `MECH-v0.2:L1` 错误套用连续布局寻址 | N20 固定旧 Concat 分支用逻辑列数算物理起点。GemmaRmsNorm 开发对照保留为作者报告范围。布局能力限制与正确正规化继续作为近邻。[Concat 固定代码](<D:/project/精度/fault-pattern-handoff/classification/development.md:11>) · [GemmaRmsNorm 开发判决](<D:/project/精度/fault-pattern-handoff/handoff/CLASSIFICATION_PILOT_0_2.md>) |
| `MECH-v0.2:L2` 地址计算中单位换算错误 | N10 固定旧循环把元素偏移直接作为按字节寻址的打包掩码下标。N06 的基址项缺失与单位转换可以在旧公式层面分开举证。[N10 与 N06 对照](<D:/project/精度/fault-pattern-handoff/classification/development.md:13>) |
| `MECH-v0.2:C1` 无效成员被纳入 | PyPTO 已见作者案例描述有效域外零参与 max。引用范围限于该来源报告。合法中性化是近邻。[PyPTO 原件索引](<D:/project/精度/fault-pattern-handoff/classification/development.md:14>) |
| `MECH-v0.2:C2` 有效贡献被遗漏 | N23 固定旧分支在中心映射越界时提前写零。对于一维静态反事实，旧分支跳过非空边界贡献区间。该证据限定在所评源码与输入约定。[N23 原件](<D:/project/精度/fault-pattern-handoff/classification/development.md:15>) · [原件重读代入](<D:/project/精度/fault-pattern-handoff/handoff/CLASSIFICATION_PILOT_0_2_1.md:26>) |
| `MECH-v0.2:C3` 原始贡献被重复计入 | SGLang 报告描述同一完整规约和的多个副本再次参与求和。两段聚合的来源一致性支撑该报告裁决，逐 rank 缓冲仍待补。合法分层规约作为近邻。[SGLang 报告与修订](<D:/project/精度/fault-pattern-handoff/classification/development.md:16>) |

同一错误动作造成的派生失效保留在因果链上。C1 与 C2 的组合范围限于同一动作中的成员替换，须能区分被纳入和被遗漏的成员身份。目录外的具体缺陷保留其动作、证据和最近上位方向。[组合裁决与冲突降级](<D:/project/精度/fault-pattern-handoff/handoff/CLASSIFICATION_PILOT_0_2_1.md:8>)

## 2. 有明确证据的候选缺口

下表保留每个已见动作可达到的证据范围和近邻。它们是后续开发候选，追加正式模式前仍需比较同机理异算子、合规行为及旧模式的吸收边界。

| 优先方向 | 已证动作与范围 | 后续拆并需要区分 |
| --- | --- | --- |
| 数值表示与计算 | N07 固定 launcher 源码漏做双精度属性到 float 通道的数值转换，具体 ABI 待证。N08 固定旧 `signbit` 路径用 `Less(x,0)` 替代位语义，来源报告含 `-0.0` 反例。N25 固定旧 GroupNormSwishGrad 实现漏了局部链式系数，同版本正向公式和静态有限差分支持。[N07](<D:/project/精度/CANN25_25_review_reports/N07.md:22>) · [N08](<D:/project/精度/CANN25_25_review_reports/N08.md:22>) · [N25](<D:/project/精度/CANN25_25_review_reports/N25.md:22>) | 将值传递边界、位谓词与数学公式分别验证。保持来源/状态不变以排除 P1/P2，固定 dtype 并用高精度对照区分公式差错与有限精度差异。 |
| 控制传播与分支 | N02 非空数据和空索引组合命中无输出早退，可比对旧守卫、新守卫和保留原数据的拷贝链。N05 Db0 的 Bias 更新放入 Db1 的条件体，旧控制流与静态四组合对照界定错误动作。N26 负小数位整数舍入始终走复制 DAG，源码和普通无溢出域的整数对照支撑丢失处理分支。[N02](<D:/project/精度/CANN25_25_review_reports/N02.md:53>) · [N05](<D:/project/精度/CANN25_25_review_reports/N05.md:24>) · [N26](<D:/project/精度/CANN25_25_review_reports/N26.md:22>) | 分开检查错误守卫、错误条件归属和缺失处理路径。入口条件、传播中的控制字段、首次错误动作和后续漏写各自记录。 |
| 一般地址计算与索引映射 | N06 固定向量量化路径漏加分组基址项。NCCL AllGather 已见原报告按 rank 标记确认整块错槽，旧发行非注册 NVLS 路径和维护者说明支持遗漏 rank 映射。ReduceScatter 对照限于镜像源码和发布记录。[N06](<D:/project/精度/CANN25_25_review_reports/N06.md:22>) · [NCCL AllGather 版本与实测范围](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/source-and-acceptance-review.md:12>) | 检查分组基址、逻辑索引到物理所有者的映射、地址量纲和物理步长。用同单位的期望与实际地址排除 L2，用布局合同和实际公式排除 L1。 |
| 同步与生命周期 | NVFP4 已见 12288 宽路径有参与轮错配，16384 宽等轮路径有共享槽复用边界问题，回放记录各自的单因素对照。两项源自同一 Issue 家族。N27 多条通信实现以窄有符号轮次表示支持有序等待，固定代码及近界计算支持轮次协议范围缺口。该案例的设备触发和提前退出仍为报告范围。[NVFP4 参与轮](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/source-and-acceptance-review.md:10>) · [NVFP4 共享槽](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/source-and-acceptance-review.md:11>) · [N27](<D:/project/精度/CANN25_25_review_reports/N27.md:22>) | 对齐参与者轮次、生产与消费顺序、实际缓冲重叠及复用时点。轮次表示越界与地址计算越界各按其字段角色和破坏的约定核对。 |

## 3. 待细分的上位方向

| 上位方向 | 下一步判别 |
| --- | --- |
| 数值表示、算术路径与参考合同 | 在合法路径和当前生效的误差或确定性合同内，分别核对输入/中间 dtype、首次窄化或超限、实际操作数及累加顺序。用已见 FlagGems nanquantile 参考失配和 PyPTO split-K 合同允许差异校准排除界限。[原 08—14 的数值和次序入口](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md:14>) · [FlagGems 参考误报](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/case-evidence-index.md:16>) · [PyPTO 允许差异](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/case-evidence-index.md:19>) |
| 控制字段、计划生产和消费边界 | 对同一个输入固定生效 key、期望分支、实际分支及中间计划，区分错误谓词、控制字段错传、计划本身错误和下游误用计划。已见 Conv3D 中实收窗宽为 12、非切分 B 装配推得 13，给出了计划消费边界的对照。[原 11—12 的计划入口](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md:17>) · [Conv3D 的计划实收与消费证据](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/source-and-acceptance-review.md:9>) |
| 逻辑到物理地址映射 | 同量纲下分别查基址和分组项、表项所有者、物理布局以及地址宽度。区分可表示但公式错误、正确公式的表示溢出、合法拒绝不受支持的布局。[原 04—07 的映射入口](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md:10>) · [原 17 的偏移表示问题](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md:23>) · [原 22 的布局能力界限](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md:28>) |
| 完成依赖、参与轮和缓冲资源 | 在固定地址、参与者集合和版本下，区分等待缺失、阶段归属错误、已完成但资源早复用及跨区域覆盖。只有重复错值仍不能选择其中一种。[原 05 的同步入口](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md:11>) · [原 21 的内存覆盖入口](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md:27>) · [NVFP4 相邻机理](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/source-and-acceptance-review.md:10>) |

## 4. 证据不足

| 已见材料 | 当前待证 |
| --- | --- |
| N03 FP32 核内候选 | 同一修订改了输出源/同步、标量读取、UB 和 golden。保留联合修改未拆分，需控制输出源和参考后验证同步，才能登记唯一或相互独立的动作。[N03](<D:/project/精度/CANN25_25_review_reports/N03.md:42>) |
| N11 工作集边界候选 | 旧新候选长度控制元数据分配和搜索范围的差异有源码。目标 shape 的实际 tiling 和几何上界未取得，所遗漏成员、物理越界及其因果边界仍待证。[N11](<D:/project/精度/CANN25_25_review_reports/N11.md:20>) |
| N12 中间存储类型候选 | 类型选择的真实 diff 已有，后端实际写出类型、字节与版本合同未闭合。后续补同构建的写出契约及受影响路径。[N12](<D:/project/精度/CANN25_25_review_reports/N12.md:20>) |
| FlashInfer decode 及 NCCL NVLS 尾部 | FlashInfer 已见 partial 窄化及计划切换，报告版构建、适用合同和误差归因待证。NCCL 另版本补零支持其重复性对照，故障报告版的保证与绝对数值精度还需独立核对。[FlashInfer 声明边界](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/source-and-acceptance-review.md:15>) · [NCCL NVLS 证据与限制](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/source-and-acceptance-review.md:13>) |
| 原 30 的症状、触发及适用范围 | 空输入与 NaN、指数算子输出差异、BNInferenceD 非有限值、方差负值及融合后不一致等仍须找同版本的首次错误动作。保留触发和已知传播入口。正式模式映射使用冻结原件及 `declared_details`。[空输入入口](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md:7>) · [原 19](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md:25>) · [原 24—25](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md:30>) · [原 29—30](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md:35>) · [正式映射条件](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/original-30-diagnostic-audit.md:43>) |

## 按失败原因决定下一步

- 原件清楚且执行者错读版本、路径或动作时，修读件提示、字段合同或语义核验，增加从原件开始的回归。
- 事实正确且已存在的边界无法区分时，调整近邻排除、层级或拆并规则。已证目录外的动作再比较可复用范围和新增成本。证据不足的条目保留缺证项。
- 分类正确且事实依据或统计有误时，修正评估协议，继续分开统计严格主目标、备选接受、事实支持及叶级覆盖。命名空间 `MECH-v0.2:*`、`API42:*`、`V4:*` 保留独立引用和覆盖分母。[评分与命名口径](<D:/project/精度/fault-pattern-handoff/classification/WORKFLOW.md>)

## 分批扩展计划

1. 先封存七条的 `0.2.1` 执行与评分版本，独立评估期间固定被测文件。全局缺口图和开发池整理可并行推进。
2. 首轮证据支持分类方法后，从有明确动作的候选中选择少量新增项。可优先比较 N07 属性类型边界、N06 分组基址遗漏和 N08 位语义谓词，各有固定源码与现有叶级的近邻。同步和分支候选按其可判别证据择批。若首轮失败源于读件、规则或评分，按失败原因先修对应环节。
3. 开始扩展版本时，将目录校验改为验证版本、模式与父级引用、必要事实、操作事实及声明的检查器。现行 `OPERATION_FACTS` 和 `VIOLATIONS` 限制为七叶三组，`COMPATIBLE_MEMBERSHIP_MODES` 专门定义 C1/C2 的组合。后续用受审目录声明承载这些关系，检查器继续通过有限的实现注册。现有组合约束和证据作用域可用旧用例回归。[现行模式和父级限制](<D:/project/精度/fault-pattern-handoff/classification/classify.py:69>) · [固定组合](<D:/project/精度/fault-pattern-handoff/classification/classify.py:12>)
4. 每小批形成近邻对照、旧模式不被误吸收的回归及新版本冻结。再由独立整理者从新家族中锁定评估包，报告实际分母和证据范围。独立等级或来源尚未核验的资料保持待整理。模型生成的候选交由人工审阅后入目录。
