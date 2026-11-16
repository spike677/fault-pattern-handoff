# 控制语义、模板和计划选择

研究决定为 SPLIT_SUBTYPES。适用关系和候选均按固定路径取证。

**正确约定** 实际执行路径须实现调用要求，合法规划候选应在淘汰前按合同检查。

**错误动作** 用不完整的能力条件选择模板，或已取得普通设置却启用恒等路径。规划器也可能在验证前淘汰候选。

**失效机制** 首错在 Host 资格、派发或枚举，输出项是否缺失仍取决于真正的执行和消费者。

**七条边界** P1 要对象错源，P2 要特殊参数状态按普通值处理。计算项遗漏须有 C2 的目标消费链。

## 子型

- **能力条件不全导致模板错选**（FM-12）。FusedMatmul StreamK/DP 与 FlashAttention EX-11 比较各自的实际资格。
- **普通操作参数未落实**（N26）。Round 的负 decimals 被 dtype 恒等捷径忽略。
- **先淘汰再验证可行候选**。EX-42 的 factor=1 未进入容量比较。

## 已核固定材料

- **FM-12** CASE-0256-M1，STATIC_CONDITIONAL。旧 IsCapable 只查 opType 的支持集合，未排除包含 DP 的配置。带融合请求的 DP tile 被分派到只直接 Fixpipe 写回的分区。DP 实际路径若无融合则部分 y 只含 matmul。Add 有非零必需加数时另按输出链审 C2，不能泛化 Mul。 [FM-12 原件](https://gitcode.com/cann/ops-nn/merge_requests/6658)
- **N26** CASE-0096-M1，STATIC_ROOT。Host 读取 decimals 并计算标志，却统一把 INT32 路径分发至仅 CopyIn→CopyOut 的 RoundInt DAG。负 decimals 仍输出原值。例 15、25 在 -1 处按取偶约定均应为 20。旧 DAG 直接物化错误结果。极端边界的修复策略需另核。 [N26 原件](https://gitcode.com/cann/ops-math/merge_requests/1558)

## 近邻和边界

- **EX-11** 另一个真实算子的模板资格错误。其守卫并非与 FusedMatmul 完全等价。后续超范围需证明实际批号和地址。正确 mask 数据来源可不变。 [EX-11 原件](https://gitcode.com/cann/ops-transformer/merge_requests/5647)
- **EX-42** 错误出现在生成计划前，无已存在的坏执行路径。反对把搜索候选当 C2 数据项。只有存在唯一可行边界候选的预算才成立，需再找另一规划器与合法淘汰对照。 [EX-42 原件](https://gitcode.com/cann/ops-nn/merge_requests/1537)
- **EX-19** 旧 guard 改动有据，但不能从修复 diff 判断普通负 override 的契约。原版本合法负 override、0 的约定和实际消费者未齐。 [EX-19 原件](https://gitcode.com/cann/ops-nn/merge_requests/6931)

## 还需验证

计划候选排除、选择不适用实现、普通参数未落实分别有正反例。EX-42 尚缺第二规划器和合法剪枝对照。

[固定证据表](../cluster_evidence.csv) · [近邻矩阵](../near_neighbor_matrix.csv) · [机理簇及锚点](../historical_mechanism_clusters.json)
