# 同步身份和活跃存储生存期

研究决定为 SPLIT_SUBTYPES。适用关系和候选均按固定路径取证。

**正确约定** 消费只能观察同期已完成的生产结果，对象存储须保持至最后合法消费。

**错误动作** 漏等待、让上一轮通知满足本轮、改变应参与的屏障集合，或在仍有消费者时覆盖活跃存储。

**失效机制** 依赖身份或可见性被破坏，或值的有效期提前结束。串行确定性覆盖与并行竞态可各自成立。

**七条边界** EX-30 条件 C1 是覆盖后的实际参与关系。EX-28 重复释放句柄属于可靠性，C3 只检查计算贡献超次。

## 子型

- **必要完成、代际或参与协议被破坏**（FM-05）。DropOutDoMask 缺同步与 EX-40/41 的代际、参与问题分别核。
- **核内流水同步待核**（N03）。InplaceApplyMomentum 保留原身份，与同号 Moe 转录冲突不得合并。
- **活跃值被另一个动作覆盖**（N22）。GeGLUGradV2 的梯度中间数据被覆盖，EX-30 另为框架重复搬入。

## 已核固定材料

- **FM-05** CASE-0040-M1，STATIC_CONDITIONAL。CopyOut 后立即 FreeTensor，同一循环未建立补丁所示的 MTE3→MTE2 完成边。UB 仍被旧搬出消费时可能已进入可复用队列。后续输入的搬入可覆盖在途内容，导致恒等输出失真。限制在确有竞争窗口的该路径。 [FM-05 原件](https://gitcode.com/cann/ops-math/merge_requests/2684)
- **N03** CASE-0316-M1，UNRESOLVED_CAUSAL_CHAIN。旧从 VECIN 中间张量计算并在 PIPE_V 屏障后直接 DataCopyPad。观察到需核查的流水依赖，尚不能确定生产可见性和标量错误哪一个先发生。生成的 V→MTE3 事件与原现场标量值缺证。VECOUT 变化或修复表现不足以定根。 [N03 原件](https://gitcode.com/cann/ops-nn/merge_requests/8566)
- **N22** CASE-0140-M1，STATIC_ROOT。旧 CDF t2 使用给 FP16/BF16 的 xBufRight 供值的 Buf4，写临时多项式。CDF 的第一个 Muls(t2,...) 已覆盖仍活跃的原 x。后续 ComputePDF 与 Mul(t1,t1,x) 读已覆盖 x。旧 diff 与同修复完整源码的未变调用逐项比对。 [N22 原件](https://gitcode.com/cann/ops-nn/merge_requests/2572)

## 近邻和边界

- **EX-40** 完成代际与缺少核内生产等待独立，前者需当前轮次通知受证。未有真实跨轮 wait 与下一缓冲内容的运行追踪。 [EX-40 原件](https://gitcode.com/cann/ops-transformer/merge_requests/764)
- **EX-30** 已中性化 UB 被后来搬入覆盖是根动作，归约纳入不合格 NaN 是有条件的 C1 下游。要有实际二次搬入和随后归约，未知原故障 tile。 [EX-30 原件](https://gitcode.com/cann/ops-math/merge_requests/3745)
- **EX-28** 句柄释放配对错误与逻辑计算重数分属对象。只见资源归还配对，不能推精度影响。 [EX-28 原件](https://gitcode.com/cann/ops-nn/merge_requests/2947)
- **EX-31** 语言级借用对象失效与写操作覆盖独立。旧材料支持可接受域异常线索，无精度传播。 [EX-31 原件](https://gitcode.com/cann/ops-math/merge_requests/1444)
- **EX-02** 保留同一缓存地址但错将前相位的内容作为仍有效，需查语义缓存失效而非可见性。新增检查是否保守重载不能推出只在当前 phase 的通用行为。 [EX-02 原件](https://gitcode.com/cann/ops-nn/merge_requests/2510)

## 还需验证

补 EX-40 的真实轮次、wait 及消费证据，核 N03 生成事件与标量链。EX-32 读错内部对象属于独立比较，屏障影响另核。

[固定证据表](../cluster_evidence.csv) · [近邻矩阵](../near_neighbor_matrix.csv) · [机理簇及锚点](../historical_mechanism_clusters.json)
