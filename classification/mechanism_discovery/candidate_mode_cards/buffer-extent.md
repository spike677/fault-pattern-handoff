# 中间容量与实际访存宽度

研究决定为 SPLIT_SUBTYPES。适用关系和候选均按固定路径取证。

**正确约定** 同一对象的活跃需求在容量内，物理搬运的真实跨度在合法对象范围内。

**错误动作** 低估中间实体的必要容量，或在起点可以正确时发出比合法范围更宽的实际访问。

**失效机制** 第一种先出现不足的分配上界，另一种先出现非法访问足迹。可相继发生，需分别核首错与消费者。

**七条边界** 按正确单位发出 32B 仍会超出小于 32B 的真实对象。L2 需地址比例错误。C2 需实际遗漏项。

## 子型

- **固定搬运宽度超对象**（FM-19）。历史算子名 Inc，固定锚点在量化 Matmul 输出清零代码。
- **单实体必要容量低估**（N11）。UpsampleBicubic2DAaGrad 的采样列表容量需真实边界。

## 已核固定材料

- **FM-19** CASE-0157-M1，STATIC_CONDITIONAL。旧两个初始化实现均发起 DataCopyParams(1,1,0,0) 的整块 DataCopy，回退起点不能使 32 B 落入不足 32 B 的对象。真实物理访问跨度越出对象。触发是在有效入口发出拷贝，非起点换算错误。确认短对象清零分支。没有原运行的具体受影响内存对象，两个代码文件属于同一事件。 [FM-19 原件](https://gitcode.com/cann/ops-nn/merge_requests/3558)
- **N11** CASE-0010-M1，STATIC_CONDITIONAL。旧 getQueueSize 将 2*(slide+support)/scale 转整数后加一，边界候选上界仍少于所需。真实枚举合法边界时可能先低估 queueSizeW/H。旧公式可核。实际设备访问、数据破坏、缺项与特定维度的生效各待核。 [N11 原件](https://gitcode.com/cann/ops-cv/merge_requests/676)

## 近邻和边界

- **EX-26** 并存缓冲总量的预算少计，区别单实体容量和已发出实际越宽的数据搬运。未定位实机破坏地址。 [EX-26 原件](https://gitcode.com/cann/ops-math/merge_requests/1788)
- **EX-03** 中间容量风险与 SmallR 提前返回是两个需要各自证明的动作。原实际 ubFactor/shape 未复跑。只有实际缺失项可计 C2，不从固定 512 B 推内存破坏。 [EX-03 原件](https://gitcode.com/cann/ops-nn/merge_requests/5348)
- **EX-39** 对齐在可用容量内也可能切错语义工作单元，与容量本身低估分开。限固定 gather 切分条件。 [EX-39 原件](https://gitcode.com/cann/ops-math/merge_requests/1017)

## 还需验证

FM-19 限两个量化 Matmul 的明确短输出清零分支，同一事件只计一次。N11 补实际枚举上界及访问。总驻留预算 EX-26 单独比较。

[固定证据表](../cluster_evidence.csv) · [近邻矩阵](../near_neighbor_matrix.csv) · [机理簇及锚点](../historical_mechanism_clusters.json)
