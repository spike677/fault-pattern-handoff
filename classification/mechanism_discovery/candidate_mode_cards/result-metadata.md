# 输出形状与返回索引编码

研究决定为 SPLIT_SUBTYPES。适用关系和候选均按固定路径取证。

**正确约定** 输出描述符合规定的轴变换，返回索引沿实际选择轴编码并指向同一结果。

**错误动作** 归约形状只调整部分轴，或输出索引物化时误用尾轴规则。

**失效机制** 结果描述或返回坐标的含义偏离合同。形状推导和输出索引编码是不同首错。

**七条边界** L1 要实际物理访问。FM-02 在 Host 描述，N09 在返回的 index 值，正确 values 也能伴随错误 indices。

## 子型

- **归约形状只更新部分轴**（FM-02）。AddLayerNorm 的 mean/rstd 被赋错误 shape。
- **返回索引误按尾轴编码**（N09）。TopKCopy 没将实际 dim 传入生成路径。

## 已核固定材料

- **FM-02** CASE-0319-M1，STATIC_ROOT。旧 InferShape 只把 rankX-rankGamma 那一维设 1，同一 shape 交给 mean 和 rstd。两条或更多归约轴且其他被漏轴长度大于 1 时，描述仍带该原长度。下游描述校验消费 mean/rstd 的 shape。源码支持描述违约，原现场 dtype/数值待核。 [FM-02 原件](https://gitcode.com/cann/ops-nn/merge_requests/8804)
- **N09** CASE-0284-M1，STATIC_CONDITIONAL。TopKCopy 旧调用无 axis，生成扁平 Arange 后用 k 取余并写 indices。非尾选择轴的索引坐标沿错误轴变化。值的复制可能正确，错误可仅在返回的索引张量。旧侧证据来自关联 PR7456，PR7522 发布版本单列。 [N09 原件](https://gitcode.com/cann/ops-nn/merge_requests/7522)

## 近邻和边界

- **EX-27** 输出类型签名、输出 shape 与返回索引值的编码分别在不同生产阶段。属于编译作用域。 [EX-27 原件](https://gitcode.com/cann/ops-nn/merge_requests/4627)

## 还需验证

分别补多轴描述的消费者和非尾轴索引的同版反向对照。EX-27 输出签名冲突仅作配置/编译近邻。

[固定证据表](../cluster_evidence.csv) · [近邻矩阵](../near_neighbor_matrix.csv) · [机理簇及锚点](../historical_mechanism_clusters.json)
