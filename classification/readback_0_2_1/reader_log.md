# 读件记录 0.2.1

本次在新执行上下文中按任务划定的材料范围提取事实。所给原件曾用于前版，本次是从开发原件出发的入口复验。工作目录为 `D:\project\精度\fault-pattern-handoff`。

## 实际读写

- 通过 `functions.exec` 调用 PowerShell `exec_command`，以 `Get-Content -LiteralPath <路径> -Raw -Encoding UTF8` 读取 `classification/readback_0_2_1/PROMPT.md`。随后并行读取 `classification/readback_0_2_1/A.json` 和 `classification/catalog.json`，并用同一命令再次读取两个 JSON，在内存中解析。逐来源输出视图行号，并核对目录事实键。
- `A.json` 内的路径和网址只用作来源元数据。实际读取对象是 `A.json` 中嵌入的文本、提示文件和目录。
- 在 `functions.exec` 内构造和解析待写 JSON，核对路径、版本、事实键及锚点。从各来源视图按一基行号截取原始引文，对序列化后重新解析的 45 条锚点逐条核对引文。提取共有 4 个案例、4 个动作、15 条事实。
- 通过 PowerShell 的 `[System.IO.File]::WriteAllText` 和 `[System.IO.File]::AppendAllText`，将经核对的 JSON 分七段写入 `classification/readback_0_2_1/facts.json`，七次写入均返回成功。以 `[System.IO.File]::WriteAllText` 写入本记录 `classification/readback_0_2_1/reader_log.md`。两个输出使用 UTF-8。

## 取证判断与未决范围

- reader-1 将问题原句的按位掩码约定、旧完整批次循环的元素偏移及同版本的 uint8_t 存储声明对读。静态范围限于旧完整批次的非零偏移。尾部批次和 SelectBatch 函数体超出所给摘录。
- reader-2 将 issue 对 None 和 -1 的说明、同版本测试属性及 tiling 代码合读。证实第 4 槽中的 -1 进入负值归一化，按非空权重表推得末行行号。实际过滤行为需要另有下游证据。
- reader-3 用 issue 确定负 pad 恰裁整维的 edge 场景，结合相同版本的 CalPos 定义与 edge 调用、旧 IsCut 和差异中的区间规则复算了一维末端的非空区间。该例仅作静态算术见证。上层派发、实际调用输入和其他维数仍待相应材料支持。
- reader-4 用同版本槽位常量、测试属性和值读取语句建立错误来源关系。动作只覆盖 host 属性读取。最终过滤成员及输出需要另外的证据。
- 四项的声明均限于固定版本和所列源码路径的静态动作。A 提供的是问题描述、源码及差异摘录，缺少与单次执行绑定的构建和调用证据。
