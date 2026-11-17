# MECH-v0.4 分类可靠性复算

此入口复用正式 MECH-v0.4 九卡和作用域裁决。它从原始 A 读出错误动作、下游、正常消费和未知边界，校验动作和因果关系并生成可复算图。首读是已开封家族开发回归。两轮冻结、锁定后由独立判卷者核对同一 A 与 B。[源码和因果判据](causal_relation_rules.md) · [判卷口径](scoring_rubric_v2.md)

以下命令从仓库的 `classification` 目录运行。设置 `RUN` 为单独的新目录，`A` 为本地受控的原始 A 路径。真实模型读件需要冻结配置使用的 Codex CLI。

```text
python -B -X utf8 -m reliability_v04.workflow freeze RUN A
python -B -X utf8 -m reliability_v04.workflow read RUN 1
python -B -X utf8 -m reliability_v04.workflow read RUN 2
python -B -X utf8 -m reliability_v04.workflow lock RUN
python -B -X utf8 -m reliability_v04.workflow verify RUN
```

若读件请求失败，应保留原始记录。追加尝试时使用 `--attempt 2`，锁定时用 `--attempts 1 2` 声明两轮实际接受的尝试。两轮只共享 A、目录、提示和 schema。冻结记录绑定精确原件字节与执行版本。

判卷文件使用与 `scoring.review_schema()` 相同的动作及漏项结构，另带 `judge_id`、`round`、`lock_sha256`、`graph_sha256` 和 `answer_sha256`。也可由独立判卷执行上下文用 `python -B -X utf8 -m reliability_v04.scoring judge RUN B 1 JUDGE_DIR` 生成机器可复核的结构。给原参考与审计修订分别运行评分，引用各自的摘要和逐案矩阵。

```text
python -B -X utf8 -m reliability_v04.scoring score RUN B SCORE REVIEW1 REVIEW2
python -B -X utf8 -m reliability_v04.scoring matrix SCORE MATRIX
```

程序回归从仓库根目录运行 `python -B -X utf8 -m unittest discover -s classification -p test_reliability_v04.py`。正式 F 在本轮开发回归结束后单独评估，使用新家族、实际访问隔离和可核验保全。

2026-11-17 的原 A 稳定性复验记录了因果修订基线、三个候选的双轮成绩、证据差异和当前 F 状态。[稳定性复验](STABILITY_REPORT.md) · [冻结与成绩摘要](STABILITY_RUNS.json)

MECH-v0.4.1 的开发复验记录了数值上位、独立根修订、双轮冻结成绩和公开测试入口。[开发复验报告](V041_REVALIDATION_REPORT.md)
