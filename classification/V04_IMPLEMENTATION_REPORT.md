# 算子精度故障分类 v0.4 试点发布

本页发布审计提交 `dfca7e1dcc1cc11a060b302244dc388841a6fc94` 中的读件程序、测试及结果摘要。工作基线为 `712d98947c3d86edc453a754e4e6ac0f0d5b2511`。正式机理目录使用 `MECH-v0.3`，裁决、事实和评分使用 0.3.1。新读件提示以 `reader_v04` 单独冻结，提示 SHA-256 为 `7ece4c7048817852dca61cc835f08fbab6f0e99ef5751a7b8285c68cc526298e`。[目录](catalog.json) · [修订提示](validation_0_3_1/reader_v04/PROMPT.md) · [执行配置](validation_0_3_1/method_acceptance_v2/execution.json)

| 工作包 | 状态 | 交付 |
| --- | --- | --- |
| A1 七家族方法验收 | `PASS` | 基线严格 4/7、4/7。修订严格 7/7、7/7，各轮独立动作 4/4。补证另计，严格 1/2、2/2，独立动作各 3/3 |
| A2 历史对照 | `COMPLETE` | 登记 53 个历史身份及 45 个 V16 EX。47 条可恢复定义、6 条 `UNRESOLVED`，原 2,385 项初筛沿原归档 |
| A3 覆盖与泛化 | `NOT_VERIFIED` | P1、L2、C1、C2、C3 达到本轮模式验证条件。P2、L1 的独立跨算子验证待完成 |
| A4 新事件原件读件 | 已执行并判卷 | 主批五家族两轮严格各 5/5。附批一案两轮严格各 0/1，审计修订标签后两轮标签各 1/1，决定性证据仍失分 |
| A5 目录扩展 | 候选审查 | 归档七张候选卡与版本迁移设计。阶段三仍在验证，正式准入待定 |

## A1 已开封回归

修订读件要求显式绑定适用约定、实际输出消费者和下游动作。两轮保留了 SGLang 的一个 C3、PyTorch 的一个 P2 主动作和一个 C1 下游、ConvTranspose 的两个独立动作。TransformerEngine、Quadric 和 ScatterNdAdd 的首读保持各自证据边界。Quadric 补证命中 C2，两轮在 ScatterNdAdd 补证中都保留两处 C2 和两个独立根。第一轮把根和下游分开，和封存参考的合写粒度不同。补证和原首读分开评分。[方法验收](validation_0_3_1/method_acceptance_v2/METHOD_REPORT.md)

## A2 和 A3

历史对照逐项记录检索谓词、决定性条件、近邻排除、代表 EX 和来源。13 个历史模式部分重叠，2 个历史下位，1 个历史上位，27 个有不同机制，10 个待核，整条等价为 0。定义未恢复的 FM-18、FM-22、FM-25、FM-26、FM-27 和 N27 保留原身份。[历史对照](history_mapping/HISTORY_MAPPING_REPORT.md) · [45 个 EX](history_mapping/v16_ex45_mapping.csv)

覆盖报告登记 26 个原独立首读家族，按案例、家族、算子和模式分别计数，封存分、审计分、开封回归和补证各有原来源。P2 和 L1 各只有一个双轮独立命中的算子。附批 V404 进入 P2 近邻索引，证据失分计入该近邻分母。[覆盖报告](coverage_v1/COVERAGE_REPORT.md) · [七模式覆盖矩阵](coverage_v1/mode_coverage_matrix.csv)

## A4 原件到事实到判决

主批 QAT ConvBn2d 和 FSDP clip_grad_norm_ 两个算子均在首读识别 C3。FSDP 的 FP16 中间溢出是同算子近邻，两轮均判已证目录外。Caffe2 新案保留 P1 至 C1 的因果边。ORT 分组卷积的读、写各命中一条 L2，同一事件家族在泛化分母只计一次。两轮各正确识别七条动作及角色，六个独立根，零误计。

附批 ReduceSumSquare 保留封存与事后修订的两套结果。两轮都定位空轴快速分支把仍须平方的输出一律拷贝为原值。按冻结 P2 的必要条件复核，实际特殊状态已被识别，审计将参考修订为已证目录外。两轮提交都缺支撑空轴语义的依赖合同锚点。现有协议对源与受评代码做提交号等值校验，诊断已复现无法接纳经标签绑定的旧依赖约定。这个问题在目录扩展方案登记。

全部新事件使用项目暴露键去重，B 在读件检出目录之外保管。读件上下文没有文件、网络或其他工具事件，两轮锁定后按原承诺揭封。成绩登记为流程演练，无外部保全见证。附批初次转换因源类型中断，原记录留存。修正类型后重新复核、封存和双轮执行。[公开案例和双渠道成绩](validation_0_3_1/coverage_holdout/COVERAGE_HOLDOUT_REPORT.md)

## A5 版本迁移和公开验证

七张候选卡记录独立机制、真实依据、近邻、触发、诊断、可模拟动作和准入尚缺的证据。版本方案把叶级定义、父类、必要事实及检查器注册分开，并保留冻结旧版的评分入口。[目录扩展方案](proposals/CATALOG_EXTENSION_PLAN.md) · [候选卡](proposals/candidate_registry.json)

在检出根目录可用标准库运行公开测试集。

```powershell
python -B -X utf8 -m unittest discover -s classification -p 'test_*.py'
```

本文的封存、事后审计和补证分数沿用原审计归档。在公开仓库中可核对读件提示、模式覆盖汇总和上游公开原件链接。
