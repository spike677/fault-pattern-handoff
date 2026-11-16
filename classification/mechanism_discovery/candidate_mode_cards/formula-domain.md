# 计算项被放入错误数值域

研究决定为 KEEP_CANDIDATE。适用关系和候选均按固定路径取证。

**正确约定** 保持各项的数学作用和变换域。实值 bias 应在指定乘积反量化之后相加。

**错误动作** 将应在实数域消费的贡献提前放入待缩放累加器，令反量化同时作用于它。

**失效机制** 固定输入、类型和项次数后，dequant(acc+bias) 与 dequant(acc)+bias 仍可能不等价。

**七条边界** C2/C3 的项账本可保持各一次。N06 是读另一组尺度，即使公式正确也会发生。

## 子型

- **反量化与实域偏置顺序**（FM-23）。QBMM 旧混合路径只为 int8 激活实值 bias epilogue。

## 已核固定材料

- **FM-23** CASE-0231-M1，STATIC_CONDITIONAL。旧 isBiasEpilogue 以 int8 为前提，低浮点的实值 bias 留在待缩放阶段。bias 与 matmul 累加量进入同一反量化式。可推导同一 bias 被额外缩放。固定范围及 epilogue/UB 消费路径尚需第二独立实证。 [FM-23 原件](https://gitcode.com/cann/ops-nn/merge_requests/5390)

## 近邻和边界

- **EX-08** 精确离散谓词被连续式替换不同于迁移偏置到错误数值域。不从权重近似自动推断缺项。 [EX-08 原件](https://gitcode.com/cann/ops-math/merge_requests/3278)

## 还需验证

核另一个融合算子和反向对照，如尺度为 1 或合同将 bias 定义在量化域。当前限固定低浮点、FP32 scale 与 bias 路径。

[固定证据表](../cluster_evidence.csv) · [近邻矩阵](../near_neighbor_matrix.csv) · [机理簇及锚点](../historical_mechanism_clusters.json)
