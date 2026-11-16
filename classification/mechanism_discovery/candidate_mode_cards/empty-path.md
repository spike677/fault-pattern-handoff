# 空路径终止与输出义务

研究决定为 SPLIT_SUBTYPES。适用关系和候选均按固定路径取证。

**正确约定** 在选择调度、排空或提前返回前，核是否存在有效工作、在途任务或非空输出义务。

**错误动作** 零有效工作仍启动不支持零任务的调度器，或有输出义务却提前交回空执行器。

**失效机制** 路径的进展和结果物化义务各有证据。零工作仍推进与应产物却返回是相反的首错。

**七条边界** N02 的错误在接口结果物化。EX-36 有明确在途计算项，输出确实缺失时是 C2。

## 子型

- **零工作被调度**（FM-01）。Softsign 的 blockNum 为 0 仍进入 ElementwiseSch。
- **非空恒等输出未物化**（N02）。IndexFill 空 index 仍需给调用方非原位 out 的逻辑内容。

## 已核固定材料

- **FM-01** CASE-0312-M2，RELIABILITY_BOUNDARY。读到零任务参数后仍构造 ElementwiseSch，并调用 Init、Process。无有效工作仍进入调度器。调度器控制进展。旧案为挂起范围，无错误精度值证据。 [FM-01 原件](https://gitcode.com/cann/ops-nn/merge_requests/8479)
- **N02** CASE-0236-M1，STATIC_CONDITIONAL。旧 self 或 index 为空即交回无工作 executor 和成功，跳过正常物化路径。index 为空但 self 非空且 out 不合法别名时，输出任务未登记。调用方读取 out 时可能观察旧值。合法空 self 或允许原位共享的分支分列。 [N02 原件](https://gitcode.com/cann/ops-nn/merge_requests/5611)

## 近邻和边界

- **EX-36** 最后一批的局部空工作不等价于整个操作没有有效在途任务。旧消费者无替代 drain 且特定 contribution 实际未到达才计 C2。 [EX-36 原件](https://gitcode.com/cann/ops-transformer/merge_requests/5609)
- **EX-41** 无计算任务的执行者仍可能负有同步参与义务。影响屏障进展。没有具体缺少精度贡献的结果链。 [EX-41 原件](https://gitcode.com/cann/ops-nn/merge_requests/8667)

## 还需验证

Softsign 只作调度与挂起边界。IndexFill 补合法别名和零元素返回对照。历史 Embedding NaN 仍待核。

[固定证据表](../cluster_evidence.csv) · [近邻矩阵](../near_neighbor_matrix.csv) · [机理簇及锚点](../historical_mechanism_clusters.json)
