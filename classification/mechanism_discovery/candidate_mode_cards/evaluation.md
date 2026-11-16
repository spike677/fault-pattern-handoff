# 有限精度表达式与累加次序

研究决定为 SPLIT_SUBTYPES。适用关系和候选均按固定路径取证。

**正确约定** 固定有效项、数学目标、类型及适用误差或一致性要求，旧求值实现应满足该约定。

**错误动作** 使用发生吸收或抵消的等价表达式，或改变受合同约束的浮点累加配对。

**失效机制** 逻辑项可完整到达。舍入误差来自表达式或加法树，近似实现的误差预算另核。

**七条边界** C2/C3 的逻辑成员与次数可保持。EX-08 实数域已不等价，归精确公式近邻。

## 子型

- **先舍掉小量再求非线性函数**（FM-09）。LogAddExp 的 1+t 在旧加法后吸收小量。EX-25 是近似预算邻例。
- **相近大数相减消减**。G05 的 FP32 原始矩差经 rsqrt 影响输出。
- **相同项的累加配对次序**（FM-10）。同一 FlashAttentionScore 事件中 Base16 与 Base256/512 的加法树不同。

## 已核固定材料

- **FM-09** CASE-0061-M1，STATIC_ROOT。先用 OpAdds 算舍入后的 1+t，再把它作为 Log 的输入。1+t 在对应 dtype 舍入为 1，即使 t 自身仍可表示。Log 输出 0，进一步与最大值合并。报告包含近零偏差。新路径所有异常值行为未验证。 [FM-09 原件](https://gitcode.com/cann/ops-math/merge_requests/3631)
- **FM-10** CASE-0518-M1，STATIC_CONDITIONAL。Base16 将两半区分别喂给部分链，Base256/512 同目的位置逐行更新一条链。同一项集的浮点组合顺序随模板切换变化。指数和被后续 Div 消费。旧完整差异可回查。现场数值与模板触发未作新的测量。 [FM-10 原件](https://gitcode.com/cann/ops-transformer/merge_requests/9995)

## 近邻和边界

- **G05** 同为在有限精度上求等价数学量，原始两矩相减消减与 log1p 小量吸收仍是不同子型。作者另报特定宽度 NaN，未证明该次调用确实派发此小核。 [G05 原件](https://github.com/microsoft/onnxruntime/pull/33357)
- **EX-25** 受误差预算约束的近似幅度与等价式因舍入失稳需要独立判据。固定近似算法的调整有据。原失败域与近似预算尚需另证，不将任意省略级数项判 C2。 [EX-25 原件](https://gitcode.com/cann/ops-math/merge_requests/4131)
- **EX-08** 同一实数规则下已不等价，区别有限精度吸收、消减和加法树。实际资格和漏项需逐目标梯度单独证明。 [EX-08 原件](https://gitcode.com/cann/ops-math/merge_requests/3278)
- **EX-37** 变更每步/末端的精度与更换同类型的配对顺序为独立动作。未固定小算子完整 rank 拓扑。 [EX-37 原件](https://gitcode.com/cann/ops-transformer/merge_requests/8544)

## 还需验证

G05 固定小核和作者报告范围分开。再补独立方差消减、实际模板派发，及明确近似误差预算。

[固定证据表](../cluster_evidence.csv) · [近邻矩阵](../near_neighbor_matrix.csv) · [机理簇及锚点](../historical_mechanism_clusters.json)
