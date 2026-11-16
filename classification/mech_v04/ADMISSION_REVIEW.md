# NUM-01 与 NUM-02 准入评审

评审基线为 `e491687a392160f977c7414c3f2bd9bfb10352a6`。依照 v0.4.1 的卡片审查与 v0.4.2 的开发验收，逐条核对两个独立正例家族、适用约定、首错和消费者、最近边界、合规对照及双轮稳定性。裁决适用于下列已证明的机理范围。实际设备调用仍按各自证据等级记录。[原评审](../proposals/v041_review/CANDIDATE_REVIEW_REPORT.md) · [v0.4.2 读件](../V042_IMPLEMENTATION_REPORT.md)

| 审核项 | NUM-01 | NUM-02 |
| --- | --- | --- |
| 正式目录裁决 | **准入** | **准入** |
| 两个真实家族 | llama.cpp CPU Flash Attention、Qdrant AArch64 Dot | ONNX Runtime CUDA SkipLayerNormalization、JAX CPU standardize |
| 首错必须定位 | 同一运行累加状态在相邻更新之间保存到过窄的类型，失真由后续更新或输出实际消费 | 以原始二阶矩减均值平方计算方差，有限精度消去仍能在同工作精度下保留的小方差，失真进入归一化 |
| 最近排除 | 独立逐项平方先溢出、合法的末端输出转换、合同允许的逐步舍入、不同的逻辑计算项 | 运行累加状态过窄、通用平方溢出、不等价公式、符合误差合同的近似 |
| 范围 | E06 的显式 F32 约定及 one-chunk 路径，Qdrant 的同算子分路径一致性及指定 NEON FP16 分支 | G05 普通小核的已核派发和消费者，JAX 0.6.2 的默认 FP32 方差及实际 CPU 调用 |

## NUM-01 运行累加状态过窄

- **E06。** 固定旧 CPU 路径接受 `GGML_PREC_F32`。显式设置经过对应的算子参数槽，one-chunk 路径对 F16 V 的加权和仍反复写入 VKQ16。标量辅助函数执行每次更新后的窄转换，下一次读取同一状态。退出循环才转宽，F32 归一化和写回消费已失真的值。该链条在明确输入的两次读件中均成立。作者另对原缺陷和修复效果作了陈述。[精度合同](https://github.com/ggml-org/llama.cpp/blob/af6b5243d6871923dfecbe06814bd566d9dc383b/ggml/include/ggml.h#L1449-L1461) · [旧半精度写回](https://github.com/ggml-org/llama.cpp/blob/af6b5243d6871923dfecbe06814bd566d9dc383b/ggml/src/ggml-cpu/vec.h#L573-L582) · [旧消费者](https://github.com/ggml-org/llama.cpp/blob/af6b5243d6871923dfecbe06814bd566d9dc383b/ggml/src/ggml-cpu/ops.cpp#L9014-L9056) · [原修复](https://github.com/ggml-org/llama.cpp/pull/29810)
- **N501。** 补核正式 Qdrant 1.19.0 构建源码，AArch64 NEON 编译带 FP16 扩展。Dot 路径对 32 个 FP16 lane 逐次更新，循环结束才转为 FP32 汇总。同一固定发布版的报告还实测了长度 1536、元素 1400 对全 1 向量的 Dot，结果为 `null`。单项 1400 可表示，32 个 lane 各处理 48 项，按近偶舍入的位宽模型在同一 lane 第 47 次才达到无穷，宽状态全量结果为 2,150,400。第 47 次来自模型，本机没有执行 NEON。该范围也独立于报告中的 Euclid 单项平方溢出。[构建](https://github.com/qdrant/qdrant/blob/74f3e85b9473c62560006c043e13737ce6b48412/lib/segment/build.rs#L16-L22) · [状态更新与归约](https://github.com/qdrant/qdrant/blob/74f3e85b9473c62560006c043e13737ce6b48412/lib/segment/src/spaces/metric_f16/cpp/neon.c#L5-L43) · [运行报告](https://github.com/qdrant/qdrant/issues/10350) · [分路径精度一致性](https://github.com/qdrant/qdrant/pull/9811)
- **合规与近邻。** PyTorch 2.8 的 CUDA sum 在 FP16 输出的常规单次归约分支使用 FP32 累加类型，最终按输出 dtype 写回，作为可定位的真实实现对照。实际 NumPy 对照的同序数据 `[2048,1,1]` 用 FP32 求和后合法转回 FP16 得 2050，逐次存 FP16 得 2048。V406 和 N503 的首错均可在单项平方处定位，仍属目录外。[PyTorch 接口](https://docs.pytorch.org/docs/2.8/generated/torch.sum.html) · [CUDA 类型派发](https://github.com/pytorch/pytorch/blob/v2.8.0/aten/src/ATen/native/cuda/ReduceSumProdKernel.cu#L164-L195) · [CUDA 写回](https://github.com/pytorch/pytorch/blob/v2.8.0/aten/src/ATen/native/cuda/Reduce.cuh#L429-L466)

## NUM-02 原始矩差求方差的有限精度消减

- **G05。** CUDA host 将 FP32 普通算子绑定至 `Simplified=false`。形状 `[1,2,4]` 的最后一维为 4，`NextSize=128`。在有效地址满足 16 字节对齐时走 `<float,32,4,false>`，仅满足合法标量对齐时走 `<float,128,1,false>`。两支共享 `LayerNormSmall`，原始矩差进入 `rsqrtf` 并形成向量输出。旧发布材料的宽度 4 与 768 现象、修复后的 H100 测试为作者证据。修复测试针对 FP32 输出以中心 FP64 为参考，绝对和相对误差界均为 `1e-4`。旧 CUDA 原复现的地址、本次实际模板及调用轨迹仍为 `NOT_TESTED`。准入限于定版静态链和各自明示的作者报告范围。[旧 host 派发](https://github.com/microsoft/onnxruntime/blob/a926b837fb8a39b0e4840fcb997ff1336cdf5db1/onnxruntime/contrib_ops/cuda/bert/skip_layer_norm_impl.cu#L173-L242) · [方差消费者](https://github.com/microsoft/onnxruntime/blob/a926b837fb8a39b0e4840fcb997ff1336cdf5db1/onnxruntime/contrib_ops/cuda/bert/layer_norm.cuh#L135-L180) · [官方误差对照](https://github.com/microsoft/onnxruntime/blob/f7b31b70308167e2f277b419f1931aed837c83ad/onnxruntime/test/contrib_ops/skiplayernorm_op_test.cc#L81-L125) · [作者验证](https://github.com/microsoft/onnxruntime/pull/33357)
- **版本交叉核对。** G05 原件版本 `a926b837` 与修复 PR 的基线 `07daf405` 的启动文件和方差消费者均字节相同。启动文件 Git blob 为 `7f5169639ff8dd61aff7c841d64e1fe17865e90b`，消费者为 `0ed2c125405e3138654bd3f52fafdba7288b36e3`。两条宽度 4 派发共有同一方差机制，待核实际指针对齐用于确定模板实例。[修复基线启动文件](https://github.com/microsoft/onnxruntime/blob/07daf405c788c300aa9fd2988104b29bcbdede23/onnxruntime/contrib_ops/cuda/bert/skip_layer_norm_impl.cu) · [修复基线消费者](https://github.com/microsoft/onnxruntime/blob/07daf405c788c300aa9fd2988104b29bcbdede23/onnxruntime/contrib_ops/cuda/bert/layer_norm.cuh)
- **N502。** 本机安装官方 JAX 及 jaxlib 0.6.2 CPU wheel，校验 `functions.py` 的 Git blob 与 N502 原件相同。用原报告种子和形状重跑，默认路径 eager 与外层 JIT 最大差为 `0.00302356`。保持 FP32、输入和 epsilon，用中心二阶矩将差降为 `2.37226e-5`。独立的高偏置测试行中，默认输出约为 `±316.228`，中心化输出约为 `±0.999995`，与高精度参考的误差约 `6.83e-9`。编译产物保留用于检查方差差式和实际消费者。[问题原件](https://github.com/jax-ml/jax/issues/37281) · [固定旧源码](https://github.com/jax-ml/jax/blob/1ad05bb26105f23ee7728b36cca12901fe70e187/jax/_src/nn/functions.py#L635-L679) · [本机运行证据](numeric-runtime-results.json)
- **合规与近邻。** 同一版本 JAX CPU 的条件良好输入 `[1,2,4]` 偏离中心高精度参考约 `1.98e-7`，落在本次对照的 `1e-4` 界内。该界用于对照，JAX 接口未在这里声明所有平台统一误差界。是否采用原始矩差、实际误差及其消费者各自举证。E06 仍只判 NUM-01，FP16 单次平方溢出仍保留目录外。[本机运行证据](numeric-runtime-results.json)

## 交付范围

正式版仅增加上述两张卡。历史七张卡保有各自 ID 和内容；v0.3 的目录、判定入口和封存字节用于历史复算。原始三案与补证双轮均用于开发验收。F 使用单独冻结的 `MECH-v0.4` 版本、独立事件和封存答案。准入评审的样本和上述补证均计入开发暴露。

正式入口复算原三案和补证两案的锁定事实，两轮各 5/5。每案的机理、首错角色和独立计数均符合已核验参考。旧固定 V406 继续给出已证目录外。此次新增 10 项回归，全套 114 项通过，269 个历史冻结文件及相应评分复算通过。F 使用冻结入口的合成端到端测试在两轮均严格 1/1，结果为流程演练。[F 准备](F_PREPARATION.md)

CPU 证据可用固定的 JAX 0.6.2、jaxlib 0.6.2、NumPy 2.2.6、SciPy 1.15.3、ml-dtypes 0.5.1 和 opt-einsum 3.4.0 运行复算脚本。设 `JAX_PLATFORMS=cpu`，关闭 X64，按需用 `JAX_REVIEW_PACKAGES` 指向独立安装目录或使用已安装的环境。Windows 还可用 `JAX_REVIEW_DLL_PATH` 指向可用的 Microsoft C++ 运行库。给脚本指定 `--ir-dir` 可输出当前构建的 IR。[运行脚本](verify_numeric_runtime.py) · [StableHLO](jax-standardize-stablehlo.mlir) · [编译后 CPU HLO](jax-standardize-cpu-hlo.txt)
