# 机理目录 0.3 的术语和参考依据

题名按可区分的错误动作或失效关系取名。下文中的“逻辑计算项”是项目总称。具体模式和案例优先注明求和项、比较候选值、局部梯度项或原始分片结果。

## 必要术语

| 术语 | 定义与对象范围 | 例子及反例 | 来源 |
| --- | --- | --- | --- |
| 有效输入元素 | 目标输出、窗口和操作语义确定后，按索引域、长度、mask 或分工约定有参与资格的元素 | 部分块有效域内的输入能参与 row_max。内存中存在尾块填充值，且计算前已阻断其影响，属于合规隔离 | [Ascend C 掩码](https://asc.gitcode.com/api/SIMD-API/basic_api/memory_vector_compute/SIMD_compute/mask.html) · [PyPTO 开发原件索引](<D:/project/精度/fault-pattern-handoff/classification/development.md:14>) |
| 求和项／比较候选值 | 针对目标结果，可标识来源和角色的加法项或比较值。按实际约定区分许可的等价变换、过滤与遗漏 | 同一个输入可合法进入两个不同窗口。传入 max 的有效候选与已正确中性化的填充位置分开 | [StableHLO Reduce](https://openxla.org/stablehlo/spec#reduce) |
| 局部梯度项 | 依据前向映射，应对指定梯度位置形成的单项局部梯度贡献 | edge 复制的多个位置可能都对应边界处同一个梯度输出。在空贡献区间写零可以符合约定 | [PadV3Grad 原件与适用边界](<D:/project/精度/CANN25_25_review_reports/N23.md:44>) |
| 原始分片结果 | 同一分组和目标输出下，源自一个可区分逻辑位置的原始部分结果，保留归并前的来源身份 | TP 聚合后的完整和在多个 rank 上有相同来源集合。独立的 partial 即使数值相同，仍是不同逻辑项 | [SGLang 作者报告索引](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/diagnosis-replay/case-evidence-index.md:22>) |
| 逻辑计算项 | 相对于指定算子语义、计算边界和目标输出，可区分来源与角色的一项逻辑输入。计入规则由该边界契约给定 | 可以是求和项、比较候选、局部梯度或原始分片。线程、rank ID、物理地址及读次数可作观测线索，须回溯逻辑来源 | 项目定义，借鉴 [Ascend C 术语表](https://asc.gitcode.com/guide/technical_appendix/concepts_and_terms/glossary.html) 和 [StableHLO Reduce](https://openxla.org/stablehlo/spec#reduce) |
| 重复计入 | 在同一目标结果及计算边界内，同一原始逻辑项的计入重数超过该运算语义允许值 | 同一完整和的多个副本进入二次求和会改变原始项重数。分层归约可合法合并来源互异的 partial，缓存重读本身没有确定重数 | 项目定义，参照 [StableHLO Reduce](https://openxla.org/stablehlo/spec#reduce) · [合法分层近邻](<D:/project/精度/fault-pattern-handoff/classification/development.md:16>) |

## 归类和案例摘要

参与范围组先核资格，至少一次实际计入需有证据。重复／遗漏组对本来应参与的项核保留情况、逻辑来源及允许重数。成员替换可触发两个组的属性；若同一作用域明确被纳入和被遗漏的是不同项，输出共同上位类及 C1+C2，按动作计数。单纯尾块超差只提供找证线索。

每案摘要按固定次序写 **对象与约定 → 具体错误动作或待核 → 适用版本和作用域 → 模式与近邻 → 因果角色 → 证据边界**。命名复用短 ID，持久化引用使用 `MECH-v0.3`。

- N24 修订版，padding 索引应取第 4 槽，代码取了第 3 槽的布尔属性。限定到已核 Host 源码，归 `MECH-v0.3:P1` 参数来源误读。旧版正确读取后才误处理 -1，单列 `MECH-v0.3:P2`。同源两版本按一个事件家族保留。[同事件源码近邻](<D:/project/精度/fault-pattern-handoff/classification/development.md:9>)
- SGLang 作者报告，所有完整和副本具有同一组原始 partial，后续求和使重数超出约定。归 `MECH-v0.3:C3` 同源计算项重复计入，声明限作者报告。后处理相加这一步有记录，最早错误动作和责任阶段待核。[归约职责与来源](<D:/project/精度/fault-pattern-handoff/classification/development.md:16>)

同一事件可以在条件库和机理目录分别索引。例如 V4 的 `D1-02` 用 EmbeddingBag #646 示范省略、全有效和部分过滤的对照。机理标签取决于上述两个版本的实际参数动作。V4 的 `T1-02` 用 Concat #2165 示范步进切片及同值连续副本的对照。固定版本的行起点公式支持 L1 标签。保留两个索引，可以追溯同一案的测试入口、源码依据和分类结果。[V4 D1-02](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/baseline/knowledge/precision_trigger_knowledge_v4.md:54>) · [V4 T1-02](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/baseline/knowledge/precision_trigger_knowledge_v4.md:520>)

## 四项依据如何落到目录

| 卡片 | 语义依据 | 分类依据及采纳 | 参考关系 | 验证依据 |
| --- | --- | --- | --- | --- |
| P1 | N24 修订版读第 3 槽，约定来源为第 4 槽 | 核实际来源是否语义等价。合法别名、正确读取后的转换各按自己的动作判断 | 项目归纳。借用 API42 的角色先验、Issue 分析的代码证据绑定 | 固定源码读错槽可分类，N07 正确来源后转换仍为已证目录外 |
| P2 | N24 旧版正确读取后错误解释 -1 | 调用路径中的状态语义和处理操作都需明确。默认值合法性按契约判断 | 项目归纳。V4 的 D1/D2 提供省略、显式值与哨兵对照的构造方法 | 与 P1 同症状而首个错误不同，状态语义缺失时保留有据层级 |
| L1 | N20 既有路径设置行间步长，行起点仍错误套用密排公式 | 任一个必要地址项错误采用连续布局假设即能支持此机制，需有生效视图 | FP-B16 为出参写回的限定参照。输入路径由 Concat 固定源码支持 | N20 行起点错误仍命中 L1。生效 stride 无依据时保留有据层级 |
| L2 | N10 的掩码每元素一位，访问索引按字节 | 明确元素、位、字节及存储宽度，再核换算。基址遗漏归自己的错误动作 | 项目归纳。API42 语义角色和 V4 打包构造转为适用性提示 | N10 错误换算成立，N06 基址遗漏与合法位打包分别做近邻 |
| C1 | PyPTO 报告有效域外的零实际进入 row_max | 实际参与及无资格均需证据。识别读入后正确中性化的合规情形 | CANNBot 尾块卡提供观察点和反例。掩码术语支持描述资格 | PyPTO 与合法中性化作对照，C1/C2 替换由同动作上位表示 |
| C2 | PadV3Grad 固定源码中越界中心仍可能对应必需梯度项 | 可独立判定必需项未保留。具体实现动作按本案举证 | CANNBot 尾块丢失是方法近邻。PadV3Grad 的梯度约定来自自身案卷 | IsCut 早退例、空区间写零合规例，及具体动作尚未确定的回放 |
| C3 | SGLang 报告同组完整副本被再次求和 | 绑定目标结果、原始来源及允许重数。角色和动作另记 | 项目归纳。StableHLO 的逻辑归约与实现组织区分用于构造合法分层反例 | 已见重数关系仍可判 C3，阶段责任未明时零个独立缺陷 |

七卡的正例、近邻和缺证项沿用对应原件视图及作用范围，独立未见验证另计。[旧卡对照与原件](./development.md) · [已审基准及复用说明](../handoff/MODE_SEMANTIC_REVIEW_0_1.md)

## 参考项目的取用

- **API42**。可直接复用“参数结构、语义角色、约束”的适用性核查。先确认是索引、掩码、梯度还是控制属性，再决定待比较语义。API42 的跳过条件记录测试构造的范围。机理排除仍需当前错误动作的正面反证。[API42 原定义](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/baseline/knowledge/trigger_library.md:34>)
- **V4**。采用稳定代码、条件定义、Requires、Skip、构造示范和参考案例的组织方式。用已有模式卡的适用前提、排除和缺证分别承接这些信息。触发轴 `API42:*`、`V4:*` 和机理轴 `MECH-v0.3:*` 按各自分母统计。[V4 原卡与分类口径](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/baseline/knowledge/precision_trigger_knowledge_v4.md:3>)
- **fault_review**。复用已审编目如何从原事件摘要统一表达问题、记录来源、变体和近邻。事件家族归并之后，再结合决定性动作和语义进行模式拆合。主题仅供检索。[固定编目研究](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/fault-review-catalog-audit.md:20>)
- **本地 fault_pattern**。沿用现成的证据包、动作作用域、近邻和四种裁决。对外部 **ascend-op-fault-patterns** 才作具体模式对照。FP-B16 的非连续出参 `AutoContiguous` 路径帮助划界，旧 Concat 的输入错误单独以自身源码证明。[FP-B16 适用范围](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/gitcode_patterns/ascend-op-fault-patterns/patterns/FP-B/FP-B16.md:6>) · [本项目分类入口](./classify.py)
- **ascend-op-issue-analysis**。采用明确约定、实际动作、竞争解释和各自证据的短链。代码缺陷与运行声明分别落作用域。[源码和运行事实的区分](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/gitcode_patterns/ascend-op-issue-analysis/README.md:97>)
- **CANNBot**。采用具体尾块 pattern 的结构，以输入指纹引导查错，再用对齐和非对齐的对照、首错位置和核内切分记录，区分尾块丢失、越域处理和周期性步长错误。对应 C1/C2 的效果仍由当前算子自身证据判定。[尾块卡的机理与验证](<D:/project/精度/fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/sources/gitcode_tools/cannbot-skills/ops/ascendc-precision-debug/patterns/tail-block-misaligned.md:9>)
