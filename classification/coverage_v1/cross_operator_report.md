# 同机理、不同算子

原独立首读的跨算子观察要求两个事件家族、两个规范化算子，且两个原读件轮次均支持叶级，决定性事实和具体动作保持稳定。有据的报告级计算项关系限于已确认的局部范围。叶级与因果角色分别报告。一个根动作的下游关系可以支持该关系的覆盖。

封存后审计将 G02 保留为缺证，并登记 H01 的 C1 下游。各批的冻结提示及工具配置不同，跨批汇总只表示已有观察。独立性由冻结、隔离与判卷记录支持，历史批次按流程演练使用 `exercise_only` 评分。

| 模式 | 有据家族/算子 | 原首读有据家族 | 原首读双轮命中家族/算子 | 双轮支持的跨算子配对 | 跨算子观察 | 阶段结论 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| P1 | 4/4 | 2 | 2/2 | 1/1 | 已观察 | VERIFIED |
| P2 | 3/3 | 1 | 1/1 | 0/0 | NOT_VERIFIED | NOT_VERIFIED |
| L1 | 3/3 | 1 | 1/1 | 0/0 | NOT_VERIFIED | NOT_VERIFIED |
| L2 | 4/4 | 2 | 2/2 | 1/1 | 已观察 | VERIFIED |
| C1 | 6/6 | 4 | 4/4 | 6/6 | 已观察 | VERIFIED |
| C2 | 10/10 | 5 | 4/4 | 6/10 | 已观察 | VERIFIED |
| C3 | 5/5 | 3 | 2/2 | 1/3 | 已观察 | VERIFIED |

## P1

原独立双轮命中案包括 scaled_dot_product_attention（G04）、Caffe2 CollectAndDistributeFpnRpnProposals（V402）。
已开封开发、回归或补证材料包括 EmbeddingBag、TVM oneDNN conv2d。
MPS mask ABI 与 Caffe2 proposal 属性已形成独立跨算子观察。独立合规对照及第二条成功近邻仍待补。

## P2

原独立双轮命中案包括 PyTorch cross_entropy（H01）。
已开封开发、回归或补证材料包括 EmbeddingBag、FlashAttention sparse MLA backward。
独立双轮正例仍只有加权 cross_entropy。Caffe2 上限绑定对照已区分；V404 附批登记为真实近邻，其决定性合同引证仍失分。

## L1

原独立双轮命中案包括 scaled_dot_product_attention（G07）。
已开封开发、回归或补证材料包括 Concat、llama.cpp Metal CPY。
补不同算子的定版非连续读/写与正规化合规对照；RMSNorm 需实际写入者。

## L2

原独立双轮命中案包括 ROCArray reinterpret（G03）、ONNX Runtime CPU fp16 grouped Conv（V403）。
已开封开发、回归或补证材料包括 ForeachLerpList、llama.cpp quantized KV state。
ROCArray reinterpret 与 ORT grouped Conv 已形成独立跨算子观察。补固定版合规单位边界、存储宽度缺证和第二条成功近邻。

## C1

原独立双轮命中案包括 llama.cpp Hexagon Flash Attention softmax（E05）、MaxPool（G08）、PyTorch cross_entropy（H01）、Caffe2 CollectAndDistributeFpnRpnProposals（V402）。
已开封开发、回归或补证材料包括 FlashAttention CuTe local attention、PyPTO row_max、llama.cpp Hexagon Flash Attention softmax。
补有效域外读取后被正确中性化的真实对照，核算其是否实际形成贡献。

## C2

原独立双轮命中案包括 TiledArray::Tensor::add_to（E01）、MLX Metal large-filter input VJP（E02）、ggml GROUP_NORM（G01）、MatrixSetDiag（G11）。
原独立首读有据但未双轮命中的材料包括 OpenVINO NPUW causal convolution（E03）。
已开封开发、回归或补证材料包括 MLX Metal large-filter input VJP、OpenVINO NPUW causal convolution、PadV3Grad edge、PyTorch scalar Tensor setitem、QLinearConvTranspose、ScatterNdAdd、TensorFlow ImageProjectiveTransformV3 backward、TiledArray::Tensor::add_to。
补有据的等价补偿、合法过滤、零贡献对照，单列首读过排与补证。

## C3

原独立双轮命中案包括 PyTorch QAT ConvBn2d（V401）、PyTorch FSDP.clip_grad_norm_（V405）。
原独立首读有据但未双轮命中的材料包括 FIA graph replay KV-length（G06）。
已开封开发、回归或补证材料包括 FIA graph replay KV-length、SGLang dense MLP、SGLang post-experts MoE reduction。
QAT 融合卷积和 FSDP 分布式范数已独立双轮命中。保留旧 DSPARK 首读失分，补同源身份缺证的真实材料。

[模式覆盖矩阵](mode_coverage_matrix.csv)
