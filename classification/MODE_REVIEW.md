# 模式语义轻量复核 0.1

这是分类工作流的新增旁路。当前目录版本和正式执行配置可由既有候选冻结记录复核。此流程检查候选定义或目录变更的建议，日常案件仍使用固定分类入口。

## 触发与处置

新模式、定义或边界变更、拆合、退役及范围排除均送一次轻量复核。有实质争议时再安排独立复核。相同候选、证据、作用域和目录版本以程序输出的复核键核对，键一致可复用之前的复核记录。七卡开发审查使用已见原件。

定义层级和本案因果角色分别记录。定义层级可以是具体实现错误、局部失效关系、条件或现象、混合或不清楚。本案角色允许主缺陷、独立错误、下游或未知。纠正上游后局部错误是否仍成立可作判别思路。静态源码、来源报告及运行证据各按自身范围使用。

| 建议 | 依据及落点 |
| --- | --- |
| `reuse` | 同一机制在固定范围有覆盖证据，指向现有模式，保留案件和原件 |
| `revise_definition` | 重述、细分或上移，继续保留原候选 |
| `propose_addition` | 具体错误动作和目录差异均有据，进入提议 |
| `retain_candidate` | 保留待核，指出缺证或未决 |
| `retain_relation` | 保留局部关系、条件或现象和案卷 |
| `exclude_scoped` | 排除一个明确匹配。注明当前作用域、目标及正面反证 |

每条结果保持 `SUGGESTION_ONLY`，原候选继续登记。格式错误、引用失配或语义不支持时，将强建议回落为保留候选。置信度和样本数量仅为背景。实际复用、新增或排除依赖相应证据；跳过另行采纳记录的目录变更保持待审。正式采纳记录应列旧目录版本、候选 ID、复核键、证据判定、采纳者、理由和新版本。验证器只输出复核记录。

## 单次模型提示

只使用该批 INPUT、当前 catalog 和本说明。逐个回答五问。将正反理由与缺失事实分别记录。正反证据空缺时明确缺什么，无反证时可给空数组。在定性之前查阅目录最近邻。外部资料用于说明限定复用或方法联系。优先区分目标算子语义与外部方法的适用边界。

模型输出 JSON 对象 `{"reviews":[...]}`。每条记录含 `subject_id`、`state`（固定 `SUGGESTION_ONLY`）、`definition_level`（`implementation_error`、`mechanism_relation`、`condition_or_symptom`、`mixed_or_unclear`）、`case_role`（`primary`、`independent`、`downstream`、`unknown`）、`recommendation` 和下列字段：

- `questions.object_and_contract` 说清对象、正确行为、版本与范围。
- `questions.actual_action` 给出能够举证的具体错误动作或局部关系。
- `questions.case_role` 说明在本案为何独立或下游；未知保留为未知。
- `questions.near_neighbor` 指出最近模式和决定性区别。另给出 `comparison`，含可空 `pattern_id` 和 `relationship`（`equivalent`、`limited_reuse`、`partial_overlap`、`distinct`、`uncertain`、`none`）。
- `questions.disposition` 说明为什么保留、为什么暂不直接入库。另记录 `support`、`counterevidence` 数组及 `missing` 字符串数组。
- `reference_relationship` 取 `equivalent_reuse`、`limited_reuse`、`partial_overlap`、`method_borrowing` 或 `no_match`。在 `reference_basis` 说明实际读取的文件及片段，给出适用界限。用 `validation_basis` 区分现有正例、反例、缺证和独立验证状态。
- 复用时给出 `target_pattern_id`。限定排除时附 `exclusion_target` 和 `exclusion_scope`，范围取当前受评对象的 `scope`。

五问及正反证据均使用 `{text, anchors}`。锚点包含 `source_id`、`start_line`、`end_line` 和逐字 `quote`。行号按输入中的每份来源视图从 1 开始。来源元数据的 `original_start_line` 可回溯原件。外部方法的范围在 `reference_basis` 说明；案件的正反事实用同作用域的原件引文。单一来源可以支撑限定的报告或静态结论。

## 复核记录核查

```powershell
python -B -X utf8 classification/mode_review.py INPUT.json MODEL_OUTPUT.json
python -B -X utf8 classification/mode_review.py INPUT.json MODEL_OUTPUT.json --evidence-review EVIDENCE_REVIEW.json
```

候选输入使用 `catalog_version` 和 `subjects`，每项含 `id`、`definition`、`scope` 及 `sources`。作用域含案件 ID、动作 ID、来源版本、路径及声明类型。原件来源字段及引用规则沿用分类工作流。外部参考可放在 `references`。

核对旧复核时传入 `--previous`。 如本轮只复用，模型输出文件使用空的 reviews 列表 JSON。内容、证据、参考或目录变化会改变上下文键。

程序验证内容绑定、引用和版本，保留问题及原模型建议。真实引用只是来源标记。复核证据语义时，先运行不带证据复核参数的命令取得候选上下文键和原模型输出哈希，再填写 `EVIDENCE_REVIEW.json`。其中 `reviews` 列表每条含 `subject_id`、`cache_key`、`review_sha256`、`decision`（`supported`、`unsupported`、`uncertain`）、`reviewer`、`reason`。这项复查可由人或当前 Work 对照原件完成，保留实际判读范围。对已证新增、复用或排除的建议，程序要求正面原件及语义复查依据。范围匹配后仍由采纳另行记录处理正式变更。普通保留与修订建议无需先作强结论。
