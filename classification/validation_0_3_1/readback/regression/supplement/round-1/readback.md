## G10

受评模型为单批单组 CPU int8，x_zero_point 和 w_zero_point 均为 0，无 B 输入。静态判定绑定提交 fac7b31168cc88790d7c8a2be07692ade3a354bf。y_zero_point 为 0 时，固定实参与约定值一致。为 25 或 -30 时，每个输出元素应计入一次对应标量，旧路径实际计入零次。Issue 报告 SDK 26.08、ONNX Runtime 1.20.0 和 CPUExecutionProvider。三个受评取值的输出哈希相同，逐元素对照也显示与零点全为 0 的输出无差异。材料缺少将 Issue 二进制绑定到该提交、将具体调用绑定到所示 SSE2 实现的运行证据。零点为 0 时与参考结果相差 1 的单个元素，原因仍待核。
