# 27 条不同机制的根因聚类

从 `dfca7e1dcc1cc11a060b302244dc388841a6fc94` 的历史对照取 27 个 `不同机制` 身份。每个身份在研究簇中只出现一次，条款定义、实际代表、错误动作、首次错误状态、消费者和证据范围逐条保存。14 个簇之下保留可区分的子型。补充样本和近邻共 34 条记录，矩阵含 48 组比较。同一案例用于多组近邻时仍共用一个事件。当前正式准入数为 0。[研究簇与校验摘要](historical_mechanism_clusters.json) · [证据明细](cluster_evidence.csv) · [近邻判据](near_neighbor_matrix.csv)

| 历史代表证据范围 | 身份数 | 使用方式 |
| --- | ---: | --- |
| `STATIC_ROOT` | 8 | 固定路径可定位合同、首错及相应阶段的消费。阶段输出可与最终设备输出分开 |
| `STATIC_CONDITIONAL` | 11 | 代码动作可定位。使用受评条件证明实际违约，进一步的设备效果按原件约束 |
| `UNRESOLVED_OLD_PATH` | 3 | 保留 FM-24、FM-28、FM-29 的历史身份和候选判据，具体旧侧消费待核 |
| `UNRESOLVED_CAUSAL_CHAIN` | 3 | N03、N12、N16 原代表的实际首错待核。EX 补充只支持各自事件 |
| `RELIABILITY_BOUNDARY` | 2 | FM-01 和 FM-14 保留终止、准入及进展作用域 |

这些是 27 条的证据状态计数。报告所列旧源码、可固定的旧侧 hunk 与有限输入例用于机制判别。设备复现沿用原材料状态。

## 簇与子型

| 研究簇 | 历史身份 | 决定性的动作边界 |
| --- | --- | --- |
| [数值转换时机与模式](candidate_mode_cards/conversion.md) | FM-08、FM-24、N15 | 过早窄化、运行状态类型和应在末端执行的舍入模式分别核对 |
| [有限输入的中间浮点溢出](candidate_mode_cards/overflow.md) | FM-17、FM-28 | 首次超出真实格式范围。缩放顺序、合并前平方和逐步累加分别取证 |
| [有限精度表达式与累加次序](candidate_mode_cards/evaluation.md) | FM-09、FM-10 | 相同数学目标可由 1+t 吸收、原始矩相减或不同加法树产生不同误差 |
| [精确整数位置的表示失真](candidate_mode_cards/integer-representation.md) | FM-16、FM-29 | 整数回绕与无证的浮点中转丢低位候选并列，和正确尺度下漏几何项分开 |
| [计算项被放入错误数值域](candidate_mode_cards/formula-domain.md) | FM-23 | 同一个 bias 参与一次，反量化时点错误改变对该项的实际尺度 |
| [数据特殊值及内部协议解释](candidate_mode_cards/special-data.md) | N16 | 非有限数据传播和阶段标记解释分别验证。原 GridSampler 及固定 Cdist 补充各有边界 |
| [控制语义、模板和计划选择](candidate_mode_cards/dispatch.md) | FM-12、N26 | 错选已有实现、普通参数未落实、丢掉可行搜索候选是不同首错 |
| [入口合法性校验](candidate_mode_cards/validation.md) | FM-14、N21 | 不支持的硬件配置漏拦与合法逻辑视图误拒有不同的约定来源 |
| [空路径终止与输出义务](candidate_mode_cards/empty-path.md) | FM-01、N02 | 完全无任务、已有在途任务、有非空输出待物化需分别判断 |
| [输出形状与返回索引编码](candidate_mode_cards/result-metadata.md) | FM-02、N09 | 输出描述元数据与已写出的索引值各有自己的消费者 |
| [中间容量与实际访存宽度](candidate_mode_cards/buffer-extent.md) | FM-19、N11 | 单实体容量不足、总驻留计费和已经发出的实际访存分别证明 |
| [对象内寻址缺少几何项](candidate_mode_cards/address-geometry.md) | N06 | 组基址遗漏与合轴丢余数可支持寻址上位。L1 和 L2 各有额外必要条件 |
| [生产消费表示与保位操作](candidate_mode_cards/representation-handoff.md) | N12、N13 | 读取宽度、实际算术保位及内部语义缓冲身份分开 |
| [同步身份和活跃存储生存期](candidate_mode_cards/dependency-lifetime.md) | FM-05、N03、N22 | 缺少流水完成边、跨轮标记、屏障参与者和确定性覆盖分开 |

## 会改变候选审查的几项证据

- DropOutV3 旧 `GetFirstValueAsFloat<double>` 在求补前做一次窄化，`p=1−2⁻²⁶` 时旧概率为 0。llama.cpp E06 的 FP16 状态每次归约更新都丢精度，EX-37 则在约定需要逐 rank 舍入时选择 FP32 汇总后才 Cast。三者各有独立适用约定。FSDP V406 的首次 Inf 发生在 SUM 前的局部平方，当前支持中间范围子型，FM-28 的实际累加器溢出继续待核。[转换与舍入](candidate_mode_cards/conversion.md) · [浮点溢出](candidate_mode_cards/overflow.md)
- ONNX Runtime 的固定小核 G05 在 FP32 形成相近原始矩之差，LogAddExp 的旧表达式则在进入 Log 前把正小量吸收到 1。FlashAttentionScore 的完整旧 hunk 另证同一 dtype 下 Base16、256、512 的加法树差异。这三种首错各需反例。EX-25 的近似误差预算及 EX-08 在实数域即不等价的离散权重留作边界。[求值与加法树](candidate_mode_cards/evaluation.md)
- Foreach EX-21 的旧消费者固定按 `T` 解码，FP32 scalar 生产约定来自补丁作者说明，旧实际生产路径与最终乘加仍待核。MatMulV3 N13 的首错是以 half 算术处理本应保位重排的 BF16 内容。MoeGatingTopK EX-32 改的是所选中间缓冲身份，同补丁还移动了屏障。按固定旧读写可保留独立候选，原父版和同步反证仍待核。[表示协议与缓冲身份](candidate_mode_cards/representation-handoff.md)
- FM-19 回查 PR 3558 两个旧量化 Matmul 初始化文件，确认短输出仍执行整块 DataCopy。V16 精简代表中的新增 helper 单独保留为修复参照。同一事件的 PR 3114 旧侧有相同物理足迹，支持明确的短对象分支。N22 的 GeGLUGradV2 则由旧 `t2=Buf4` 和修复中未改的 FP16 `xBufRight`、后续 PDF 消费组成确定性覆盖链。[访存宽度](candidate_mode_cards/buffer-extent.md) · [活跃存储](candidate_mode_cards/dependency-lifetime.md)

## 复核线索

证据表的每条锚点包含来源键、JSON Pointer 或文本行范围、原样节选及摘要。来源键在主 JSON 的 `sources` 中映射到检出、总工作区或本机原件缓存，附 SHA-256。旧侧 diff 的节选排除新增代码。标记为修复对照或未变上下文的引用用于连接相同代码段，版本按原件登记。EX 映射的检索链接与本轮实际绑定的固定代表和近邻分别储存。对照中缺合同、设备轨迹、另一独立家族或合规反向证据时，在卡片按具体动作记录。[0.4 对照](../history_mapping/mode_crosswalk.json)
