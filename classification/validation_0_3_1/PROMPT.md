# 0.3.1 分类执行提示

只读取当前批发给你的 A 包、冻结目录和规则。逐案先核目标版本、契约和实际执行路径，用一条短句说明看到的具体动作或缺证点。Issue 中明确确认的根因可以支持作者报告范围的结论。保留与故障同时发生或修复时新增的操作，以及作者的假设。

## 证据断言

每项事实保存目录事实键 `key`、布尔 `value`、简明 `explanation`、`claim_state` 和 `anchors`。每个锚包含 `source_id`、视图内一基起止行 `start_line`、`end_line`、逐字 `quote` 和用途 `use`。同一动作的锚点须对应 `scope.version`，不能拼接不同构建或未经证明等同的两份版本。缺证省略对应真或假，保留明确观察和候选解释。

| `claim_state` | 对应断言 | 锚点用途 |
| --- | --- | --- |
| `observation` | 可观察的代码、补丁或报告内容，例如旧分支缺项、补丁新增等待、报告修后通过 | `context` |
| `hypothesis` | 作者猜测或待排查的解释 | `context` |
| `confirmed_report` | 作者明确确认的具体事实，作用域为 `reported` | `confirmation` 引同一版本和作用域路径的 Issue 或报告 |
| `derived` | 由实际适用约定与目标版本的旧动作推出来的事实，说明推导链和近邻区别 | `requirement` 引约定，`behavior` 引同作用域代码或旧方 diff。操作、上位、证实目录外缺陷、排除及角色等决定性断言必须同时引二者。其他事实可只引其中一个相关依据 |
| `verified_runtime` | 与目标构建、动作和该次调用绑定的实测事实，作用域为 `runtime` | `runtime` 引同版本、路径、`build` 与 `call_id` 的运行记录 |

锚点使用 `behavior` 时，diff 只引旧侧上下文或删除行，新增行单列为 `context`。结论如需多个锚点，写清每个锚点证明的条件。代码观察和候选解释可以与决定性事实并存，程序只使用具备声明依据的断言作裁决。

- 填充或掩码存在只说明候选位置。判断它违反有效域时继续核实有效值域、非法项被实际消费及其影响。参与范围上位也需要有据的 `actual_contribution`。
- 屏障补丁和修后通过只支持改动与结果。核实旧队列或生产消费契约和旧执行路径缺少的依赖，再决定是否构成违约。
- 合法中性化、屏蔽、连续化或分层规约的反证须绑定在同一所评路径和对象。可见材料不足时保留上位或 `insufficient`。静态推导能证明违约时可在该范围确认。
- 同一替换动作支持 C1+C2 时，用同范围事实 `distinct_members_for_replacement` 说明两个计算项如何区分。

## 动作、因果角色和运行

每案事实包为 `{"case_id": "...", "fact_protocol": "classification_facts/0.3.1", "operator": "...", "roles": [], "actions": [...]}`。每个动作含 `id`、`description`、`role`、`scope`、`facts`。至少留一项评估，材料不足时描述待核动作或范围。每条具体说明保留实际操作及证据边界。`scope` 含 `version`、`path` 和 `claim`，后者为 `reported`、`static`、`runtime` 之一。静态路径绑定对应代码或 diff，运行路径另有实际证据一致的 `build` 和 `call_id`。

有证据表明实现动作本身违反约定时，填写 `implementation_action` 并给出可核定位。关系已经建立、具体实现动作或责任未知时保留机制。角色取 `primary`、`independent`、`downstream` 或 `unknown`。用 `causal_role` 独立记录角色依据，只有 `downstream` 附 `upstream_id` 并说明改正上游后该后果为何随之消失。两个并列且各自成立的根动作均可记 `independent`。缺证时记 `unknown`。程序会保留未经支持的角色提议，在正式输出中降为未知。

按实际材料使用目录事实、`established_other_defect`、`compliant` 或 `contract_inapplicable`。以 JSON 数组保存事实包，`case_id` 集合与 A 一致。执行 `python -B -X utf8 classify.py --batch A.json facts.json`，保持退出码、事实包、输出以及实际工具日志。对每项冲突、证据降级或未决角色说明范围。正式计分仍需逐项核对来源是否实际支持所声明的用途和推论。
