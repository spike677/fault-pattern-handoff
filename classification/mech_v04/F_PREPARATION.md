# F 独立评估准备

正式裁决目录为 `MECH-v0.4`，判定版本为 `0.4.1`。七条历史卡沿用原内容，NUM-01 与 NUM-02 已准入。v0.3 的入口继续服务历史锁定复算。本次冻结包含正式目录、判定、读件提示、响应 schema、评分程序和已见事件清单。单独分发的 F 执行包仅包含这些冻结依赖和清单，供未来的隔离环境接收 A。[正式目录](catalog.json) · [准入评审](ADMISSION_REVIEW.md) · [F 冻结](F_FREEZE.json)

## 独立样本与保管

- 由材料整理者选取未见真实事件家族。优先覆盖两条新模式的正例、旧模式正例、最接近的交界、合法末端精度或允许误差、缺证和已证目录外。每个家族只计算一次，跨 Issue、补丁、回移、镜像和复用的材料按共同家族归并。缺某种覆盖时以实得样本报告。
- 整理者仅在 A 留下原件、版本和锚点所需的元数据。B 包记录预期机理、具体动作、角色或上游、关键引证和近邻，由另一个人或上下文审查并独立保管。同一人的不同工作目录只有在实际访问隔离得到证实时可用于正式评估。
- 对已见记录检查 `development-exposures.json`。它合并 v0.4.1 暴露清单、N501–N503、近期核验过的关联提交和来源。E06、G05、V406、已完成的 13 个演练家族及封存后相关补证均计入当前 413 条暴露键。[开发暴露清单](development-exposures.json)
- 每轮用独立访问范围、新进程和各自的实测哨兵。实际运行记录由外部见证确认。两轮捕获后先锁定原始日志、事实和预测，再由判卷者对照 B。角色和具体动作各有指标。缺外部见证或实际隔离的材料按 `exercise` 使用。

## 执行入口

以下命令从检出根目录运行。实际 `A.json`、`B.json` 及输出使用各自独立目录。当前交付冻结的是执行工具和输入规则，后续正式评估需用未暴露事件另立 A/B，并验证真实执行环境。

```powershell
$f = 'classification/mech_v04/F_FREEZE.json'
$eval = 'classification/mech_v04/evaluation.py'
$sentinel = '../custody/sentinel.bin'
python -B -X utf8 $eval check-freeze $f
python -B -X utf8 $eval seal $f A.json ../custody/B.json seal.json --kind real
python -B -X utf8 $eval probe $sentinel probe1.json
python -B -X utf8 $eval read $f A.json seal.json round1.jsonl --probe probe1.json
python -B -X utf8 $eval capture $f A.json seal.json round1.jsonl context1.json run1.json --probe probe1.json
python -B -X utf8 $eval probe $sentinel probe2.json
python -B -X utf8 $eval read $f A.json seal.json round2.jsonl --probe probe2.json
python -B -X utf8 $eval capture $f A.json seal.json round2.jsonl context2.json run2.json --probe probe2.json
python -B -X utf8 $eval lock $f A.json seal.json run1.json run2.json lock.json
python -B -X utf8 $eval score $f A.json seal.json run1.json run2.json lock.json ../custody/B.json review.json score.json
```

`read` 返回实际上下文 ID 和冻结执行配置。外部见证将验明的执行人、见证人、哨兵哈希和四项访问声明合并到 `contextN.json`。这些字段为 `executor_id`、`witness_id`、`probe_sha256`、`isolation_mechanism`、`sentinel_in_custody`、`only_approved_inputs`、`fresh_context` 和 `no_prior_predictions`。真实运行应由不同于保管者和审查者的执行者完成。具体 A/B 对象和判卷文件沿用分类评估工作流。[A/B 与复核规则](../WORKFLOW.md)

合成端到端测试覆盖正式模式接入、封存、两轮捕获、锁定、严格评分、已有事件拒绝和哨兵可读中止。已完成的 13 家族双轮源材料评估按演练归档。三项实际访问探测均可读，且缺外部见证。正式 F 需要合格隔离、外部见证和新的未见样本。
