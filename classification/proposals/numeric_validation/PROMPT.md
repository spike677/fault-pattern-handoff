# 数值机理候选读件

依据分发的原件、受评范围和七条冻结机理定义，先定位适用约定、实际旧路径，以及最先发生失真的操作。追踪失真状态的实际消费者。区分源码条件推导、作者陈述与同构建的实际运行。按原件事实生成结构化 JSON，旧目录已证的结果继续用旧事实键表达。

对目录外已证动作，用 `established_other_defect`、`applicable_contract`、`implementation_action` 和有据的 `causal_role` 描述。评价数值候选时还需要两个共同事实。用 `contribution_set_preserved` 核对计算项身份和重数。用 `distorted_value_consumed` 定位失真值如何进入归约、归一化或输出。只有事实确有锚点时才提交肯定。

| 机理 | 决定性事实 |
| --- | --- |
| NUM-01，累加状态过窄 | `loop_carried_narrow_state` 定位同一状态如何在连续更新之间反复窄化、读取和更新。说明最先发生的精度或范围损失。`wider_state_preserves_same_updates` 在保持计算项、顺序和运算相同的条件下对照宽状态，指出能恢复的量。合法的最终转换单独判断。 |
| NUM-02，方差消减 | `variance_from_raw_moment_difference` 定位旧路径怎样以原始二阶矩减去均值平方求方差，记录实际类型。`centered_variance_survives_at_same_precision` 在相同工作精度和相同数据上比较中心二阶矩，说明小方差何时丢失。`variance_consumed_by_normalization` 引用旧归一化实际使用该方差的路径。 |
| 归约前平方溢出 | `pre_reduction_square_overflow` 定位可表示的输入在哪道平方及结果存储之后超范围，随后如何进入归约。区分这个单次运算与跨迭代的状态存储。 |

对每个决定性事实，`claim_state=derived` 要同时引用同版本的 `requirement` 和动作作用域中的旧 `behavior`。从新补丁得到的约定或猜测只能作为观察。给出用于比较的输入、数据类型、关键中间值和依赖关系。作者报告的复现只有在路径、派发与版本都能对应时才用于扩展结论。给每个动作明确的作用域与角色。引用分发节选内显示的一基行号和来源 ID，使用既有事实协议的等级和锚点类型。只输出符合响应 schema 的 JSON。
