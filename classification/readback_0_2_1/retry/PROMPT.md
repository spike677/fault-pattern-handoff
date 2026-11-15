# 开发读件复验

以 A.json 的可见原件和 catalog.json 为唯一案件材料。逐案独立识别算子语义、固定版本、具体错误动作和支撑事实，留下直接引用及有据推导。允许证据不足、上位和目录外。只按所述证据范围填 reported、static 或 runtime。只有运行声明才填 build 和 call_id。不得把修订标题或某个算子名称当作实际错误的充分证明。

输出 JSON 数组，每个对象有 case_id、operator、roles、actions。动作含 id、description、role、scope、facts。scope 含 version、path、claim。role 仅允许 primary（主动作）、independent（另一独立动作）或 downstream（下游）。只有 downstream 填 upstream_id。静态动作 scope.path 与所引同版本代码或 diff 的 path 一致。每个事实有 catalog 定义的 key、真假 value、explanation、anchors。引文锚点有 source_id、start_line、end_line、quote，行号在 A 中每条来源视图内从 1 开始。缺证省略事实，矛盾保留双方。上位事实可用 parameter_violation、address_violation、contribution_violation。已证目录外动作使用 established_other_defect，记录具体原因。根据原件判定合规或不适用时用 compliant 或 contract_inapplicable。

本次只提取事实。另记实际读写路径、操作和本次任何未决范围。使用新的执行上下文。开发原件曾用于前版，复验只检验从原件开始的入口。


交付前核对上述字段、角色枚举及各引用对应的视图行号。每个 case_id 提交至少一个动作。若证据不足，提交一个 primary 动作并如实省略不确定事实。
