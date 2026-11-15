# 0.3 分类执行提示

仅从已封存的 A 包和随附的固定目录判断。A 包里作者的错误动作说明是可用证据。先识别源件版本、算子语义角色、实际路径、对应约定和具体动作，再提取事实；算子名、症状和修复标题仅用于定位可见材料。提取完成后，用冻结的本地分类规则得到结果。保留实际工具操作和事实提取日志。

每案给出一个事实包，其中包含 case_id、operator、roles、actions。每个动作包含 id、description、role、scope、facts。role 只允许 primary、independent、downstream 或 unknown；只有 downstream 填 upstream_id。scope 包含 version、path 和 claim。claim 只允许 reported、static、runtime。静态动作应绑定该版本中的代码或 diff 路径。只有实际运行声明才填写能与原件一致绑定的 build 和 call_id。

每个事实包含目录认可的 key、布尔 value、explanation 和 anchors。每处 anchors 记录 source_id、视图内一基 start_line、end_line 和逐字 quote。只在证据支持正面或反面事实时填真假。缺证时省略对应事实，互相冲突的事实在同一范围内分别留档。表示上位关系可用 parameter_violation、address_violation、contribution_violation。已证具体动作超出目录时记录 established_other_defect 并说明原因。按实际材料使用 compliant 或 contract_inapplicable。

一个动作造成多个后果时，分别说明独立错误和下游关系。对 C1/C2/C3，先判断目标结果、有效项、逻辑来源及合法重数，再判断哪个实际实现动作违反了约定。有明确的同作用域证据才填 implementation_action=true，并写明可核验动作及引文。局部关系成立而责任未明时保留支持关系的事实，使用 unknown 角色，不补造起始动作。需要表达同一替换动作的 C1 与 C2 时，只有材料确证两个成员不同才提供同作用域的 distinct_members_for_replacement。证据只到上位关系时，保留有据层级并指明缺失点。整个案由至少一个动作记录表示；材料不足时保留证据不足评估项。

最终事实包是 JSON 数组，按 case_id 与 A 对齐。通过 classify.py --batch 产生与事实包配套的结果列表。输出和日志交回当前隔离运行的捕获步骤。
