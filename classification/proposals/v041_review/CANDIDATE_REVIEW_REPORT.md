# v0.4.1 七张候选卡的根因审查

七张卡均有具体动作、适用约定、源位置、近邻判据、诊断和可模拟动作。决策为四张 `REFINE`、一张 `NEW_CANDIDATE`、两张 `REUSE`。`REUSE` 在本报告中指复用有据的历史子机制条款。候选审核使用冻结 `MECH-v0.3` 和 v0.4 证据基线 `dfca7e1dcc1cc11a060b302244dc388841a6fc94`。[逐卡记录及源哈希](candidate_review.json)

| 卡片 | 决策和适用范围 | 实际最近邻与准入证据缺口 |
| --- | --- | --- |
| NUM-01 | `REFINE`。E06 在 F16 V 的 CPU 单块 attention 循环内更新 FP16 状态，最后才转宽。 | V406 在 SUM 前单次平方已溢出。EX-37 约定逐 rank 在目标类型舍入，旧路径延迟该舍入。候选分类回归待接入。已有一个正例家族。[E06 原 PR](https://github.com/ggml-org/llama.cpp/pull/29810) · [V406 原 PR](https://github.com/pytorch/pytorch/pull/90028) · [EX-37](https://gitcode.com/cann/ops-transformer/merge_requests/8544) |
| NUM-02 | `REFINE`。G05 普通小 kernel 的两矩在 FP32 归约，`E[x²]−E[x]²` 估计的方差交给 `rsqrtf` 并形成向量输出。 | E06 的偏差在状态存储宽度。EX-25 的旧九项指数缩放为近似与拟合问题。最小原始矩差条件有源码支持，宽度 4 的那次作者复现未绑定实际派发。候选分类回归待接入。[G05 固定旧消费者](https://github.com/microsoft/onnxruntime/blob/a926b837fb8a39b0e4840fcb997ff1336cdf5db1/onnxruntime/contrib_ops/cuda/bert/layer_norm.cuh#L162-L180) · [EX-25](https://gitcode.com/cann/ops-math/merge_requests/4131) |
| CTRL-01 | `NEW_CANDIDATE`。EX-32 无 bias 旧 helper 从排序目标 D 读回 D，局部动作与数据源 S 的角色相冲突。 | V402 的 P1 错读上限参数，C1 是有据下游。EX-30 在正确缓冲上覆写活跃值。EX-32 还需完整父版的 S/D 交付与排序链，及把同补丁屏障改动独立控制的证据。[EX-32](https://gitcode.com/cann/ops-transformer/merge_requests/5059) · [V402](https://github.com/pytorch/pytorch/pull/7091) · [EX-30](https://gitcode.com/cann/ops-math/merge_requests/3745) |
| CTRL-02 | `REUSE`。FM-11 的规划候选子机制适用。EX-42 的 after-sort 先递减再验证，漏掉条件上可行的初值 1。 | EX-26 低估并存缓冲预算，EX-03 在实际 kernel 归约中漏必需贡献。EX-42 的 pre-sort hunk 仅到循环入口，正式回归限 after-sort 的旧路径。[EX-42](https://gitcode.com/cann/ops-nn/merge_requests/1537) · [EX-26](https://gitcode.com/cann/ops-math/merge_requests/1788) · [EX-03](https://gitcode.com/cann/ops-nn/merge_requests/5348) |
| ADDR-01 | `REFINE`。把宽泛的偏移项遗漏收窄到合轴块的边界交集。EX-14 可静态定位四行范围被旧判断跳过。 | G07 用密排假定替换了真实 batch stride，V403 的字节跨度错当元素跨度。EX-14 原设备块参数及最终消费仍需对应。[EX-14](https://gitcode.com/cann/ops-transformer/merge_requests/1878) · [G07](https://github.com/pytorch/pytorch/issues/181133) · [V403](https://github.com/microsoft/onnxruntime/pull/33598) |
| REP-01 | `REFINE`。把 N12 的存储契约收窄到同址标量解码。EX-21 旧标量读取以数据元素 T 的宽度解码，作者说明 BF16 元素路径的标量实为 FP32。 | V403 是正确表示对象内地址错。应补旧版真正的 scalar producer 与实际乘加消费锚点。PR6728 直接支撑旧 hunk，PR6974 仍为关联材料，scalar_list 另查。[EX-21 直接 PR](https://gitcode.com/cann/ops-nn/merge_requests/6728) · [关联 PR](https://gitcode.com/cann/ops-nn/merge_requests/6974) |
| SYNC-01 | `REUSE`。FM-05 的完成通知代际子机制适用。EX-40 的发布与等待比较固定值，旧标记若残留可通过新轮判断并触发 DataCopy。 | EX-41 的先错是未齐集的 SyncAll 参与者。EX-40 要补同址跨轮实际时序与精度消费。发布和等待的直接来源为 Dispatch PR757。Combine PR764 单列。[Dispatch PR757](https://gitcode.com/cann/ops-transformer/merge_requests/757) · [EX-41](https://gitcode.com/cann/ops-nn/merge_requests/8667) |

## 边界复算

- NUM-01 的合成同序贡献 `2048,1,1` 每步留在 FP16 时最终仍为 2048，按宽状态可得 2050。V406 的局部 norm 512 可表示，平方 262144 才越过 FP16 的最大有限值 65504。FULL_SHARD 的两个分片各参与一次。两种机制分别记录跨迭代状态与下一道逐元素运算的结果范围。
- NUM-02 用同样可表示的值 `4095.5,4096.5`。正确舍入到 FP32 的均值与原始二阶矩已经不足以恢复小方差，原始矩差为 0，中心二阶矩为 0.25。历史 LogAddExp 先求 `1+t` 再对数的微量吸收共享有限精度求值上位关系，实例执行动作不同。[G05 旧矩与消费者](https://github.com/microsoft/onnxruntime/blob/a926b837fb8a39b0e4840fcb997ff1336cdf5db1/onnxruntime/contrib_ops/cuda/bert/layer_norm.cuh#L135-L180) · [历史 LogAddExp](https://gitcode.com/cann/ops-math/merge_requests/3631)
- EX-14 的明示静态参数为 `gSize=5, gS1Idx=5055, dealRowCount=64, bottom=1023, actS1Size=1024`。精确区间 `

## 准入与复算

NUM-01、NUM-02 的代表、实际近邻、必要判据和排除条件已成型，可先用于候选目录评审。CTRL-01 有一处已定位的独立局部动作。CTRL-02、SYNC-01 的历史复用限各自子机制。其余卡片的未闭合源链分别记录。所有卡片作为正式叶级的分类回归待接入。

历史聚类提供两个数值候选的上位与近邻依据。中间缓冲选源、标量解码和同步代际在分组中共享若干生产消费原件，各自按首错区分。交叉索引以工作包 C 的研究簇身份为准。[历史机制聚类](../../mechanism_discovery/historical_mechanism_clusters.json)

历史根因比较中，FM-11 与 C2 的交集要沿执行期消费者证明，N23 的空间几何与 C1/C2 关系依赖目标实际贡献，N10 部分实例的实际寻址单位错误对应 L2。D 表链接这些边界，EX-32 仍是算子内的选源动作，N20 的一般映射沿用历史谱系。[逐对边界裁决](../../history_mapping_v2/overlap_decisions.json)

[静态边界示例及复算入口](../../V041_IMPLEMENTATION_REPORT.md#独立复算)
