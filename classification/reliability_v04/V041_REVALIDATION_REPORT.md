# MECH-v0.4.1 开发复验报告

2026-11-17。复验使用 MECH-v0.4 正式九卡。开发判定版本为 `0.4.2`，可靠性演练协议为 `mech_v04_reliability_exercise/0.3`。

| 阶段 | 版本 | 用途 |
| --- | --- | --- |
| 公开交付基线 | `2db0b04a564dc8bff2e66cee2b20bf9889a4c7b8` | 上轮稳定性报告和公开历史 |
| 本地对照引擎 | `dea1d10ccfe8a23f71cba6d420d4a8bf26f6ad54` | 上轮双读和原始评分 |
| 本地双读引擎 | `cdf0488fed34b78db725cdf13393645397413f96` | 在两个新上下文读取同一个原 A |
| 本地最终引擎 | `1997e9486197e2efc8bc41feceb68c50865a1369` | 修正重叠引文导致的重复计根，回放两轮锁定事实 |

## Work 复核

Work 核对冻结提示，复算原 B 与同 A 范围审计，分别检查版本、具体错误动作、机理层级、因果关系和独立根。ARM64Tokenizer 的原件足以证明局部填充掩码错误，实际注意力消费缺少绑定。同 A 范围审计因此核准一处局部根。ORT 的接口级 L1 及对应根仍是两轮漏项。

Work 建立 18 项机理层级合成对照，最终全部达标，并补了三项重叠引文对照。同一操作用两种重叠引文窗口重复描述时，两项负控均从两根修正到一根，独立边均被拒绝。两处旧实现各有决定性证据时，即使共享报告位置，正控仍保留两根。 [层级对照与夹具](validation_0_4_1/run_parent_leaf_regression.py) · [重叠引文对照](validation_0_4_1/reproduce_overlapping_roots.py)

## Codex 实现

- 数值上位 `numerical_evaluation` 要求合同、实际实现动作、数值求值违约、参与项保持和失真值实际消费在同一范围内成立。NUM-01 与 NUM-02 继续使用各自的叶级证据，归约前平方溢出按首错边界处理。读件 schema 注册已有的上位事实，冻结记录绑定实际执行的分类依赖和版本。 [分类规则](../mech_v04/classifier.py) · [读件 schema](reader.py) · [执行冻结](workflow.py)
- 独立关系检查两处旧实现的各自证据。同一动作的重述保存在图中并标注归属，计根和评分使用归并后的动作。下游关系和有据的独立边回到该动作，局部下游机理继续出现在图中。 [动作图](graph.py) · [评分](scoring.py) · [分类单测](../test_mech_v04.py) · [动作图单测](../test_reliability_v04.py)

## 双轮成绩

两轮使用已见的原 A 和同一渲染提示，各自以新上下文读完 13 个家族并锁定，再由 Work 判卷。表中每格按第一轮、第二轮排列。

| 指标 | 上轮 `dea1d10` | 本轮 `cdf0488` |
| --- | --- | --- |
| 有据机理，原 B | 10/14、10/14 | 10/14、9/14 |
| 有据叶级，原 B | 3/6、3/6 | 3/6、3/6 |
| 具体错误动作 | 11/11、11/11 | 11/11、11/11 |
| 语义失效关系，原 B | 10/11、10/11 | 10/11、10/11 |
| 因果关系 | 13/14、13/14 | 13/14、13/14 |
| 核准独立根，原 B | 9/11、9/11 | 9/11、9/11 |
| 核准独立根，同 A 范围审计 | 10/11、10/11 | 10/11、10/11 |
| 严格完整案，原 B | 9/13、9/13 | 9/13、8/13 |

本轮每轮声称 10 根。原 B 每轮误计 1 根、漏 2 根，同 A 审计每轮误计 0 根、漏 1 根。原 B 与同 A 审计的有据机理和完整案成绩一致。同 A 审计的语义失效关系为两轮各 11/11。

MIGraphX 两轮均有据归入数值上位并计一根。旧 GPU 路径的实际同工作精度仍缺绑定，原 B 的 NUM-02 叶级分仍缺。RotaryEmbedding 第二轮对同一实现同时提交参数违约和目录外主张，最终输出目录外，导致有据机理和完整案各失一分。诊断副本撤去重复主张后恢复参数上位和一根，表中保留原锁成绩。Qwen 的 C3、ggml 的 NUM-01 及 GridSampler 的两个独立根在两轮均保留。 [上轮逐案摘要](STABILITY_REPORT.md)

最终引擎与本提交的公开代码分别回放 `cdf0488` 两轮的锁定事实。每轮 13 个完整判决图均与原图一致，每轮声称根数均为 10。此处复验对象为确定性程序判定，双轮读件成绩取自 `cdf0488` 的原锁。

## 复算入口

在公开检出运行以下命令可复验程序和合成对照。可靠性与评分 30 项、跨版本 5 项、正式流程和注入接口 9 项、诊断兼容 17 项全部通过。Work 合成对照为 18/18 和 3/3。

```sh
python -B -X utf8 -m unittest discover -s classification -p 'test_reliability*.py'
python -B -X utf8 -m unittest discover -s classification -p 'test_mech_v04_cross_version.py'
python -B -X utf8 -m unittest discover -s diagnosis_mvp -p 'test_*.py'
python -B -X utf8 classification/reliability_v04/validation_0_4_1/run_parent_leaf_regression.py .
python -B -X utf8 classification/reliability_v04/validation_0_4_1/reproduce_overlapping_roots.py .
cd classification
python -B -X utf8 -m unittest test_mech_v04.FWorkflowTest test_mech_v04_injection
```

最终候选在含本地归档的独立检出运行 `python -B -X utf8 -m unittest discover -s classification -p 'test_*.py'`，155 项分类测试全通过。公开检出直接运行同一全量命令时有 131 项通过，另有 24 项因缺本地夹具报 `FileNotFoundError`。历史正式冻结按公开基线 `2db0b04` 的 `0.4.1` 实现校验。

正式 F 状态为 `BLOCKED`，待建立可验证的访问隔离和独立见证。本轮双读按开发演练登记。原件、答案、原始读件与判卷记录及 F 预筛材料均保存在本地。
