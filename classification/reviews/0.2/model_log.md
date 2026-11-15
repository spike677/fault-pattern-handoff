# 七卡语义轻量复核执行记录

当前 Work 对目录 0.2 的七张既有候选卡做了一次语义复核。复核材料为已见开发证据。

## 实际输入

- `classification/MODE_REVIEW.md`。读取判定流程、五问及输出要求。
- `classification/catalog.json`。读取目录 0.2、分类单位、证据约定及七张卡片的定义与近邻。
- `classification/reviews/0.2/input.json`。读取七个候选的作用域、所有案件摘录以及四份外部片段。外部片段为 `fp-b16` 的 FP-B16.md、`evidence-discipline` 的 EVIDENCE_DISCIPLINE.md、`issue-analysis` 的 README.md 和 `cannbot` 的归档 README.md。片段的原件起始行和版本随输入记录。

## 实际工具活动

- 在交接目录内用 PowerShell 以 UTF-8 读取上述三个文件。
- 在工具会话内解析已读取的 JSON，逐来源展示视图行号。当前模型根据摘录与目录作出每张卡的语义判断，然后从同一视图抽取逐字引文。
- 在内存中核对七条记录、三十五个问题、53 个问答及证据条目、125 条逐字引文的视图范围、来源 ID 和版本。
- 用 PowerShell 将两份结果写为 UTF-8。此次复核未读取旧结论、测试、其他模型意见或留置材料，未访问原件 URL，未执行验证器或运行算子。

## 结论范围

EmbeddingBag 两卡、Concat、ForeachLerpList 及 PadV3Grad 的证据为当前材料支持的静态或条件性结论。PyPTO 与 SGLang 记录作者报告的具体作用域。PadV3Grad 的条件推导仍待绑定到合法实参，SGLang 的摘录支持规约组合的超重数，单阶段的职责归属待核。全部七条为建议，目录状态继续保持候选。独立验证待完成。
