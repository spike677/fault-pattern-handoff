# MIGraphX NUM-02：公开证据边界

审查状态 **CLOSED**；本案保持 `numerical_evaluation` 上位，NUM-02 叶级
**NOT_VERIFIED**，GPU 实测 **NOT_TESTED**。审查关闭表示完成了限定范围的追踪
和缺口清点，实际故障 GPU 工作精度尚未闭合。

固定旧版 `78746563c499a1d99fdd4ca6fd09ad94edb9671f` 的源码追踪覆盖 parser、
variance rewrite、GPU passes、lowering、simple/fused reduction JIT、
lane/wave/block 调度、typed views 和归一化消费者。

| 证据环节 | 已知结论与边界 |
| --- | --- |
| 公式与合同 | 旧 rewrite 引入原始矩差；图级 variance 进入后续归一化 |
| 类型传播 | 浮点 mean 在读侧缩放；accumulator 从 read 返回类型推导，不能默认全部 FP32 |
| 编译选择 | 固定源码可确定选择规则；variance rewrite 不受 fast_math 门控，但故障实际配置未绑定 |
| 消费者 | parser 的 rsqrt/mul 与测试构造的 sqrt/div 分开记录；正常消费者不另计错误动作 |
| 同精度对照 | CPU 控制显示原始矩丢失小正方差、产生负值及不同求和顺序的影响；clamp 不能恢复已丢失方差 |
| 实际 GPU | 最终选路 IR、HIP/args.hpp、gfx、flags、code object 和调用对应关系仍缺 |

本地 **63/63 检查通过**，涉及 14 个固定源文件、23 个源码锚点和 5 个算术对照。
这些数字不是 GPU 测试数，也不是分类准确率。上位判断结合旧源码与作者明确
的默认 GPU 路径故障报告，不能只用数学公式概括；缺失具体实例类型同样不构成
排除 NUM-02 的证据。

最小补证要求为同次故障的输入、shape/stride、设备和编译参数，最终 IR 与生成
内核类型，以及绑定该次调用的原始矩、稳定算法、参考方差和归一化输出。
取得这些材料前，本案不进入 NUM-02 叶级验证分母。

[公开控制代码](../../reliability_v044/public_controls.py) 提供与本地控制一致的
CPU 算术复算。完整源码快照、评审原件及逐项锚点继续本地保管，正式九条目录
与历史成绩保持原样。
