# SecondOpinion

SecondOpinion 是一个面向计算机领域论文评审的第三方 review 质量评估项目。

## 背景

CS 领域很多作者在投稿后会觉得 OpenReview 上收到的 review 不够公平、不够专业，或者语气不够友好。但目前缺少一个独立机制来系统性评价 review 本身。

因为大量会议的论文、review、rebuttal 和 decision 都集中在 OpenReview 上，本项目希望基于这些数据建立一个可解释、可审计的 review audit 系统。

## 核心想法

本项目不是让 AI 重新决定论文该不该接收，也不是重新写一篇 review，而是评估已有 reviewer 的意见质量。

系统会把 review 中的关键批评拆成具体 claim，定位这些 claim 在论文中的相关证据，然后评价这条 review 是否：

- 专业
- 具体
- 有论文证据支持
- 建设性强
- 语气友好、职业
- review 分数和文字评价一致

## 关键问题

1. 如何用 OpenReview 官方 API 抓取论文、review、评分、评论和 decision，并自动更新。
2. 如何设计可信的 AI 评分机制，而不是让模型凭感觉打分。
3. 是否需要结合 RAG，让 AI 基于论文正文、review 原文和 venue review guideline 进行证据化判断。
4. 如何用人工标注校准 AI，让评分标准有信服力。

## 标注思路

推荐采用 review-level 和 claim-level 的混合标注。

Review-level 关注整条 review 的总体质量：

- 专业度
- 具体性
- 建设性
- 友好度
- 分数一致性
- 总体 review quality

Claim-level 关注 reviewer 的具体批评是否成立：

- claim 类型，例如实验、理论、novelty、writing、related work
- 是否具体
- 是否有论文证据支持
- 是否与论文内容矛盾
- 严重程度
- 是否可操作

## MVP

第一版可以先支持一个公开 OpenReview venue，例如 ICLR。

MVP 输出：

- 每条 review 的专业度分
- 每条 review 的友好度分
- review 中的关键 claim
- 每个 claim 对应的论文证据
- review 分数和文字是否一致
- 简短解释

## 项目文件

- [P0 ICLR Review Audit Project Plan](docs/P0%20Iclr%20Review%20Audit%20Project%20Plan.docx)

## MVP 使用方式

当前 MVP 是一个本地可运行的 review audit 工具，先完成最小闭环：

1. 抓取 ICLR OpenReview submission 和 replies，完整保存 raw snapshot。
2. 从 raw snapshot 派生 normalized papers / reviews / rebuttals / decisions schema。
3. 从 review weaknesses 中抽取可审计 claim。
4. 用论文摘要、author response 和可扩展 paper sections 做轻量 evidence retrieval。
5. 输出 claim-level verdict、issue flags、Review Quality Score 和 Markdown / HTML 报告。

先跑内置样例：

```bash
PYTHONPATH=src python3 -m secondopinion demo
```

生成结果：

- `data/audits/demo_audit_results.json`
- `reports/mvp_demo.md`
- `reports/mvp_demo.html`

抓取少量 ICLR 2024 公开数据并归一化：

```bash
PYTHONPATH=src python3 -m secondopinion snapshot-iclr \
  --year 2024 \
  --limit 10 \
  --normalize-out data/normalized/iclr_2024_sample.json
```

raw snapshot 会保存在类似下面的目录：

```text
data/raw/openreview/iclr/2024/20260518T120000Z/
```

每个 snapshot 包含：

- `manifest.json`：记录 source、venue、year、API query、paper/reply 数量和 raw page 文件列表。
- `notes_page_0000.json`：OpenReview API 的完整分页响应，不删除字段。

也可以从已有 snapshot 重新派生 normalized 数据：

```bash
PYTHONPATH=src python3 -m secondopinion normalize-snapshot \
  --snapshot data/raw/openreview/iclr/2024/<snapshot_id> \
  --out data/normalized/iclr_2024_sample.json
```

构建 PDF evidence store：

```bash
PYTHONPATH=src python3 -m secondopinion build-evidence-store \
  --input data/normalized/iclr_2024_sample.json \
  --out data/derived/iclr_2024_with_evidence.json \
  --limit 10
```

这一步会下载 submission PDF，解析正文和 appendix，并把 page / section / text chunks 加回 normalized dataset。PDF 文件和派生 evidence dataset 默认保存在 `data/pdfs/`、`data/derived/`，不会提交到 GitHub。

对归一化数据做审计：

```bash
PYTHONPATH=src python3 -m secondopinion audit --input data/normalized/iclr_2024_sample.json
```

如果已经构建 evidence store，可以直接审计派生数据：

```bash
PYTHONPATH=src python3 -m secondopinion audit --input data/derived/iclr_2024_with_evidence.json
```

本版先使用 `rule-baseline-v0.1`，重点是验证数据链路、schema、rubric 和报告格式。后续可以把 claim extraction、evidence retrieval 和 verdict 分类替换为 LLM + RAG 实现。

数据原则：

- `data/raw/` 保留不同 venue 的原始结构，用于复现和重新派生。
- `data/normalized/` 才是跨 venue 统一 schema。
- `data/audits/` 和 `reports/` 是可重复生成的产物。
- 上述目录默认不提交 GitHub；仓库只提交代码、schema、文档和小样例。

## 目标

建立一个更透明、可解释、可审计的 review 质量评价机制，帮助作者、会议和社区理解 peer review 的质量问题。
