# 精确整数位置的表示失真

研究决定为 KEEP_CANDIDATE。适用关系和候选均按固定路径取证。

**正确约定** 供地址或计数消费者使用的整数，在同一单位及合法尺寸下应按合同精确保留。

**错误动作** 用位宽或精度不足的中间类型保存位置，造成回绕、截断或失去低位。

**失效机制** 实际位置的数值先失真，随后错误整数被用于地址或计数。需核各运算操作数和返回变量。

**七条边界** 正确换算比例仍可能错表示。L2 需证明比例错误，L1 需原视图的密排替代。

## 子型

- **整数回绕**（FM-16）。TopKV2 将 workspace 字节位置累加到 uint32_t。
- **整数经浮点中转丢低位**（FM-29）。历史候选保留。EX-38 是 RNG dtype 与分块耦合。

## 已核固定材料

- **FM-16** CASE-0035-M1，STATIC_CONDITIONAL。将地址累计状态存 uint32_t，后续继续以该变量对应 GM 段。字节偏移跨有效类型范围时截断或回绕，4 GiB 是 uint32_t 的边界。后续排序的临时区域可能重叠。改变量宽度仍不保证乘法操作数在所有更大尺寸中足够宽。 [FM-16 原件](https://gitcode.com/cann/ops-math/merge_requests/2180)
- **FM-29** 历史原代表待核，UNRESOLVED_OLD_PATH。历史候选线索是高 stride 条件下地址经 FP32 中转丢精度。未找到实际整数到浮点再到整数的旧路径与地址消费者。同位宽边界限定的整数回绕可比较。EX-38 改的是 RNG 输出 dtype 与切分，不能替代。

## 近邻和边界

- **EX-38** 从 FP32 RNG 中转触发序列分块变化不证明整数先经 FP32 再恢复为地址。不能以补丁的切分强化推出旧 32768 元素阈值。 [EX-38 原件](https://gitcode.com/cann/ops-math/merge_requests/4005)
- **EX-09** remaining 被额外递减是更新动作，值域容量可充足。与 32 位表示不足区分。只有实际必要后半 lane 无其他路径时判 C2。 [EX-09 原件](https://gitcode.com/cann/ops-math/merge_requests/4579)

## 还需验证

TopKV2 扩大域时还要核乘法操作数位宽。FM-29 要旧整数到浮点、还原到实际地址并被消费的链。

[固定证据表](../cluster_evidence.csv) · [近邻矩阵](../near_neighbor_matrix.csv) · [机理簇及锚点](../historical_mechanism_clusters.json)
