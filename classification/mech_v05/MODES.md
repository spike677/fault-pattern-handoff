# MECH-v0.5 公开模式定义

开发知识目录：原九条保持不变，31个新增开发定义可按证据匹配，5个研究条目只检索。定义数不是独立泛化准确率。

完整机器规则见 [catalog.json](catalog.json)，事实含义在 fact_definitions；历史身份仅作条件投影。

## P1 · 参数来源误读

父类：`parameter`；状态：`inherited_v04`；分类启用：`True`。

适用路径从语义不等价的槽位、字段或参数取得值。

必要事实：`applicable_contract`、`expected_source`、`actual_source`、`non_equivalent_source`。

排除事实：`correct_source`、`equivalent_source`。

## P2 · 特殊参数状态误解释

父类：`parameter`；状态：`inherited_v04`；分类启用：`True`。

正确取得特殊状态后，套用不适用的有效值处理，改变状态语义。

必要事实：`applicable_contract`、`correct_source`、`special_state`、`wrong_state_treatment`。

排除事实：`non_equivalent_source`、`state_treatment_allowed`。

## L1 · 错误采用连续布局寻址

父类：`address`；状态：`inherited_v04`；分类启用：`True`。

路径应按原视图寻址且地址被消费前没有正确连续化，实际地址映射的至少一个必要项错误采用连续布局假设，导致映射偏离原视图。

必要事实：`applicable_contract`、`supported_view`、`no_correct_contiguous_conversion`、`contiguous_formula`。

排除事实：`correct_contiguous_conversion`、`view_unsupported`、`view_formula_correct`。

## L2 · 寻址单位换算错误

父类：`address`；状态：`inherited_v04`；分类启用：`True`。

地址运算在 element、bit 与 byte 间的转换遗漏、重复或落在错误位置。

必要事实：`applicable_contract`、`expected_units`、`storage_width`、`wrong_conversion`。

排除事实：`address_units_consistent`。

## C1 · 无效计算项纳入

父类：`item_participation`；状态：`inherited_v04`；分类启用：`True`。

按当前计算约定无资格参与的逻辑计算项，实际进入目标计算，且未按该运算语义中性化或排除。

必要事实：`applicable_contract`、`ineligible_member`、`actual_contribution`。

排除事实：`member_eligible`、`contribution_neutralized`。

## C2 · 必需计算项遗漏

父类：`item_multiplicity`；状态：`inherited_v04`；分类启用：`True`。

在给定计算语义下，至少一次必须保留的逻辑计算项未到达目标结果，且该次贡献未由等价路径保留。

必要事实：`applicable_contract`、`required_member`、`omitted_contribution`。

排除事实：`contribution_preserved`、`omission_permitted`。

## C3 · 同源计算项重复计入

父类：`item_multiplicity`；状态：`inherited_v04`；分类启用：`True`。

相对于同一目标结果，同一逻辑来源及语义角色的计算项实际计入次数超过该操作的约定。

必要事实：`applicable_contract`、`original_contribution_identity`、`expected_multiplicity`、`excess_multiplicity`。

排除事实：`expected_multiplicity_met`、`repeat_semantics_permitted`。

## NUM-01 · 运行累加状态过窄

父类：`numerical_evaluation`；状态：`inherited_v04`；分类启用：`True`。

同一运行累加状态在连续更新之间被保存至不足以满足适用约定的窄类型，后续消费该失真状态。

必要事实：`applicable_contract`、`implementation_action`、`contribution_set_preserved`、`distorted_value_consumed`、`loop_carried_narrow_state`、`wider_state_preserves_same_updates`。

排除事实：`pre_reduction_square_overflow`、`variance_from_raw_moment_difference`、`compliant`、`contract_inapplicable`。

## NUM-02 · 原始矩差求方差的有限精度消减

父类：`numerical_evaluation`；状态：`inherited_v04`；分类启用：`True`。

在保持输入和工作精度时，用原始二阶矩减均值平方形成失真的方差，该方差被归一化实际消费。

必要事实：`applicable_contract`、`implementation_action`、`contribution_set_preserved`、`distorted_value_consumed`、`variance_from_raw_moment_difference`、`centered_variance_survives_at_same_precision`、`variance_consumed_by_normalization`。

排除事实：`pre_reduction_square_overflow`、`loop_carried_narrow_state`、`compliant`、`contract_inapplicable`。

## CTL-EMPTY-01 · 零任务进入不支持的调度入口

父类：`control`；状态：`reviewed_definition`；分类启用：`True`。

合法零工作调用未按约定短路，而进入要求至少一个有效任务的调度入口。

必要事实：`applicable_contract`、`implementation_action`、`zero_work_legal`、`zero_work_entry_unsupported`、`zero_work_entry_taken`。

排除事实：`pending_work_needs_drain`、`empty_entry_supported`、`compliant`、`contract_inapplicable`。

## META-SHAPE-01 · 结果形状元数据推导违约

父类：`metadata`；状态：`reviewed_definition`；分类启用：`True`。

旧实现把不符合算子形状约定的输出 shape/rank/动态维交给分配或下游消费者。

必要事实：`applicable_contract`、`implementation_action`、`expected_output_shape_bound`、`wrong_output_shape`、`wrong_shape_consumed`。

排除事实：`output_shape_correct`、`only_address_formula_wrong`、`compliant`、`contract_inapplicable`。

## PLAN-SPLIT-01 · 有效任务域规划失配

父类：`plan`；状态：`reviewed_definition`；分类启用：`True`。

任务划分或重规划未保持所需逻辑任务域或任务原子性，并把失配计划交付执行。

必要事实：`applicable_contract`、`implementation_action`、`required_task_domain_bound`、`planned_task_domain_wrong`、`wrong_plan_executed`。

排除事实：`task_domain_preserved`、`only_buffer_capacity_wrong`、`compliant`、`contract_inapplicable`。

## ADR-GEOM-01 · 寻址几何项或对象内基址错误

父类：`address`；状态：`reviewed_definition`；分类启用：`True`。

在单位和整数表示均正确时，寻址公式遗漏或错置组基址、轴组合或窗口项，错误地址被消费。

必要事实：`applicable_contract`、`implementation_action`、`expected_geometry_bound`、`wrong_geometry_term`、`address_units_consistent`、`address_representation_exact`、`not_dense_layout_substitution`、`distorted_address_consumed`。

排除事实：`geometry_mapping_correct`、`contiguous_formula`、`wrong_conversion`、`compliant`、`contract_inapplicable`。

## ADR-OWNER-01 · 缓存逻辑对象与物理归属错配

父类：`address`；状态：`research_definition`；分类启用：`False`。

缓存访问使用与当前逻辑批次或对象身份不一致的物理槽、block table归属。

必要事实：`applicable_contract`、`implementation_action`、`cache_ownership_contract`、`wrong_cache_owner`、`wrong_owner_storage_consumed`。

排除事实：`cache_owner_correct`、`only_geometry_term_wrong`、`compliant`、`contract_inapplicable`。

## SYNC-DEP-01 · 必要同步依赖或参与协议违约

父类：`synchronization`；状态：`reviewed_definition`；分类启用：`True`。

活跃生产消费路径违反已要求的完成、代际匹配或屏障参与协议。

必要事实：`applicable_contract`、`implementation_action`、`required_ordering_protocol`、`ordering_protocol_violated`、`unsynchronized_consumer_reachable`。

排除事实：`ordering_protocol_satisfied`、`only_barrier_patch_success`、`compliant`、`contract_inapplicable`。

## NUM-NARROW-01 · 非循环状态在必要运算前过早窄化

父类：`numerical_evaluation`；状态：`reviewed_definition`；分类启用：`True`。

在后续必要运算仍需原信息时先窄化输入或一次性中间值，使信息不可恢复地丢失并被消费。

必要事实：`applicable_contract`、`implementation_action`、`needed_precision_before_operation`、`premature_narrowing`、`not_loop_carried_narrow_state`、`narrowing_loss_consumed`、`deferred_narrowing_preserves_contract`。

排除事实：`narrowing_allowed_at_this_boundary`、`loop_carried_narrow_state`、`compliant`、`contract_inapplicable`。

## NUM-ABSORB-01 · 非线性求值前的小量吸收

父类：`numerical_evaluation`；状态：`reviewed_definition`；分类启用：`True`。

有限精度加法先吸收随后非线性结果所需的小量，等价稳定表达式可在相同精度下保留它。

必要事实：`applicable_contract`、`implementation_action`、`same_terms_and_precision`、`small_term_absorbed_before_nonlinearity`、`stable_expression_preserves_small_result`、`distorted_value_consumed`。

排除事实：`variance_from_raw_moment_difference`、`expression_meets_error_contract`、`compliant`、`contract_inapplicable`。

## NUM-ORDER-01 · 受合同约束的浮点累加次序违约

父类：`numerical_evaluation`；状态：`reviewed_definition`；分类启用：`True`。

逻辑项及次数相同，但实际加法配对或逐步舍入违反明确的一致性、顺序或误差要求。

必要事实：`applicable_contract`、`implementation_action`、`same_contribution_ledger`、`required_accumulation_order_or_budget`、`accumulation_order_violates_contract`、`order_difference_consumed`。

排除事实：`order_difference_within_contract`、`loop_carried_narrow_state`、`compliant`、`contract_inapplicable`。

## CTL-DISPATCH-01 · 选择不满足所需语义的执行分支

父类：`control`；状态：`reviewed_definition`；分类启用：`True`。

条件选择或快捷路径忽略必要语义/能力条件，使合法请求进入不实现其所需计算的分支。

必要事实：`applicable_contract`、`implementation_action`、`required_execution_semantics`、`selected_branch_incompatible`、`incompatible_branch_taken`。

排除事实：`selected_branch_satisfies_contract`、`input_outside_promised_support`、`compliant`、`contract_inapplicable`。

## VALID-SUPPORT-01 · 必需的不支持场景拦截缺失

父类：`validation`；状态：`reviewed_definition`；分类启用：`True`。

合同要求在执行前拒绝的后端配置未被守卫排除，进入不支持该配置的实际路径。

必要事实：`applicable_contract`、`implementation_action`、`rejection_required_for_configuration`、`required_guard_missing`、`unsupported_configuration_executed`。

排除事实：`configuration_supported`、`unsupported_configuration_rejected`、`compliant`、`contract_inapplicable`。

## NUM-RANGE-01 · 活跃浮点中间值超出表示范围

父类：`numerical_evaluation`；状态：`reviewed_definition`；分类启用：`True`。

有限合法输入的约定结果可表示，旧活跃中间运算先超出实际浮点格式范围，失真随后被消费。

必要事实：`applicable_contract`、`implementation_action`、`finite_input_target_representable`、`actual_working_format_bound`、`intermediate_nonfinite_created`、`overflow_result_consumed`。

排除事实：`input_already_nonfinite`、`target_mathematically_out_of_range`、`overflow_path_not_consumed`、`compliant`、`contract_inapplicable`。

## BUF-EXTENT-01 · 正确起址上的访存长度或足迹违约

父类：`buffer`；状态：`reviewed_definition`；分类启用：`True`。

起始对象和地址正确，但实际搬运/向量访问足迹超出该对象的合法有效区间。

必要事实：`applicable_contract`、`implementation_action`、`memory_object_extent_bound`、`memory_start_correct`、`transfer_extent_exceeds_object`、`out_of_extent_access_executed`。

排除事实：`transfer_extent_within_object`、`only_address_start_wrong`、`compliant`、`contract_inapplicable`。

## REP-META-01 · 布局描述与实际数据表示错配

父类：`representation`；状态：`reviewed_definition`；分类启用：`True`。

向消费者交付与实际payload格式不一致的布局、块轴或格式描述，使其按错误表示解释数据。

必要事实：`applicable_contract`、`implementation_action`、`actual_payload_layout_bound`、`layout_descriptor_mismatch`、`mismatched_descriptor_consumed`。

排除事实：`descriptor_matches_payload`、`only_result_shape_derivation_wrong`、`compliant`、`contract_inapplicable`。

## NUM-DOMAIN-01 · 贡献项放入错误缩放或变换域

父类：`formula`；状态：`reviewed_definition`；分类启用：`True`。

应在指定实值域消费的贡献被放到另一缩放/变换域，使其数学权重即使在精确算术中也错误。

必要事实：`applicable_contract`、`implementation_action`、`contribution_domain_contract`、`contribution_inserted_in_wrong_domain`、`domain_mismatch_changes_formula`、`wrong_domain_result_consumed`。

排除事实：`domain_order_contract_satisfied`、`only_scale_source_wrong`、`compliant`、`contract_inapplicable`。

## BUF-INIT-01 · 消费前的状态初始化义务缺失

父类：`buffer`；状态：`reviewed_definition`；分类启用：`True`。

缓冲区或归约状态在首次消费前未取得当前调用所要求的初值，遗留/未初始化状态被消费。

必要事实：`applicable_contract`、`implementation_action`、`initial_state_required`、`required_initial_state_missing`、`uninitialized_state_consumed`。

排除事实：`all_slots_written_before_read`、`previous_state_is_valid_initial_state`、`compliant`、`contract_inapplicable`。

## CTL-EMPTY-OUT-01 · 空更新分支未履行结果物化义务

父类：`control`；状态：`reviewed_definition`；分类启用：`True`。

合法空更新分支虽无更新项，仍须复制或物化规定结果；旧早退未建立该输出。

必要事实：`applicable_contract`、`implementation_action`、`empty_update_requires_output`、`empty_branch_skips_materialization`、`missing_output_postcondition`。

排除事实：`empty_output_already_materialized`、`output_alias_permitted_and_satisfied`、`compliant`、`contract_inapplicable`。

## REP-CONVERT-01 · 数值类型边界的必需转换缺失

父类：`representation`；状态：`reviewed_definition`；分类启用：`True`。

同一语义值进入要求不同数值类型的消费者前，未执行合同要求的数值转换。

必要事实：`applicable_contract`、`implementation_action`、`producer_consumer_representation_contract`、`required_numeric_conversion_missing`、`unconverted_value_consumed`。

排除事实：`numeric_conversion_correct`、`different_logical_object_selected`、`conversion_not_required`、`compliant`、`contract_inapplicable`。

## REP-WIDTH-01 · 消费者读宽与实际存储格式不符

父类：`representation`；状态：`reviewed_definition`；分类启用：`True`。

同一语义对象按一种格式生产和存储，却被消费者用不一致的宽度和类型解释其内存。

必要事实：`applicable_contract`、`implementation_action`、`producer_storage_format_bound`、`consumer_storage_width_wrong`、`wrong_width_value_consumed`。

排除事实：`producer_consumer_widths_match`、`producer_actual_write_width_unknown`、`compliant`、`contract_inapplicable`。

## REP-REINTERPRET-01 · 保位解释被误作数值转换

父类：`representation`；状态：`reviewed_definition`；分类启用：`True`。

需保持数值语义的边界对同一位型只作类型重解释，再以不同编码的数值参与运算。

必要事实：`applicable_contract`、`implementation_action`、`numeric_value_conversion_required`、`bit_reinterpretation_used_as_conversion`、`reinterpreted_numeric_value_consumed`。

排除事实：`bit_preserving_transport_required`、`numeric_conversion_correct`、`compliant`、`contract_inapplicable`。

## DATA-SIGN-01 · 符号位合同被数值比较替代

父类：`data_semantics`；状态：`reviewed_definition`；分类启用：`True`。

需要符号位语义的实现改用数值大小比较，无法保留负零或合同指定NaN符号的行为。

必要事实：`applicable_contract`、`implementation_action`、`sign_bit_semantics_required`、`numeric_comparison_replaces_signbit`、`distinguishing_signed_value_consumed`。

排除事实：`numeric_sign_comparison_is_contract`、`signbit_extraction_correct`、`compliant`、`contract_inapplicable`。

## META-INDEX-01 · 输出索引的逻辑轴序映射错误

父类：`metadata`；状态：`reviewed_definition`；分类启用：`True`。

输出索引使用不符合被选轴和逻辑坐标的编号规则，即使数值结果本身可正确。

必要事实：`applicable_contract`、`implementation_action`、`output_index_coordinate_contract`、`output_index_mapping_wrong`、`wrong_index_returned`。

排除事实：`output_index_mapping_correct`、`only_memory_address_wrong`、`compliant`、`contract_inapplicable`。

## BUF-CAP-01 · 中间缓冲容量预算不足

父类：`buffer`；状态：`reviewed_definition`；分类启用：`True`。

活跃中间对象的最大并存需求已明确，但旧容量计算低估需求并被实际分配/访问采用。

必要事实：`applicable_contract`、`implementation_action`、`live_buffer_demand_bound`、`buffer_capacity_underestimated`、`undersized_buffer_used`。

排除事实：`buffer_capacity_sufficient`、`only_transfer_length_wrong`、`compliant`、`contract_inapplicable`。

## NUM-ROUND-01 · 转换舍入或饱和规则违约

父类：`numerical_evaluation`；状态：`reviewed_definition`；分类启用：`True`。

在正确转换边界采用不满足当前合同的舍入或饱和规则，区分输入下产生不同结果。

必要事实：`applicable_contract`、`implementation_action`、`rounding_saturation_contract`、`wrong_rounding_or_saturation_mode`、`rounding_distinguishing_input_consumed`。

排除事实：`rounding_mode_permitted`、`rounding_controls_equivalent_for_input`、`compliant`、`contract_inapplicable`。

## DATA-NONFINITE-01 · 已有非有限数据传播规则违约

父类：`data_semantics`；状态：`reviewed_definition`；分类启用：`True`。

对已存在的NaN/Inf数据使用违反算子规定的传播、屏蔽或分支规则。

必要事实：`applicable_contract`、`implementation_action`、`nonfinite_propagation_contract`、`existing_nonfinite_value`、`nonfinite_handling_violates_contract`。

排除事实：`nonfinite_handling_allowed`、`nonfinite_is_internal_marker`、`first_nonfinite_created_by_overflow`、`compliant`、`contract_inapplicable`。

## SYNC-DRAIN-01 · 无新任务时遗漏在途工作排空

父类：`synchronization`；状态：`reviewed_definition`；分类启用：`True`。

流水线没有新的输入任务时，旧退出条件跳过先前已生产、仍应完成的在途工作。

必要事实：`applicable_contract`、`implementation_action`、`pending_work_needs_drain`、`empty_iteration_skips_drain`、`pending_result_not_completed`。

排除事实：`no_pending_work`、`pending_work_fully_drained`、`compliant`、`contract_inapplicable`。

## CTL-TAIL-01 · 整除余数被误作末个整块有效长度

父类：`plan`；状态：`reviewed_definition`；分类启用：`True`。

有效域非空且恰好整除块长时，旧控制将余数零直接用于最后整块，丢失其完整有效长度。

必要事实：`applicable_contract`、`implementation_action`、`last_block_full_on_exact_division`、`zero_remainder_used_as_empty_tail`、`wrong_tail_length_consumed`。

排除事实：`zero_tail_means_no_allocated_block`、`full_last_block_length_preserved`、`compliant`、`contract_inapplicable`。

## CTL-ELIDE-01 · 快捷条件错误消去必需运算

父类：`control`；状态：`reviewed_definition`；分类启用：`True`。

输入属性满足部分identity条件但不满足全部语义前提时，旧快捷分支省略仍需执行的运算。

必要事实：`applicable_contract`、`implementation_action`、`operation_still_required_under_control`、`partial_identity_guard_elides_operation`、`elision_changes_target_result`。

排除事实：`operation_identity_for_all_relevant_controls`、`required_operation_executed_elsewhere`、`compliant`、`contract_inapplicable`。

## BUF-LIFE-01 · 活跃值在最后消费前被覆写

父类：`lifetime`；状态：`reviewed_definition`；分类启用：`True`。

同一缓冲区尚有必需消费者时被分配给另一值或提前覆写，使消费者读取了错误代内容。

必要事实：`applicable_contract`、`implementation_action`、`live_value_has_future_consumer`、`live_buffer_overwritten`、`overwritten_value_consumed`。

排除事实：`last_consumer_completed_before_reuse`、`buffers_do_not_alias`、`compliant`、`contract_inapplicable`。

## FORM-COEF-01 · 数学公式的必需系数或变换遗漏

父类：`formula`；状态：`reviewed_definition`；分类启用：`True`。

旧公式遗漏合同所要求的非中性系数或必要变换，在精确算术下也与目标函数不等价。

必要事实：`applicable_contract`、`implementation_action`、`exact_formula_contract`、`required_formula_term_missing`、`formula_inequivalent_on_valid_input`、`wrong_formula_consumed`。

排除事实：`formula_transformation_equivalent`、`difference_only_from_floating_rounding`、`compliant`、`contract_inapplicable`。

## VALID-DOMAIN-01 · 输入合法性校验使用错误语义域

父类：`validation`；状态：`reviewed_definition`；分类启用：`True`。

合法性应依据合同指定的逻辑或物理域，旧谓词改用不等价的另一域，造成错误拒绝或接受。

必要事实：`applicable_contract`、`implementation_action`、`validation_domain_contract`、`validation_uses_wrong_domain`、`wrong_domain_changes_acceptance`。

排除事实：`validation_domain_equivalent`、`input_rejection_required`、`compliant`、`contract_inapplicable`。

## REP-TRANS-01 · 显式数据重排映射违约

父类：`representation`；状态：`research_definition`；分类启用：`False`。

显式布局转换把已知源逻辑值写入不符合目标布局合同的位置或填充。

必要事实：`applicable_contract`、`implementation_action`、`layout_transform_contract`、`layout_transform_mapping_wrong`、`wrong_transformed_layout_consumed`。

排除事实：`layout_transform_correct`、`only_descriptor_wrong`、`compliant`、`contract_inapplicable`。

## SYNC-DET-01 · 规定确定性未被执行策略保持

父类：`synchronization`；状态：`research_definition`；分类启用：`False`。

在明确的确定性合同下，旧执行策略允许导致结果不一致的调度/原子配对自由度。

必要事实：`applicable_contract`、`implementation_action`、`determinism_required`、`nondeterministic_execution_source_bound`、`nondeterminism_violates_required_level`。

排除事实：`nondeterminism_permitted`、`difference_within_required_determinism_level`、`compliant`、`contract_inapplicable`。

## ADR-FLOAT-01 · 精确整数地址经浮点中转丢位

父类：`address`；状态：`research_definition`；分类启用：`False`。

要求精确保留的整数地址经不足有效位的浮点格式中转后再还原，丢位地址被消费。

必要事实：`applicable_contract`、`implementation_action`、`exact_integer_address_required`、`integer_float_roundtrip_loses_bits`、`distorted_address_consumed`。

排除事实：`integer_float_roundtrip_exact`、`integer_range_loss`、`compliant`、`contract_inapplicable`。

## CTL-COUNT-01 · 控制计数器表示范围失真

父类：`control`；状态：`research_definition`；分类启用：`False`。

循环或协议计数器在要求精确保留时超出整数表示范围，并改变控制流或完成条件。

必要事实：`applicable_contract`、`implementation_action`、`exact_control_count_required`、`control_count_range_loss`、`wrong_count_controls_execution`。

排除事实：`control_count_representable`、`count_is_only_address_offset`、`compliant`、`contract_inapplicable`。

## ADR-INT-01 · 整数地址表示范围不足

父类：`address`；状态：`reviewed_definition`；分类启用：`True`。

合法逻辑位置所需的精确整数地址量，在实际整数运算或转换中超出表示范围而失真，并被同一路径的地址消费者使用。

必要事实：`applicable_contract`、`implementation_action`、`exact_integer_address_required`、`actual_integer_type_bound`、`integer_range_loss`、`distorted_address_consumed`、`same_mapping_preserved_by_widening`。

排除事实：`address_contract_inapplicable`、`integer_representation_exact`、`float_mediated_address_rounding`、`damaged_address_not_consumed`、`mapping_error_survives_unbounded_integer_arithmetic`、`state_role_is_nonaddress_numeric_accumulation`、`compliant`、`contract_inapplicable`。
