# 算子精度故障模式库工程状态

2026-11-15，北京时间｜本轮项目事实及同步条件

## 项目与目录

- **工程执行**在本地 Codex 项目「精度」，实际根目录为 `D:\project\精度`。应用登记中，本 Work 与「算子精度故障诊断链」都属于该本地项目。源码、测试、证据和既有聊天继续在原处使用。
- **研究接手**使用 ChatGPT Project `fault_pattern`。应用清单另有一个同名本地项目，位置是 `C:\Users\86152\Documents\ChatGPT\fault_pattern`。接手时选择 ChatGPT Project；涉及本地文件的任务以「精度」根目录为准。
- 本轮交接引用既有 P0 报告。该报告复核 SHA-256 为 `81d84022200eb66b91ca0430f22fded5a502b6024f61fe15375630f2370b83c7`。下表和文末链接给出本地证据位置。[P0–P1 审查原报告](<../算子精度故障模式库_P0-P1设计审查_20261115.md>)

## Git 检出和固定来源

| 位置或资产 | 已核实版本及状态 |
| --- | --- |
| 工程根及 FaultAudit 源码根 | 工程根和 `fault-evidence-audit-codex-initial-public-release` 都没有项目级 `.git`。根目录的 `handoff/` 在两个工作树的跟踪范围之外。 |
| [FaultAudit 0.1.3 发布检出](<../fault-evidence-audit-codex-initial-public-release/work/publish/github-v013-net>) | 分支 `codex/initial-public-release`，`9d947633fa9c0e06ee7e74772ef4890601d31150`，54 个跟踪文件，工作树干净。fetch、push 的 `origin` 均指向下列公开 FaultAudit 仓。 |
| [CANN25_review 检出](<../CANN25_review>) | `main@edb8c4f8913f3e419e9b360350548ccc961a87e0`，939 个跟踪文件，工作树干净。这里无远端配置。另有 25 份拆分单案报告。 |
| 本地 0.1.21 源码快照 | `16ce36aa427d0ccc7d6b3d93d59d33d28907ceb8` 对应的快照没有 Git 元数据。P0 将 50 个核心 Python 文件和 4 个选查测试逐一重算对象哈希，均和 `510601f` 固定树一致。原 42、V4 及清单的 3 个对象也一致。[0.1.21 清单](<../fault-evidence-audit-codex-initial-public-release/work/update_check_16ce36a/remote_sources.json>) · [P0–P1 审查原报告](<../算子精度故障模式库_P0-P1设计审查_20261115.md>) |
| 固定研究基线 | `510601f887f8ad174335f617a9d7e2a808ff897f`。P0 在项目内的 29 个 Git 对象库中未找到其提交。本轮从 GitHub 核实研究分支仍指向该 SHA。固定提交的父提交为 `16ce36aa427d0ccc7d6b3d93d59d33d28907ceb8`。[本地研究入口](<../fault-evidence-audit-codex-initial-public-release/work/classification_research_20261114/rule_review_510601f/research/README.md>) · [固定提交](https://github.com/spike677/fault-evidence-audit/commit/510601f887f8ad174335f617a9d7e2a808ff897f) |

## GitHub 接入状态

- **当前公开源可读。** 本 Work 的 GitHub 连接已读取仓库元数据、分支及固定提交。公开仓 `spike677/fault-evidence-audit` 的默认分支 `codex/investigation-plan` 当前指向 `510601f887f8ad174335f617a9d7e2a808ff897f`。本地发布检出的 `origin/codex/initial-public-release` 是旧跟踪引用，虽然本地比对为 0 领先、0 落后，GitHub 当前分支列表仅列研究分支，查询旧分支返回 404。发布提交 `9d947633fa9c0e06ee7e74772ef4890601d31150` 本身仍可按 SHA 读取。 [仓库](https://github.com/spike677/fault-evidence-audit) · [研究分支](https://github.com/spike677/fault-evidence-audit/tree/codex/investigation-plan) · [0.1.3 发布提交](https://github.com/spike677/fault-evidence-audit/commit/9d947633fa9c0e06ee7e74772ef4890601d31150)
- **私有交接目标待确认。** CANN25 历史发布清单指向 `spike677/vllm_ascend_op_fi`。当前 GitHub 连接读该仓元数据返回 404，现有清单无法证明仓库状态、可见性或上传授权。私有仓库、接收范围及 `fault_pattern` 内的实际读取能力仍需按选定目标核实。[25 份单案历史发布清单](<../CANN25_25_review_reports_manifest.json>) · [历史打包清单](<../CANN25_publish_manifest.json>)
- **当前成果可供内容审阅。** 后续同步应使用获批目标仓的工作树和逐件文件清单，以完整提交 SHA 记录交接版本。工程根为本地目录，不能靠现有两个检出的提交把 `handoff/` 自动纳入。

## 材料处理范围

| 资料 | 当前处置 |
| --- | --- |
| 四份交接 Markdown | 可优先做发布审阅。内容采用结论摘要、版本和证据定位。外发版还应审阅本机路径、历史仓名、案例身份及引用的可见范围。 |
| 自有源码、测试、合成示例 | 按发布许可和实际文件内容逐件审阅。0.1.3 已有证据台账、测试和合成示例的发布示范，源码树和快照身份各自保留。 |
| 真实证据和历史资料 | 原始表的固定版本已查到内网 Wiki 与工单引用。CANN25 的资料目录含保存的页面和评审记录。原始工作簿、来源回执、内网链接、客户和运行记录、运行数据库、缓存原文及发布辅助脚本都列入审批范围，优先用经批准的脱敏摘要。 |
| 凭据初筛 | 对两个本地检出已跟踪的文本做了路径级模式筛查，检查私钥标记、常见 GitHub 和 AWS 凭据形态，筛查无命中。检查范围是这两个 Git HEAD 的所选文本，逐文件合规和完整敏感信息审查待随明确的同步清单完成。 |

本轮的 GitHub 操作为只读查询。同步和授权所需的文件选择、目标核实和跨入口对读步骤见 [接手计划](./NEXT_TASKS.md)。分类与验证事实分别见 [分类设计](./CLASSIFICATION_DESIGN.md)、[检查记录](./WORK_REVIEW.md)。
