# v0.3.1 计算项读件回归

七条模式定义、分类器及评分器使用 `21a6af4224b7c62681c241236c6850cac3e72109` 的文件字节。新读件以所评结果为目标，分别给出计算项身份、预期次数、实际次数和消费路径。同一个中间值已经含有某项时，沿到实际消费者判断它是否再次加入同一目标。非零参数如进入约定算式的加法，则沿到算式和写回核对这一加数。[修订提示](PROMPT.md) · [输出结构](RESPONSE.json)

## 固定回归

| 材料 | 第 1 轮 | 第 2 轮 | 决定性证据 |
| --- | --- | --- | --- |
| SGLang DSPARK NPU replay | C3，主动作 1 | C3，主动作 1 | 本次 verify 宽度为 8。准备端将 1000 更新为 1008，回退再次对同一请求的同一块加 8，把 1016 传给本地 replay |
| TransformerEngine 原件 | 缺证 | 缺证 | 固定旧侧支持有符号排序及前缀选择。报告者对 `-1` 的预期没有同版契约 |
| Quadric 首读原件 | 缺证 | 缺证 | 报告说明改变输出零点时结果不变。旧取值和消费链在首读包中缺失 |

三件开封回归每轮完整案均为 3/3，独立动作均为 1/1。[原件](regression/first/A.json) · [语义复核](regression/first/review.json) · [评分](regression/first/score.json)

### Quadric 补证

单独加入固定旧版的 schema、CPU 调用及 MLAS 消费者。旧调用把 `ZeroPoint` 实参固定为 `(T)0`。消费者将其用于限幅和输出加法，写回前没有来自模型的非零加数。两个会话均判 C2，保留一个主动作。首读和补证各有封存记录和判卷。[补证原件](regression/supplement/A.json) · [补证评分](regression/supplement/score.json)

## 新事件双轮盲读

| 固定原件 | 第 1 轮 | 第 2 轮 | 证据 |
| --- | --- | --- | --- |
| PyTorch 加权 `cross_entropy` | P2 主动作，C1 下游 | P2 主动作，C1 下游 | 同版接口要求忽略与 `ignore_index` 匹配的样本。旧平滑分支用未过滤的 `target` 查询类权重，使忽略项的权重 2 进入分母。分母得 5，按约定应为 3。两轮均只计一个独立主动作。[同版旧源码](https://github.com/pytorch/pytorch/blob/8b1e49635a488a4b260ef5d5657279585c5a291d/aten/src/ATen/native/LossNLL.cpp#L542-L555) |
| NumPy `add.at` | 合规 | 合规 | 固定测试的 `b[0]` 和 `b[2]` 均为 100，分别按自己的索引更新同一目标。Indexed loop 逐项推进源指针，结果为 202。原始目标值只计一次。[同版测试](https://github.com/numpy/numpy/blob/5fcd16dc72cbc4563deec5225e84f3b585e69afe/numpy/_core/tests/test_ufunc.py#L2210-L2213) |

P2 首读两轮各 **1/1**，C3 近邻误报均为 **0**。按封存答案，两轮各命中两项预定判决，独立动作各 **1/1**，完整案各 **1/2**。封存答案记录了 P2 主动作，漏列两轮均指出的有据 C1 下游。按所评分母关系补记下游、复算得到两轮各 **2/2** 完整案，独立动作计数保持一个。两个分数分别保存。[封存成绩](holdout/first/score.json) · [逐案判卷](holdout/first/review.json) · [事后口径及复算](holdout/first/answer-scope-audit/score.json)

两案与 282 条既有开发暴露键核对无交叠。上游选定修订的实际第一父与相关旧 hunk 逐行一致。参考答案由另一会话审核后存放在 checkout 之外。首读两轮同载荷、不同会话，日志均无工具调用，锁定后才揭盲。仓库按 `exercise` 口径评分，无外部人工见证。语义结论限于固定源码的受评路径。[来源与版本](holdout/sources.json) · [编号原件](holdout/first/A.json) · [第 1 轮事实](holdout/first/round-1/facts.json) · [第 2 轮事实](holdout/first/round-2/facts.json) · [揭盲记录](holdout/reveal.json)

## 上轮封存成绩

上一轮新事件首读完整案两轮各 9/11，独立动作各 7/8。上一轮 Quadric 补证的完整案分别为 1/1 和 0/1。TransformerEngine 的事后口径另存，两轮各 10/11。保存的评分、封存、锁定记录沿用上轮原始字节，另附 SHA-256。[原首读](prior/first/score.json) · [原补证](prior/supplement/score.json) · [原事后复算](prior/first/answer-scope-audit/score.json) · [校验清单](prior/SHA256SUMS.txt)

## 独立复算

从仓库根目录运行以下命令。Windows 检出使用 `core.autocrlf=false`，以便保持封存文件字节。复算只使用 Python 标准库。

```powershell
python -B -X utf8 classification/validation_0_3_1/readback/replay.py classification/validation_0_3_1/readback/regression
python -B -X utf8 classification/validation_0_3_1/readback/replay.py classification/validation_0_3_1/readback/holdout
python -B -X utf8 -m unittest discover -s classification -p 'test_*.py'
```

复算从实际会话记录恢复选择的行号，按冻结原件补齐引文，再执行固定裁决和官方评分，并与已保存结果比较。运行新的成对读件时，先准备冻结批次及其封存记录，再对同一批次下还没有输出的新阶段运行 `readback.py <stage> --pair`。

复算 PyTorch 下游关系的事后口径时，使用原锁定答卷并给评分器传入单独的答案修订。

```powershell
$batch = 'classification/validation_0_3_1/readback/holdout'
$stage = "$batch/first"
$audit = "$stage/answer-scope-audit"
python -B -X utf8 classification/evaluate.py score "$batch/freeze.json" "$stage/A.json" "$stage/seal.json" "$stage/round-1/run.json" "$stage/round-2/run.json" "$stage/lock.json" "$stage/B.json" "$audit/review.json" regraded.json --revision "$audit/revision.json"
```
