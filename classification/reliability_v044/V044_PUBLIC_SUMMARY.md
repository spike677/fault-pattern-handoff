# MECH-v0.4.4 公开审查与复验摘要

日期：2026-11-17。程序基线：`5d4f21872af5776ebabbb331ec6696892f1f0f74`。

本轮完成整数地址候选审查、MIGraphX 证据边界审查和历史成绩收尾，F 已形成材料
草包及访问预检，正式执行仍 **BLOCKED**。本轮没有修改九条正式目录、分类器
或读件提示，没有新增独立模型读件或 GPU 算子执行，不产生新的泛化准确率。

## 四项交付

| 工作包 | 状态 | 结果及边界 |
| --- | --- | --- |
| 整数地址表示范围 | DECIDED / NEW_CANDIDATE | 三个开发暴露家族、四动作；18 算术控制与 18 固定源码断言通过。正式准入 0 |
| MIGraphX 工作精度 | CLOSED | 保留 numerical_evaluation 上位；NUM-02 叶级 NOT_VERIFIED，实际 GPU 执行 NOT_TESTED |
| 历史可靠性基线 | FROZEN | 36 成绩行、9 批次、235 动作对账行；18 条本地复算命令通过，294 个历史输入哈希未变 |
| F 准备 | BLOCKED | 24 条入池筛出 20 候选、241 个原件视图；参考答案尚未审定，模型通道和独立见证未完成 |

整数地址的共同问题是合法坐标所需的精确整数关系在到达地址消费者前失真，
与单位换算、连续布局误用及浮点状态窄化分别比较。候选定义、已核边界与
正式准入限制见 [候选卡](../candidate_reviews/integer_address_range/MODE_CARD_CANDIDATE.md)
和 [审查摘要](../candidate_reviews/integer_address_range/REVIEW_PUBLIC_SUMMARY.md)。

MIGraphX 已追至固定旧版的 lowering、JIT、归约调度、类型传播及归一化消费者。
14 个源文件、23 个锚点及 5 个 CPU 算术对照构成 63 项检查。缺少同次故障运行
绑定的最终 IR、生成内核、设备与编译参数，不能据此确认实际 GPU 全程工作精度。
[MIGraphX 审查摘要](../candidate_reviews/migraphx_num02/REVIEW_PUBLIC_SUMMARY.md)

## 历史成绩保持原口径

| 批次 | 两轮严格成绩 | 用途 |
| --- | --- | --- |
| 原始 13 案 | 2/13、2/13 | 原封存基线 |
| dea1d10 最终提示 | 9/13、9/13 | 提示开发回归 |
| cdf0488 后续复验 | 9/13、8/13 | 开发复验 |
| Benchmark-01 | 8/10、7/10 | 同案方法比较 |
| Benchmark-02 | 6/6、6/6 | 四个旧家族与两个同族控制的定向回放 |

各批次、原 B、同 A 作用域审计和补证成绩分别登记；不能合并分母，也不能用
Benchmark-02 替代 13 案成绩。程序动作身份、语义接纳根数及严格完整案指标
分别记录。ORT 的原材料缺证与补证 L1 分列；RotaryEmbedding 同据重复主张
归并与不同来源的竞争主张分开验证。正常下游消费不新增错误动作。

历史 FROZEN 表示来源与口径固定，并不表示所有旧参考答案都已被证明正确。
原件、答案、逐案事实/预测、动作对账和完整运行日志继续本地保管；公开仓库
能够复算下列算术控制及代码回归，不能单独复算依赖私有材料的全部历史成绩。

## F 准备的实际边界

排除清单保留全部 424 个开发暴露键并补至 441 个。20 个候选已保存 A 草包和
B 整理草案；10 条源材料待复核，10 条还需证据审查。**正式参考答案 0、正式
封存 0、新模型读件 0、预测 0、F 判卷 0。** 候选数不等于合格或已验证样本数。

Windows/WSL 宿主直接执行可读答案哨兵、历史答案和旧预测，隔离不合格。
本地 Docker 非特权双轮 shell 预检通过：三项合成哨兵拒读，真实答案和另一轮
输出未挂载，A 与必要代码只读。路径未挂载和权限拒绝分别记录。

F 仍需逐案参考审定、模型/权重/配置冻结、实际模型工具通道隔离，以及独立
答案保管和见证。当前整理者接触 B，不能兼任正式首读。shell 预检不能代替
这些条件。F 候选身份、材料、参考草案、排除谱系和访问日志均未包含在本提交。

## 公开复算

在仓库根目录使用 Python 3.10+：

冻结入口按文件原字节验哈希，检出时须保留 Git 中的 LF。Windows 可使用
`git -c core.autocrlf=false clone ...`。发布前的首次 Windows 检出曾因系统
`core.autocrlf=true` 改写四份冻结提示/结构文件而失败；核对 Git blob 与冻结
哈希一致后，仅恢复独立发布目录的原始字节，再复验。未修改冻结定义或内容。

```sh
python -B -X utf8 classification/reliability_v044/public_controls.py --verify
python -B -X utf8 -m unittest discover -s classification -p "test_reliability*.py"
python -B -X utf8 -m unittest discover -s classification -p "test_reviewed_static.py"
```

公开控制保留本地审核使用的纯算术函数：18 个整数情形、5 个方差情形和 7 条
方差断言。其输出与本地既有控制逐项一致。期望分类文字是审查注释，脚本没有
调用分类器或模型，也不模拟实际 GPU 内核选择，不应作为分类准确率。

[公开验证记录](PUBLIC_VALIDATION.json) 给出发布文件摘要、公开复算结果和
本地审计聚合结果。完整本地审计 manifest 的 SHA-256 为
`ade9d2a20a45c6687c491a49d0a03dd707b408b3058fcd731ddc0c2137f59d38`。
本提交只公开审查摘要、候选定义、可移植算术控制和聚合验证记录，不扩大正式目录。
