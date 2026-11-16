# v0.4.2 原件读件修复与数值候选审核

本地工作从数值候选审计提交 `25808757205288bfa19f4c7259c99accf4243154` 开始，父提交为 `3067d55`。GitHub API 核对的试点分支为 `7234428d7915e2c094ff70d178f933d8fed7e8d6`。正式分类目录仍为 `MECH-v0.3`，新增正式模式数为 0。[公开试点提交](https://github.com/spike677/fault-pattern-handoff/commit/7234428d7915e2c094ff70d178f933d8fed7e8d6)

## E 原件读件

读件提示要求动作本身携带对应证据等级。由合同、固定旧行为和消费链得出的断言，填写 `derived` 及对应引证。作者确认限其陈述范围，运行验证需要构建、调用和路径匹配。响应结构新增 `supporting_operations`，保留正常转宽、归约和写回的原件引证，并关联已有动作。读回程序沿用正式判定器验证来源。无据根动作、无据下游关系和无效支持锚点会留痕，原始动作记录完整保留。七模式判定与候选判据沿用冻结代码。[读件提示](proposals/numeric_validation_v042/PROMPT.md) · [输出结构与校验](proposals/numeric_validation_v042/reader.py) · [回归](test_numeric_reader_v042.py)

| 原件测试 | 第一轮 | 第二轮 | 核查范围 |
| --- | ---: | ---: | --- |
| 历史封存 N501–N503 | 0/3 | 0/3 | 原始读件与原判卷复算。 |
| 同三案新协议重读 | 3/3 | 3/3 | A 包和范围逐字节相同。 |
| E06/G05 用旧摘录重读 | 1/2 | 1/2 | G05 两轮通过，E06 两轮候选证据不足。 |
| E06/G05 同版本补证 | 2/2 | 1/2 | E06 两轮通过。G05 第二轮缺少绑定动作文件的合同引证。 |
| 补证与跨文件引证说明 | INVALID | 未评分 | 第一轮把 G05 的尺寸作为元素来计算，并提交空动作数组。两个原始答卷均保留。 |
| 补证、明确输入和完整动作记录 | 2/2 | 2/2 | E06 和 G05 均为有引证的 `derived`，每案一个独立动作，校验无告警。 |

新三案的六份主动作都填写 `derived`，两轮各报告三个独立根动作，逐案人工核对首错一致。Qdrant 的正常转宽、JAX 的归一化消费和 FlashInfer 的后续 FP32 归约各自保留原件引证。旧答卷分别多列了 3 条、1 条正常操作。新答卷中每案各有一条错误动作，两轮的支持操作条数分别为 5、4。

| 家族 | 复核到的首错 | 新读件裁决 |
| --- | --- | --- |
| N501 Qdrant Dot | 两轮之间保存同一个 FP16 lane。给定输入的第二次更新把 2049 舍回 2048，随后正常转宽。 | 两轮 NUM-01 |
| N502 JAX standardize | FP32 原始矩差使方差 1 变成 0，随后用该值标准化。 | 两轮 NUM-02 |
| N503 FlashInfer RMSNorm | 可表示的 300 先在 half 中平方溢出，再转换为 FP32 参与线程求和。 | 两轮已证目录外 |

本轮使用新建临时上下文，模型及推理档位沿用旧执行记录。每轮仅输入提示、目录、范围和公开原件。禁用文件、网络等工具，日志解析核验每轮独立 ID 和零工具事件。每批先固定输入与参考哈希，再锁定两轮完整答卷，然后评分。材料已开封，登记为 `exercise_revised_prompt`。本轮无外部见证。评分以机理、角色、独立计数和整案动作为结构指标，首错文本按原件逐案核对。旧封存分（受控归档） · 原三案复测（受控归档） · 旧摘录补测（受控归档）

旧摘录 E06 第一轮选择作者确认作用域，计算项保持、宽状态对照和失真值消费未被采纳。第二轮在静态作用域填入作者确认的适用合同，触发 `missing_scoped_confirmation`。为 E06 补入同提交的通用累加精度 API、Flash Attention 的设置与派发、半精度标量写回、归一化和输出代码。为 G05 补入同提交的形状读取、类型注册和派发。补证后 G05 第二轮将适用合同仅与上游派发相连，候选分级缺少 `layer_norm.cuh` 内的旧行为锚点。增加通用跨文件引证说明及正反回归，要求每条决定性静态事实同时绑定它的适用合同和动作文件中的旧代码。补齐的公开原件来源（受控归档） · 补证评分（受控归档） · [跨文件引证说明](proposals/numeric_validation_v042/SCOPE_BINDING.md)

跨文件复读的第一轮把 `[1,2,4]` 解读为一行元素，现有裁决拒绝空动作数组，两轮因此未锁定评分。后续材料分别给出轴尺寸和 FP32 行元素。启用跨文件说明时，响应数组至少提供一项，缺证要明确记录 `unknown`。在保留原参考的条件下，该批两轮各严格 2/2。两轮稳定识别 E06 的逐次窄状态与 G05 的方差消减，均保留了根动作的正常消费者引证。失效答卷（受控归档） · 明确输入的冻结材料（受控归档） · 最终补证评分（受控归档）

## NUM-01 与 NUM-02 准入前审核

- **NUM-01。** E06 CPU Flash Attention 和 N501 Qdrant AArch64 Dot 为两个独立家族。查到 N501 同提交的 SIMD 长度门槛为 16，评估长度 64 满足该条件。给定 AArch64、NEON、FP16、非 Windows 和对应 C 编译分支，首错是跨两次更新保存窄状态。公开报告的 Euclid 运行、Dot 的给定向量和编译条件各有自己的适用范围。[Qdrant 固定门槛](https://github.com/qdrant/qdrant/blob/74f3e85b9473c62560006c043e13737ce6b48412/lib/segment/src/spaces/simple.rs#L17-L22) · [原报告](https://github.com/qdrant/qdrant/issues/10350)
- **NUM-02。** G05 ONNX Runtime 和 N502 JAX 为两个独立家族。G05 在固定旧代码中正常注册为普通、非 Simplified 模板。对 `[1,2,4]` 的 FP32 输入，取 `ld=4`、`next_size=128`。向量地址条件成立时走 `SkipLayerNormKernelSmall<float,32,4,false>`，否则走 `<float,128,1,false>`。两支进入普通小核，原始矩差由 `rsqrtf` 消费并进入向量写回。宽 768 的规则不同，向量化地址条件满足时为 ILP=8，否则会走一般核。旧启动文件在材料固定提交与修复 PR 的基础提交具有相同 Git blob。作者报告了 FP32 宽 4 和 768 的旧内核现象。作者实测的旧启动模板和调用 ID 仍待绑定。[G05 固定派发](https://github.com/microsoft/onnxruntime/blob/a926b837fb8a39b0e4840fcb997ff1336cdf5db1/onnxruntime/contrib_ops/cuda/bert/skip_layer_norm_impl.cu#L173-L242) · [实际消费代码](https://github.com/microsoft/onnxruntime/blob/a926b837fb8a39b0e4840fcb997ff1336cdf5db1/onnxruntime/contrib_ops/cuda/bert/layer_norm.cuh#L135-L180) · [作者报告及修复对照](https://github.com/microsoft/onnxruntime/pull/33357)
- **近邻与合规控制。** V406 和 FlashInfer 分别保留一次平方溢出的目录外结果。合成的末端 FP16 输出合同允许把宽状态 2049 最后舍入为 2048。多一次贡献时，先宽累加再按合同输出为 2050，循环中反复窄化仍给 2048。对条件良好的行 `[1,2,4]`，FP32 归一化输出和中心参考的最大绝对误差为 `1.60e-7`，在 `1e-4` 允许范围内。高偏置近常量行 `[8191,8193]` 的原始矩差得到 0，中心参考为 1，最大输出差为 315.23。两个合规控制为确定性数值复算。[数值控制](proposals/numeric_validation_v042/controls.py)

两个数值候选保留在开发验证。新读件覆盖的第二个家族已开封，合规对照为合成，正式准入仍待评审。CUDA 运行与派发复核在当前环境记为 `NOT_TESTED`。

## CTRL-01 定向补证

取回修复提交 `10815a6cc04aa83cba0206a79870731cba958b01` 的确切父版本 `43cdc3214a797b1c371fb1b83cfa784c181d2b88`。父版分别初始化 `xSigmoidBuf_` 和 `xBiasBuf_`，无 bias 的 SoftMax 先写 S，旧 helper 却从 D 读并回写 D。排序的 `SortInGroup` 和 `TopKCompute` 都消费 D。静态首错连到排序消费者。运行中 D 的具体内容和设备输出仍待绑定。[父版本完整源码](https://gitcode.com/cann/ops-transformer/blob/43cdc3214a797b1c371fb1b83cfa784c181d2b88/moe/moe_gating_top_k/op_kernel/arch35/moe_gating_top_k_regbase.h) · [修复提交](https://gitcode.com/cann/ops-transformer/commit/10815a6cc04aa83cba0206a79870731cba958b01)

生成两份可独立应用的对照补丁。源对照只切换 D 到 S 的选源，保留 helper 内原屏障。屏障对照只把屏障移到调用点，保留从 D 读。两份对照均通过 `git apply --check`，按任一顺序组合都可按字节复原正式修复源码。固定不同的 S、D 初值进行静态 Top1 对照，父版和仅移动屏障给索引 0，选源对照和组合给索引 1。设备同步、编译调度及 NPU 实测 `NOT_TESTED`，CTRL-01 仍是候选。对照生成与复算（受控归档） · 选源补丁（受控归档） · 屏障补丁（受控归档）

## 验收与复算

A–D 沿用既有结论。七条稳定定义及 269 个历史冻结文件校验通过。固定数值回归 E06/G05/V406 为 3/3。104 项单测通过，新增回归覆盖证据等级、跨文件引证、缺证动作、FlashInfer 与 V406、正常消费、真实下游、两个独立根动作和两组合法边界。七类扩大取样继续沿用 v0.4.1 的矩阵，C2 达到取样目标，其余六类仍有对照缺口。F 为 `BLOCKED`，待正式目录冻结和独立事件、参考答案保管、访问隔离或外部见证就绪。[既有覆盖矩阵](coverage_v1/mode_coverage_matrix.csv)

从检出根目录运行以下命令。带有原始日志的本地演练目录与源码检出并列。本次实际使用 Codex 自带的 Python 3.12.14。Windows 检出离线 Git 包时可用 `git -c core.autocrlf=false clone` 保留校验使用的文件字节。

```powershell
python -B -X utf8 -m unittest discover -s classification -p 'test_*.py'
python -B -X utf8 classification/validation_0_4_1/verify.py
python -B -X utf8 classification/proposals/numeric_validation/verify_regression.py
python -B -X utf8 classification/proposals/numeric_validation/holdout.py verify classification/proposals/numeric_validation/holdout
python -B -X utf8 classification/proposals/numeric_validation_v042/exercise.py verify ../exercise-revised-original
python -B -X utf8 classification/proposals/numeric_validation_v042/exercise.py verify ../exercise-revised-fixed
python -B -X utf8 classification/proposals/numeric_validation_v042/exercise.py verify ../exercise-supplemented-fixed
python -B -X utf8 classification/proposals/numeric_validation_v042/exercise.py verify ../exercise-scope-explicit
```
