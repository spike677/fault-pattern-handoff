# 数据特殊值及内部协议解释

研究决定为 SPLIT_SUBTYPES。适用关系和候选均按固定路径取证。

**正确约定** 同版定义的非有限数据或内部状态应按适用规则传播、选分支或解码。

**错误动作** 把应传播的非有限数据替换成有限值，或把无贡献内部标记交给普通数值运算。

**失效机制** 给定值或内部标记已存在且被正确读取。首差来自本阶段解释而影响下游结果。

**七条边界** P2 的对象是特殊接口参数。C1/C2 的下游关系仍以实际算术消费及逻辑资格成立为准。

## 子型

- **已存在非有限数据的传播**（N16）。EX-24 固定另有证，GridSampler 保留原案范围。
- **内部无贡献标记的解释**。EX-43 的 POS_INF LSE 进入 max/sub，应核生产与消费的标记合同。

## 已核固定材料

- **N16** CASE-0012-M1，UNRESOLVED_CAUSAL_CHAIN。原 GridSampler 的 Select 将非有限坐标改为 −100，之后才继续反射/邻点选取。旧坐标变化有明确 diff，原 Inf 现场应有梯度及最早错误的输出消费者未闭合。Cdist EX-24 独立验证已存在 NaN 被压成有限值。保留原代表与新代表各自范围。 [N16 原件](https://gitcode.com/cann/ops-cv/merge_requests/904)

## 近邻和边界

- **EX-24** 固定 Cdist 可以支持已有特殊数据传播子型，不替代未闭环 GridSampler。原证据限同版本 fminf 原语和已定位的 Cdist 路径。 [EX-24 原件](https://gitcode.com/cann/ops-math/merge_requests/2743)
- **EX-43** 内部阶段标记送入 max/sub 与 NaN 传播及接口参数 P2 各不同。全无效分片的规定输出及被消费的无资格贡献还需独立核对。 [EX-43 原件](https://gitcode.com/cann/ops-transformer/merge_requests/561)
- **EX-06** 只有同版合同要求透传该 grad，且旧选择零实际交给输出时才支持 C2。不按特殊接口参数 P2。NaN 透传合同仍是适用条件。 [EX-06 原件](https://gitcode.com/cann/ops-nn/merge_requests/8553)

## 还需验证

GridSampler 原 Inf 反射合同待核。EX-43 全无效分片合同不明。EX-06 需同版本 NaN 梯度规则闭合。

[固定证据表](../cluster_evidence.csv) · [近邻矩阵](../near_neighbor_matrix.csv) · [机理簇及锚点](../historical_mechanism_clusters.json)
