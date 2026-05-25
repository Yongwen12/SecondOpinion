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
- [SecondOpinion MVP Design Notes](docs/secondopinion-mvp-design-notes.md)

## MVP 使用方式

当前 MVP 是一个本地可运行的 review audit 工具，先完成最小闭环：

1. 抓取 ICLR OpenReview submission 和 replies，完整保存 raw snapshot。
2. 从 raw snapshot 派生 normalized papers / reviews / rebuttals / decisions schema。
3. 从 review weaknesses 中抽取可审计 claim。
4. 用论文摘要、可扩展 PDF evidence chunks 和外部学术证据做 review-time evidence retrieval；author response 保留给 post-review / rebuttal guidance。
5. 输出 claim-level verdict、issue flags、Review Quality Score 和 Markdown / HTML 报告。

当前 claim extraction 使用 `claim-extraction-llm-v0.1`：LLM 负责从 review 原文中抽取、拆分和分类 claim，系统只做 deterministic validation。每条 claim 必须带 `source_field` 和可回指到原文的 `source_sentence`；匹配不到原文的 claim 会被丢弃。

当前 evidence retrieval 使用 `section-aware-bm25-v0.2`：review assessment 阶段只使用 review-time evidence，例如 abstract、PDF evidence chunks 和 appendix，不使用 author response、final decision 或后续修订来给 reviewer 打分。author response 只应进入 post-review / rebuttal guidance 阶段。retrieval 会按 claim 类型给 section 加权，并在报告中保留 page、section label 和 snippet。默认 verdict 仍使用 `rule-baseline-v0.1`，偏保守；打开 LLM judge 后会生成面向用户的 SecondOpinion take，并用统一 stance 展示 SecondOpinion 对 reviewer point 的态度：`strongly_disagree` / `disagree` / `mixed` / `agree` / `strongly_agree`。

下一版目标要求外部证据进入 review assessment 和 rebuttal guidance。对 novelty、related work、baseline、实验充分性、method validity 和 field norm 相关 claim，系统需要检索相关论文、venue guideline、benchmark/baseline convention 等外部材料；reviewer score 和 final decision 只能作为优先级和校准信号，不能当作 claim correctness 的 ground truth。

下一步重点：

1. 设计聪明、快速、省钱的外部证据路径：metadata-first 检索，先用论文标题、摘要、venue guideline 和 benchmark/baseline convention；只对高优先级或不确定 claim 下载全文、生成摘要，并缓存所有外部 evidence。
2. 做小规模专家标注：先选小几十篇论文，给专家展示 claim-level reviewer point，让他们用 1-5 分快速标注是否同意 reviewer 的实质性看法，并对 rebuttal usefulness 打分；第一阶段主要看 SecondOpinion stance 和专家分数的 correlation。

运行 audit 前需要设置 OpenAI API key：

```bash
export OPENAI_API_KEY="..."
```

默认走 cheap-first 策略：claim extraction、review point judge 和 annotation LLM labeler 都使用 `gpt-5-nano`，并对 GPT-5 系列默认设置 `SECONDOPINION_REASONING_EFFORT=minimal`。也可以用 `SECONDOPINION_CLAIM_MODEL` / `--claim-model`、`SECONDOPINION_JUDGE_MODEL` / `--judge-model` 或 `SECONDOPINION_ANNOTATION_MODEL` 覆盖。

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

这一步会下载 submission PDF，解析正文和 appendix，并把带有 page / section label / text 的 evidence chunks 加回 normalized dataset。PDF 文件和派生 evidence dataset 默认保存在 `data/pdfs/`、`data/derived/`，不会提交到 GitHub。

对归一化数据做审计：

```bash
PYTHONPATH=src python3 -m secondopinion audit --input data/normalized/iclr_2024_sample.json
```

打开 review point judge + RAG verdict：

```bash
PYTHONPATH=src python3 -m secondopinion audit \
  --input data/derived/iclr_2024_with_evidence.json \
  --llm-judge
```

如果已经构建 evidence store，可以直接审计派生数据：

```bash
PYTHONPATH=src python3 -m secondopinion audit --input data/derived/iclr_2024_with_evidence.json
```

`--llm-judge` 使用 `review-point-judge-v0.2`：LLM 不重新决定论文是否该 accept，而是判断单条 reviewer point 是否被 review-time evidence 支持。当前 review assessment 不使用 author response、final decision 或后续修订来给 reviewer 打分。每条 point 会记录 `review_point_type`、`stance`、`support_score`、`answer_coverage_score`、`question_value_score`、`second_opinion_take`、`quoted_manuscript_evidence`、`reasoning_summary`、`professionalism_score`、`specificity_score`、`helpfulness_score` 和 `fairness_score`。其中 `stance` 是主展示维度，表示 SecondOpinion 是否同意 reviewer point；其他分数保留给排序、调试和后续 calibration。如果调用失败，系统会保留 rule baseline verdict，并给 claim 加上 `llm-judge-failed` flag。

## 标注与校准

每次 audit run 都可以导出成标注任务包，用于人工标注、LLM 平行标注和一致性比较。

导出标注任务和静态 HTML：

```bash
PYTHONPATH=src python3 -m secondopinion annotation-export \
  --audit data/audits/audit_results.json
```

默认输出：

- `data/annotations/tasks/<run_id>.jsonl`
- `reports/annotations/<run_id>.html`

HTML 标注包默认不显示 LLM 标注结果。人工导出的 JSONL 可以先校验：

```bash
PYTHONPATH=src python3 -m secondopinion annotation-validate-labels \
  --labels data/annotations/labels/human/<run_id>.jsonl
```

生成独立的 LLM 平行标注：

```bash
PYTHONPATH=src python3 -m secondopinion annotation-llm-label \
  --tasks data/annotations/tasks/<run_id>.jsonl
```

比较 human labels 和 LLM labels：

```bash
PYTHONPATH=src python3 -m secondopinion annotation-compare \
  --tasks data/annotations/tasks/<run_id>.jsonl \
  --human data/annotations/labels/human/<run_id>.jsonl \
  --llm data/annotations/labels/llm/<run_id>.jsonl
```

第一阶段只预留 `venue_guideline`、`external_reference`、`field_consensus` 这些外部 evidence source type，不接实时外部搜索。

## Google Drive 数据存储

GitHub 只适合放代码、schema、文档和小样例。raw snapshot、PDF、derived evidence dataset、审计报告这些大文件可以放到 Google Drive for Desktop 的同步目录里。

先查看本机可用的 Drive 路径：

```bash
PYTHONPATH=src python3 -m secondopinion storage-info
```

然后设置 artifact 根目录：

```bash
export SECONDOPINION_STORAGE_ROOT="$HOME/Library/CloudStorage/GoogleDrive-<account>/My Drive/SecondOpinionData"
```

设置后，所有相对路径形式的 `data/...` 和 `reports/...` 都会自动读写到这个 Drive 根目录下。例如：

```bash
PYTHONPATH=src python3 -m secondopinion snapshot-iclr \
  --year 2024 \
  --limit 10 \
  --normalize-out data/normalized/iclr_2024_sample.json
```

实际会写入：

```text
$SECONDOPINION_STORAGE_ROOT/data/raw/...
$SECONDOPINION_STORAGE_ROOT/data/normalized/iclr_2024_sample.json
```

也可以不用环境变量，单次命令指定：

```bash
PYTHONPATH=src python3 -m secondopinion audit \
  --storage-root "$HOME/Library/CloudStorage/GoogleDrive-<account>/My Drive/SecondOpinionData" \
  --input data/derived/iclr_2024_with_evidence.json
```

绝对路径不会被改写，`examples/`、`docs/`、源码等仓库文件也不会被重定向。

数据原则：

- `data/raw/` 保留不同 venue 的原始结构，用于复现和重新派生。
- `data/normalized/` 才是跨 venue 统一 schema。
- `data/audits/` 和 `reports/` 是可重复生成的产物。
- 上述目录默认不提交 GitHub；仓库只提交代码、schema、文档和小样例。

## 目标

建立一个更透明、可解释、可审计的 review 质量评价机制，帮助作者、会议和社区理解 peer review 的质量问题。
