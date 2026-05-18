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

## 目标

建立一个更透明、可解释、可审计的 review 质量评价机制，帮助作者、会议和社区理解 peer review 的质量问题。
