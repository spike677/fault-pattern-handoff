# MECH-v0.4 发布与复算

| 变化 | 版本与兼容范围 |
| --- | --- |
| 机理目录 | `MECH-v0.3` 的七个 ID 与卡片内容原样继承。正式命名空间 `MECH-v0.4` 增加 `NUM-01`、`NUM-02`。 |
| 读件 | v0.4.2 三段提示新增明确的证明与旁证范围说明。实际提示、响应结构和执行配置由 `F_FREEZE.json` 绑定。 |
| 裁决 | 正式入口 `classification/mech_v04/classifier.py` 使用 `0.4.1`。作用域内的锚点本身足以证明事实时，经过核引的异版材料单列为旁证。 |
| 事实包 | 继续使用 `classification_facts/0.3.1`。使用未绑定引证的更旧事实应从冻结原件重新提取，原档可用其历史程序复算。 |
| 评分 | 协议仍为 `classification_only/0.3.1`。以声明的目录、裁决版本、双轮锁定输出和判卷口径评分。旧成绩及报告继续指向各自的冻结版本。 |

已审核的窄状态案例 E06、N501 在正式目录下判 NUM-01。原始矩差链条已证明的 G05、N502 判 NUM-02。首错在单项平方处的 N503 和 V406 保留已证目录外。旧结果按其当时可用的目录解释。[九条模式及测试映射](../mech_v04/MODE_CARDS.md) · [迁移表](../mech_v04/migration_from_v03.json) · [两个数值模式的准入](../mech_v04/ADMISSION_REVIEW.md)

## 公开复算

需要 Git 和 Python 3.10 或更新版本。公开入口核验文件哈希、九条目录、冻结、跨版本判据、合成双轮评分、九项离线注入和诊断兼容。以下命令也适用于已有网络检出的仓库根目录，或解压后的源码包根目录。

```text
git -c core.autocrlf=false clone -b codex/mechanism-classification-pilot https://github.com/spike677/fault-pattern-handoff.git mech-v04
cd mech-v04
python -B -X utf8 classification/release/verify.py
```

也可从发布离线包检出。两种包均固定在 `MECH-v0.4` 标签的内容提交上。

```text
git -c core.autocrlf=false clone -b codex/mechanism-classification-pilot MECH-v0.4-release.bundle mech-v04
cd mech-v04
python -B -X utf8 classification/release/verify.py
python -B -X utf8 classification/mech_v04/classifier.py --help
python -B -X utf8 classification/mech_v04/evaluation.py --help
```

## 受控复算

拥有受控包的执行者可解压后运行 `python -B -X utf8 verify.py replay-logs`。它从包内 Git bundle 全新克隆，回放完整测试、历史分、Work 原始双轮捕获与封存分、正式准入五案、P0 定向对照。成绩复算使用锁定答卷。新模型首读另按正式独立评估流程执行。原始 A/B、逐案预测和完整日志保存在受控包。公开发布由试点历史上的脱敏提交和单独清单组成，受控 bundle 保留两个本地源提交的真实祖先链。[公开验收汇总](TEST_RESULTS.json) · [独立评估准备](../mech_v04/F_PREPARATION.md)
