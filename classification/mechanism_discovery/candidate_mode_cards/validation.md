# 入口合法性校验

研究决定为 REVIEW_SCOPE。适用关系和候选均按固定路径取证。

**正确约定** 依同一版本、接口和目标后端的合法域判定可运行性，分别校验逻辑输入和物理后端限制。

**错误动作** 放行后端不支持的配置，或用物理存储形状误拒合法的逻辑视图。

**失效机制** 实际接受域偏离规定。误拒、漏拒及其错误校验关系须分别定位。

**七条边界** N21 在入口取形状判维，未发生 L1 式实际写入。FM-14 的非法配置放行区别于选错已有策略。

## 子型

- **硬件不支持请求漏拦截**（FM-14）。目标 DMA 配置的缺少条件需同版平台限制确认。
- **合法输入被误拒**（N21）。用 StorageShape 而非合法 ViewShape 作输入维数校验。

## 已核固定材料

- **FM-14** CASE-0201-M3，RELIABILITY_BOUNDARY。旧 Host 设 isDmaFlag 后缺相应平台拒绝分支。不能执行的 DMA 配置被接受。证据止于条件规划准入失败。原 Issue 平台是否 DAV_5102 与实际数值路径仍待核。 [FM-14 原件](https://gitcode.com/cann/ops-nn/merge_requests/4643)
- **N21** CASE-0114-M1，STATIC_CONDITIONAL。旧 ValidateInputShape 取 GetStorageShape 来比 expected_dims。物理存储维数与合法视图维数不同会误拒。仅记录入口拒绝。尚未定位原现场具体是哪一个梯度或门控张量。 [N21 原件](https://gitcode.com/cann/ops-nn/merge_requests/2031)

## 近邻和边界

- **EX-27** 已注册错误输出 dtype 后被编译拒绝，没有物理读写宽度违约证据。本案不是设备精度支持，界定在接口编译作用域。 [EX-27 原件](https://gitcode.com/cann/ops-nn/merge_requests/4627)

## 还需验证

Conv2DV2 的原报告平台与 DAV_5102 能力绑定待核。ThnnFusedLstmCellGrad 缺具体误拒输入。运行失败另作可靠性范围。

[固定证据表](../cluster_evidence.csv) · [近邻矩阵](../near_neighbor_matrix.csv) · [机理簇及锚点](../historical_mechanism_clusters.json)
