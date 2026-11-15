# 开发读件复验记录

## 读写与操作

- 工作目录为 `D:/project/精度/fault-pattern-handoff`。在单独执行上下文中，通过 `functions.exec` 调用 PowerShell 的 `Get-Content -LiteralPath -Encoding utf8 -Raw`，读取 `classification/readback_0_2_1/retry/PROMPT.md`、`classification/readback_0_2_1/A.json` 和 `classification/catalog.json`。
- 三份材料并行初读后，因组合回显被截断，单独重新读取目录中 P1、P2 与判定规则；再次读取 `A.json`，按每条来源视图打印其自 1 起的行号。目录用来定位语义角色、事实键及证据边界。事实依据为案卷原文与下列计算。
- 在同一工作目录使用 PowerShell 由原件切分各引句，按行范围生成原样引用，并以 UTF-8 写入 `classification/readback_0_2_1/retry/facts.json` 和本记录 `classification/readback_0_2_1/retry/reader_log.md`。回读交付的 JSON，核对案件集合、字段、事实键、角色与范围，以及引文与原件逐字符一致。
- 本次仅访问上述三份输入与两个输出。未读取旧提取结果、评分、仓库历史或所列来源的原始路径和网页。该隔离是开发读件操作范围。

## 案件判断

- **reader-1**。报告第 1 行说明 Select 掩码按位使用以及需要除以 8；同版本 `mask-storage` 第 3 行给出 `uint8_t` 存储。`diff` 第 11 至 17 行把数据下标、掩码下标和偏移步进放在同一旧循环。非零且字节对齐的批次起点能区分元素下标与掩码字节下标。证据限于可见旧循环，修订后 `SelectBatch` 的方法体及运行路径未核验。
- **reader-2**。`issue` 第 1 和 4 行给出 None 与 -1 约定。`slots` 第 2 行和 `action` 第 2 至 3 行给出正确的第 4 槽及负值归一化，因而在有表行时可静态算出末行索引。同版本 `host-fixture` 第 2 至 3 行另示布尔 `include_last_offset` 与独立的整数 `padding_idx=-1`，作为约定旁证。可见范围终止于宿主赋值，实际过滤或聚合结果未确定。
- **reader-3**。`old-edge` 第 2 行调用 `CalPos`；同版本另一文件的 `shared-coordinate` 第 10 至 14 行显示一维坐标为 `outIndex=yIdx` 与 `inIndex=outIndex+leftPads`。一维前向长度 2、左裁剪 2、右边界复制 3 时，反向输入长度为 3，三项的前向坐标按 edge 规则均钳到末项。对末项反向输出 1，中心为 -1，`diff` 第 20 至 36 行将区间算为 [0, 2]，第 64 至 78 行给出区间逐项累加和写回。旧版 `IsCut` 在该条件成立并跳过累加。这个代入复核区间成员及源码行为，前端校验、调度可达性与实际梯度值均未验证。
- **reader-4**。`slots` 第 1 至 2 行区分第 3、4 槽，`action` 第 1 至 7 行可见同一布尔来源赋给两个宿主字段。`host-fixture` 第 4 至 5 行给出 `include_last_offset=false` 和 `padding_idx=-1` 的独立设置，可复算前者经赋值成为 0 时与后者的区别。该版本的可证动作是读取来源错误，实际过滤或聚合结果未确定。

四个动作均限于 `static`。跨文件的 fixture 和坐标辅助代码记录在此，JSON 中的静态动作锚定同版本同路径代码或 diff，并保留适用的报告引句。本次未运行算子，未填写 build 和 call_id。案卷未提供可独立举证的第二项错误动作。

