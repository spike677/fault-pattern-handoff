# v0.4.1 历史根因校准与目录扩展

公开版源自审计提交 `3067d55d354d77dd2b476c894b1365f979685922`。工作基线为 `dfca7e1dcc1cc11a060b302244dc388841a6fc94`，七条正式试点机理用 `MECH-v0.3`，事实和评分用 0.3.1。历史对照以合同、首错位置、实际动作、消费者和可区分的近邻裁决。旧评估、事后审计、补证与新家族读件按其原归档记录。

| 任务 | 交付结果 |
| --- | --- |
| A 七条方法收尾 | 依赖绑定补证两轮各 1/1，三项旧近邻复读各 3/3，两个跨算子新案两轮各 2/2，冻结 269 个旧文件 |
| B 历史根因边界 | 13 个历史身份展开 21 个已登记配对，引用 26 个固定 EX。14 对部分重叠、1 对限定父子关系、1 对不同机制、5 对待核 |
| C 目录外机制研究 | 27 个历史身份分为 14 个研究簇，61 条证据明细和 48 组近邻比较，子型记录首错差异 |
| D 七张候选卡审查 | 4 张收窄适用范围，2 张复用历史子机制，1 张保留为独立候选 |
| E 目录版本 | `MECH-v0.4-candidate` 登记两张优先审议卡。正式准入数 0 |
| F 独立验证 | 等待候选分类回归和正式版本冻结。未来家族留出沿用独立保管与锁后揭封 |

## 历史机制边界

FM-15 的冻结离线资源错源条款属于 P1 具体子型。FM-20 的 QBMM 固定代表写入了错误的存储元数据，与 L1 的密排地址公式区分。V403 的一个预打包写动作同时满足 FM-04 的越界偏移和 L2 的字节单位错误。这个交集限该固定路径。整条历史卡等价为 0。[根因边界报告](history_mapping_v2/ROOT_CAUSE_BOUNDARY_REPORT.md) · [逐对明细](history_mapping_v2/root_cause_pair_review.csv)

27 个历史身份中，8 个可定位固定路径首错，11 个只能在明示条件下静态确认。6 个仍缺旧路径或因果链，2 个属于可靠性边界。EX-21 的窄解码动作可定位，FP32 生产语义见作者说明，旧生产实参和乘加消费仍待核。该案只作为部分支持。[聚类报告](mechanism_discovery/MECHANISM_DISCOVERY_REPORT.md) · [证据表](mechanism_discovery/cluster_evidence.csv) · [近邻表](mechanism_discovery/near_neighbor_matrix.csv)

## 候选目录

优先审议 NUM-01 和 NUM-02。E06 的首次失真发生在反复保存 FP16 累加状态时。G05 在固定小核中以 FP32 相减两个原始矩，丢失小方差。V406 在跨 rank 求和之前的单次平方处溢出，作为 NUM-01 的近邻。G05 原报告的具体形状和小核派发仍待绑定。两张卡已有真实代表和近邻，候选分类回归待接入。[七卡审查](proposals/v041_review/CANDIDATE_REVIEW_REPORT.md) · [候选目录](proposals/v041_candidate_catalog.json)

## 方法收尾

ReduceSumSquare 的旧原封存、事后审计严格分均为每轮 0/1。新补证视图验证固定依赖绑定，只在受评静态路径接受依赖条文。两轮均准确引用合同，作为已证目录外各得 1/1。OpenVINO 的报告级 C2、NumPy GCD 的合规状态、DSPARK 的同源 C3 复读各两轮正确。[方法报告](validation_0_4_1/METHOD_CLOSEOUT.md)

新案 V411（vLLM NIXL MoE）和 V412（CUDA adaptive_max_pool2d.out）分别为 P2、L1 增加第二个独立双轮算子。旧输出视图的写回地址有直接源码证据。新案均为固定旧源码静态评估和流程演练。与原独立首读合计 28 个家族，按 0.4 原覆盖规则七条均达到该轮的观察条件。原历史覆盖数据继续按原批次复算。[双轮判卷](validation_0_4_1/operator_holdout/OPERATOR_HOLDOUT_REPORT.md) · [七模式覆盖矩阵](validation_0_4_1/operator_holdout/mode_coverage_matrix.csv)

## 独立复算

在这个公开版本的检出根目录运行下列命令。第一条检验固定依赖绑定与已有分类回归，第二条重算候选卡的七个静态数值与边界示例。

```powershell
python -B -X utf8 -m unittest discover -s classification -p 'test_*.py'
python -B -X utf8 classification/proposals/v041_review/recompute_examples.py
```

原封存、事后审计和补证成绩依据完整本地审计包。从审核 Git bundle 检出源提交后运行 `python -B -X utf8 classification/validation_0_4_1/verify.py`，可逐轮复算锁定答卷和历史分数。
