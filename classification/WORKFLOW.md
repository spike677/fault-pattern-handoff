# 算子故障机理分类试点 0.3.1

本流程接受已知 Bug 材料，输出可追溯的实现缺陷分类。模式卡和算子语义索引在 `catalog.json`。历史诊断入口在 `diagnosis_mvp`。实验的模型回复、工具配置和事实包需要留档，便于将抽取差异与规则差异分开复核。

## 固定读件流程

将下列步骤作为执行提示。分发给评估执行者的材料限于冻结模式定义、程序、本流程及 A 包。准备事实时应使用执行者可见的原件片段。材料无法建立具体动作时，提交一个证据不足评估项，范围与事实按实填写。A 包包含来源文本本身，可保留作者的根因陈述。

1. 先逐件记录版本、路径、算子和涉及的语义角色。区分作者陈述、固定源码推导和绑定到具体运行的观察。遇到版本不明的报告，说明它所描述的动作和声明范围。复述原始记录时保留其不确定性。
2. 找出可单独说明的实现动作，为每个动作分配中性 ID，用一句话写清错误发生的位置与操作。依次提取生效约定、实际动作和区分近邻所需的事实。每个事实需有原件锚点。需要结合多句或源码推导时，列出这些锚点，并在解释中给出推导链。原件中的修复标题、症状和算子名可作入口线索。
3. 参照模式卡的必要事实填写 `facts`。只有明确反证时填 `false`。缺证时省略对应事实，冲突材料则保留双方。仅在上位约定已被证实破坏时填写相应的上位事实。已证明是目录外缺陷时，记录具体动作和支持证据。按源件报告、源码或运行选择声明范围。
4. 记录主缺陷、其他独立错误及有必要保留的下游失效关系。为下游动作指明其上游 ID，用原件说明依赖。给每个独立错误保留单独证据。评审应检查纠正上游动作后，下游是否仍有另一个可独立举证的实现错误。
5. 保存事实包，按下面的入口运行规则。对照原文审查决定性事实、声明范围和近邻解释。语义支持由原件复核确认。运行复查时固定原件、目录、执行提示及模型和工具配置。

## 接口与初始复跑

每个输入案例使用 `case_id` 和 `sources`。来源含 `id`、`version`、`path`、`kind` 与 `text`。视图可保留 `origin`、`original_start_line`，便于逆查完整原件。事实包按同一 `case_id` 记录算子、角色及错误动作。动作 `role` 取 `primary`、`independent`、`downstream` 或 `unknown`。只有下游动作填写 `upstream_id`。静态动作的 `scope.path` 使用所引固定版本代码或 diff 的路径。事实引文包含来源 ID、视图内一基起止行与原句。静态代码的声明绑定版本及路径。运行声明才需要构建、调用和运行观测。

规则入口从交接仓根目录运行。单案个例可以从开发包各取同一 `case_id` 的对象用于检查。

```powershell
python -B -X utf8 classification/classify.py CASE.json FACTS.json
python -B -X utf8 classification/classify.py --batch classification/development_cases.json classification/validation_0_3/development_facts_0_3.json
python -B -X utf8 -m unittest discover -s classification
```

状态 `leaf`、`parent`、`insufficient`、`outside` 分别表示具体模式、上位类、证据不足和范围外。范围外细分 `compliant`、`inapplicable`、`outside_catalog`。最后一种表示已证有具体缺陷，来自其近邻或已知目录边界。相同上下游链按独立动作计数。程序能够验证引文、作用域、冲突及必要字段，事实是否确由引文支持归判卷复核。

## 11 个既有检查的用途

静态材料可直接支持分类。存在可比较的结构化观测时可调用 `diagnosis_mvp/diagnose.py` 的局部计算。该脚本的路线和调用 ID 属于它自己的运行取证接口。

| 旧判据 | 实际计算及角色 | 分类所需的额外语义与回归 |
| --- | --- | --- |
| `INTERFACE_CONTRACT` | 比较规范化的两个值是否相同，记录检查发现 | P1 需要字段来源不等价。P2 需要正确读取及特殊状态误处理。用 N24 两版本和 N07 近邻复核 |
| `PLAN_GENERATION` | 比预期范围与生产范围，定位线索 | 同单位、同作用域。范围先在上游错误时，成员后果单独登记为下游 |
| `PLAN_TRANSFER` | 比生产范围与接收范围，定位线索 | 同一次传递、同单位。断在上游时保留区分证据 |
| `PLAN_CONSUMPTION` | 比接收范围与消费范围，定位线索 | 消费边界与成员语义分开。计划范围不符仍需证明具体错误动作 |
| `ADDRESS_MAPPING` | 计算基址加各维坐标乘步长，比较实际元素偏移 | L1 需要生效视图和连续布局假设。L2 要有单位和换算证据，旧函数只比较元素偏移。分别用 N20、N10 和 N06 检查 |
| `LOCAL_NUMERIC_DEVIATION` | 在参考资格、dtype 和容差可核时比较数值，记录检查发现 | 局部超差仅作线索。用历史逐段误差和非法参考回归校验 |
| `UNEXPECTED_CONTRIBUTION` | 实际身份集合减预期身份集合，C1 证据支撑 | 需明确实际已形成贡献、资格与边界，区分存在 padding 和 padding 真正参与 |
| `REPEATED_CONTRIBUTION` | 比预期身份的实际与预期重数，C3 证据支撑 | 需追溯同一原始贡献，核对允许的重数及分层规约语义 |
| `MISSING_CONTRIBUTION` | 按身份统计实际缺少的重数，C2 证据支撑 | 需证明该贡献语义上必需，区分合法 mask、稀疏过滤与分工 |
| `COLLECTIVE_PARTICIPATION` | 对比参与者与轮次多重集，定位线索 | 轮次不符可帮助检查身份，时序分类由后续范围处理 |
| `SHARED_SLOT_EARLY_REUSE` | 检查同分配、交叠字节范围、代际及共同顺序，定位线索 | 同一地址的跨轮访问需确认顺序，生命周期模式由后续范围处理 |

## 裁决与评分口径 0.3

目录 ID P1–C3 保持稳定，展示名和计分引用采用 0.3。“计算项的参与范围问题”核查 C1 的参与资格。“计算项重复／遗漏问题”核查 C2/C3 的必需项和重数。若 C1+C2 的同一替换动作有同范围证据表明针对不同项，输出计算项问题上位类与两个相容属性，最多计一个已证的独立动作。

C 类的叶级裁决记录局部机制。要主张具体独立错误，事实包还要以同作用域原件支持 implementation_action 并在解释中给出实际动作。关系有据、动作未明时仍输出关系模式，角色记 unknown，独立缺陷分母单列。相同或重复读出的物理值需按逻辑来源及操作语义再核。核心事实冲突阻止肯定结论，只有叶级区分不足时保留有据层级。

有多个允许结果时，金标准以显式 primary 决定分母，替代结果另计。组层级和 C1+C2 组合随目录冻结。机理持久化用 MECH-v0.3，API42、V4 保留输入构造的轴及各自分母。术语、参考关系及例外边界见 TERMS_AND_REFERENCES.md。

历史配置、事实和评分按原 Git 快照复跑。首批 0.3 开发试测的可执行快照为 `064a872082b6f0c2eb549558148ad3a5acf7028e`。修订版沿用 0.3 目录和 `MECH-v0.3`，冻结协议为 `classification_only/0.3.1`。历史 A 可以再次用于开发回归，配置、提示或模式变化后的未见复验使用新事件家族。

## 独立样本交接

独立整理者在分类执行环境之外准备 A、B 两包。最终入组及评分以冻结标准为准，在执行者得到材料前锁定清单、复核记录及哈希。开发暴露清单供整理者排查同源事件，实际候选先保存在整理者环境。约 20 个真实事件家族是筹备目标，所有已入组家族计入分母。缺真实样本的类别记录实际覆盖。

A 只含原始材料的评估视图及追溯元数据。B 在执行者不可访问的位置由整理者私下保管。使用外部权限控制并用与答案无关的哨兵验证执行者的读取确实被拒绝。整理者与判卷复核者分别签录其职责和检查记录。每次运行保存原件及配置哈希和输出。两次运行分别启动隔离上下文，在都冻结后开启 B 包。程序保存流程记录，实际独立性由隔离和保管记录支持。用同一共享工作区演练时，结果标为流程演练。

样本答案以 A 内可见证据裁定，保留语义事实及近邻的审查理由。判卷时逐项审查正确标签的决定性事实。缺证或引文语义不支持时，保留标签命中与严格证据失败两项结果。答案修订保留旧版本及理由，对受影响预测统一重评。已揭盲家族纳入开发暴露清单。

## 分类单轨命令

运行文件使用 JSON。文件路径指向对应角色可访问的存储位置，A 与 B 实际分开放置。以下命令从交接仓根目录运行。

```powershell
python -B -X utf8 classification/evaluate.py freeze execution.json development_lineage.json freeze.json --artifact validation_0_3_1/PROMPT.md --artifact TERMS_AND_REFERENCES.md
python -B -X utf8 classification/evaluate.py seal freeze.json A.json B.json seal.json --kind real
python -B -X utf8 classification/evaluate.py probe SENTINEL probe-1.json
python -B -X utf8 classification/evaluate.py capture freeze.json A.json seal.json results-1.json context-1.json facts-1.json execution-1.log run-1.json --probe probe-1.json
python -B -X utf8 classification/evaluate.py probe SENTINEL probe-2.json
python -B -X utf8 classification/evaluate.py capture freeze.json A.json seal.json results-2.json context-2.json facts-2.json execution-2.log run-2.json --probe probe-2.json
python -B -X utf8 classification/evaluate.py lock freeze.json A.json seal.json run-1.json run-2.json lock.json
python -B -X utf8 classification/evaluate.py score freeze.json A.json seal.json run-1.json run-2.json lock.json B.json review.json score.json
```

`freeze` 由开发者操作，冻结当前规则文件、读件流程、详细执行提示、模型和工具配置以及开发暴露键。实际执行配置 `execution.json` 含 `model`、`prompt` 和 `tools`。命令中的暴露清单应使用本批实审版本，可从随仓的 `classification/development_lineage.json` 扩展。键使用 `event:平台/组织/仓库#Issue号`、`patch:平台/组织/仓库!PR号` 和经对照的补丁、源码、镜像或答案键。别名需按实际事件连通关系归并。

`seal` 在整理者可查看双包的环境执行。A 为 `{"cases":[...]}`，每案的多个来源保留原件片段。B 记录整理者和独立答案复核者 ID、筛选说明及全部案例。每案含原件和暴露复核、事件家族、来源键、算子及期望动作。期望动作记录可接受状态、模式或上位类、关键事实、近邻和上下游关系。`specific_action` 写 A 所支持的具体错误操作，证据不足时用 `null`。允许集合有多个不同裁决时显式指定 `primary`。如果 A 支持至少两个根动作且没有确定主次，在案级设置 `root_order_unspecified: true` 并填写 `root_order_rationale`。评分仍核对每条下游边对应的上游动作。

`probe`、读件、分类和 `capture` 分别从两个隔离执行上下文运行。两个 `facts` 文件各是该次独立提取的事实包列表，两个 `results` 文件各可用 `classify.py --batch A.json facts-1.json` 生成，第二次使用其独立事实包。保留实际执行日志。上下文记录执行者、上下文、外部见证人、隔离方式、实际冻结配置、哨兵哈希，以及独立保管、只读已批准输入、新上下文、无先前结果四项见证。整理者与见证人确认被拒绝或未挂载的哨兵确实部署在待验证边界。

`lock` 锁定两轮输出。判卷者随后持锁定记录及 B 运行 `score`。按错误操作、对象、源码位置与作用域对齐预测与参考动作。每项 `facts_supported` 核查裁决所需的证据，另以 `action_correct` 和 `action_rationale` 核查具体操作或应保留的未知。逐动作登记失败成因及遗漏，重复断言可标 `double_count: true`。判卷记录的 `stability` 数组逐案包含 `case_id`、`same_decisive_facts`、`same_specific_action` 和 `rationale`。严格标签和允许集合内的一致性分别计算，因果结构按对齐的动作身份与边比较。答案修订使用 `score --revision` 并绑定原 B 哈希，保留原结果。

评分文件分别给出有据机理与状态、按家族的叶级覆盖、具体动作及未知动作误确认、因果关系和完整案件。独立动作按身份对账 `claimed`、`expected`、`true_positive`、`false_positive`、`false_negative` 和 `duplicates`，可回溯到动作或遗漏项。两个执行上下文都记录冻结的 `execution` 配置。共享权限边界中的开发试测使用 `seal --kind exercise`。

与命令对应的最小 JSON 构造和失败回归见 `test_evaluate.py`。实际原件不得与其答案存放在同一可读目录或分发包。
