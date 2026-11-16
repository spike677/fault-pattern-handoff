# 生产消费表示与保位操作

研究决定为 SPLIT_SUBTYPES。适用关系和候选均按固定路径取证。

**正确约定** 同一物理对象按约定宽度和位型交付。只重排格式的阶段须保存规定的位载荷。

**错误动作** 按不同宽度或 dtype 读取存储，或把只需重排的数据重新解释后执行改变值的实际算术。

**失效机制** 同一个物理位置的位模式被错解码或被错误算术改写。真正数值转换与指针重解释分别核实。

**七条边界** L2 的对象是地址比例，P1 是参数源。EX-21 地址对象可正确，EX-32 选择的内部缓冲对象已经错误。

## 子型

- **生产的宽度与消费者解码不符**（N12）。Foreach EX-21 的旧读法固定，生产宽度来自作者说明。ReduceAll 为未闭环原代表。
- **保位重排按错误编码执行算术**（N13）。MatMulV3 的 BF16 数据以 half 运算。

## 已核固定材料

- **N12** CASE-0030-M1，UNRESOLVED_CAUSAL_CHAIN。旧 Host 统一分配 DT_BOOL 描述并交给 launcher。EX-21 另见旧消费者按 T 解释标量首元素，作者说明该分支存储为 FP32。旧 ReduceAll 的描述可见，物理写宽与第一个错误字节仍未知。保持 ReduceAll 缺证。Foreach EX-21 为固定消费者与作者所述生产合同的独立比较，旧生产者及最终乘加待核。 [N12 原件](https://gitcode.com/cann/ops-math/merge_requests/2092)
- **N13** CASE-0258-M1，STATIC_CONDITIONAL。将 BF16 位串 ReinterpretCast 为 half，再用 Muls(1) 做实际浮点计算。某些 BF16 位载荷在 half 下属于另一数值类别，进入不保位的算术。结果被物化成重排张量，实际设备 NaN 载荷和 canonicalization 未补测。 [N13 原件](https://gitcode.com/cann/ops-nn/merge_requests/6633)

## 近邻和边界

- **EX-21** 若 T=BF16 的旧受评路径已生成 FP32 scalar，读取会错解同一对象。需要确定写与读的实际宽度，各自对应原调用。旧生产者、实际乘加及首个错误输出待核。ReduceAll A3 与 list 路径另有取证范围。 [EX-21 原件](https://gitcode.com/cann/ops-nn/merge_requests/6974)
- **EX-27** 输出签名失配在编译期已拒绝，不能为实际物理表示冲突作正例。无设备写宽或消费者。 [EX-27 原件](https://gitcode.com/cann/ops-nn/merge_requests/4627)
- **EX-32** 旧首错可定位为读待写 D 而非选中的中间结果 S。与正确对象内类型、存储生存期及接口参数来源分别判。未取得完整父提交与隔离同步变化的实机证据。单一事件可登记候选，当前不满足独立反向对照。 [EX-32 原件](https://gitcode.com/cann/ops-transformer/merge_requests/5059)

## 还需验证

原 ReduceAll 缺内核签名及物理写宽。EX-21 固定旧解码，需补旧 FP32 scalar 生产和实际乘加路径。MatMulV3 保位失败需具体载荷与指令对照。

[固定证据表](../cluster_evidence.csv) · [近邻矩阵](../near_neighbor_matrix.csv) · [机理簇及锚点](../historical_mechanism_clusters.json)
