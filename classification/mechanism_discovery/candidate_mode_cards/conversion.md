# 数值转换时机与模式

研究决定为 SPLIT_SUBTYPES。适用关系和候选均按固定路径取证。

**正确约定** 在同版约定指定的运算和存储边界使用相应类型和转换规则，保留下一运算仍需要的精度。

**错误动作** 在精度仍被需要时降低表示精度，或在指定转换点采用违约的舍入或饱和模式。

**失效机制** 数学式及数据项可以相同，首差发生在转换时点、状态类型或转换模式。后续升精无法恢复已丢信息。

**七条边界** 同一输入对象上的转换与 P1 错源分开。小项舍为零仍可被执行，C2/C3 需核逻辑账本。L2 需位置换算。

## 子型

- **输入过早窄化**（FM-08、FM-24）。DropOutV3 的补数在旧 FP32 下变零。Logspace 仅为待核检索子型。
- **转换舍入或饱和配置错误**（N15）。Sqrt 的末端 CEIL/RINT 可分。EX-35 还须分别定位局部策略与全局控制。
- **逐次归约状态类型或舍入位置不符**。E06 在每次更新过窄。EX-37 不落实合同要求的逐 rank 舍入。

## 已核固定材料

- **FM-08** CASE-0041-M1，STATIC_ROOT。正确取得同一个 double p 后先 static_cast<float>，再用 float 求补。p=1−2⁻²⁶ 时先窄化变 1，prob 成 0，正确应为 2⁻²⁶。tiling 的 prob 在旧侧已可验证错误。现场种子与 kernel 端点消费者未复跑。 [FM-08 原件](https://gitcode.com/cann/ops-math/merge_requests/2701)
- **FM-24** 历史原代表待核，UNRESOLVED_OLD_PATH。V18 描述在计算前按输出 dtype 窄化的线索。未定位固定旧 Cast、输入类型及首个差异值。暂作 FM-08 的检索子型。未用其他算子的窄化代表替换该历史源。 [FM-24 原件](https://gitcode.com/cann/ops-math/issues/2105)
- **N15** CASE-0039-M1，STATIC_ROOT。FP32 结果显式通过 CAST_CEIL 输出。sqrt(2) 的 FP16 最近值约 1.4140625，向上取为 1.4150390625。直接进入 yLocal。原平台和 shape 未公示，模式判据仍要同版本的舍入约定。 [N15 原件](https://gitcode.com/cann/ops-math/merge_requests/2848)

## 近邻和边界

- **E06** 逐次窄更新与一次输入窄化是不同子型。同一独立事件，只支持指定 CPU one-chunk 路径，未作为本轮新运行。 [E06 原件](https://github.com/ggml-org/llama.cpp/pull/29810)
- **EX-37** 两案的指定舍入方向不同。EX-37 与改加法树也分开。具体原失败 dtype/shape 与旧实际 rank 树未恢复，按约定与可区分示例使用。 [EX-37 原件](https://gitcode.com/cann/ops-transformer/merge_requests/8544)
- **EX-35** 转换处必须按合同饱和，与此前的活跃算术已经溢出为不同首错。是关联多路径材料。原 dtype/shape、原控制状态和现场比例仍限制精确溯因。 [EX-35 原件](https://gitcode.com/cann/ops-nn/merge_requests/4322)

## 还需验证

为窄累加补同一精度约定下的第二独立算子与合法输出降精对照。FM-24 的 Logspace 旧路径及消费者待补。

[固定证据表](../cluster_evidence.csv) · [近邻矩阵](../near_neighbor_matrix.csv) · [机理簇及锚点](../historical_mechanism_clusters.json)
