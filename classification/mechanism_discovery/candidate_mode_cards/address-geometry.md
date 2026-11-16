# 对象内寻址缺少几何项

研究决定为 REFINE_EXISTING_PARENT。适用关系和候选均按固定路径取证。

**正确约定** 在正确对象中按逻辑组、轴内余数和实际局部坐标计算偏移。

**错误动作** 遗漏非首组的基址项，或整除只保留商而丢失合轴的实际余数。

**失效机制** 对象和单位可正确，地址函数仍因漏几何项而选错区间，后续消费错误地址。

**七条边界** 可停在寻址上位。L1 要密排代用，L2 要单位换算，P1 要错源。组基址与合轴除法保留各自公式。

## 子型

- **分组基址被省略**（N06）。ExtendConvTranspose 的非首组 VECTOR_QUANT scale 被定位到首组。
- **合轴路线上整除丢余数**。EX-14 支持寻址上位，仍需具体必须清零而未清的坐标。

## 已核固定材料

- **N06** CASE-0198-M1，STATIC_ROOT。旧 CalcScaleOffset 不收 groupIdx，向量路径只乘 nCoreIdx_*singleCoreCin。合法非首组会与首组共享 scale 起点。量化消费该对象内错误索引。此份 diff 只证明实际 scale 偏移，不推到另一个 offset 数组。 [N06 原件](https://gitcode.com/cann/ops-nn/merge_requests/4616)

## 近邻和边界

- **EX-14** 同属对象内地址几何缺项，遗漏组基址与丢合轴余数分别定义。寻址上位已有据。每个具体清零/计算成员真实的范围仍待核。 [EX-14 原件](https://gitcode.com/cann/ops-transformer/merge_requests/1878)

## 还需验证

补不同算子的几何子型，以及同版本组 0 或不丢余数的真实反向对照。EX-14 的实际局部清零集合仍需闭合。

[固定证据表](../cluster_evidence.csv) · [近邻矩阵](../near_neighbor_matrix.csv) · [机理簇及锚点](../historical_mechanism_clusters.json)
