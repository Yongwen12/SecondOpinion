# SecondOpinion 趣味性增强规格 v0.2

Date: 2026-06-17
Status: Draft — 拟并入 `reviewer_score_social_design` 第 4 节(Social Layer)之后,作为新的「趣味层 / Fun Layer」章节。

本规格在不改动后端六维评分的前提下,新增三个纯前端的确定性派生层:**称号(Archetype)**、**卡片正面布局**、**情绪反应(Reactions)**,外加一个可选的**段位(Tier)**层。目标是把「六个数字」变成有记忆点、可截图、可共鸣的社交内容。

设计原则(承接 v0.1 第 7 节安全边界):
- **对事不对人**:所有称号、段位、文案评的是「评论」,不是「人」。
- **正面可放飞,负面须自嘲**:正向人设可俏皮;负向人设必须中性/自嘲,不出现人身贬义词。
- **确定性**:同一 `paper_id + reviewer_id`、comments 不变时,称号/段位/avatar 完全可复现。
- **假名 paper-scoped**:任何派生内容不得包含可反推真实身份的信息。

---

## 1. 称号 / Archetype 层

### 1.1 输入

六维分数(0–100,前端 public 命名):

```text
specificity, evidence, actionability, agreement, rebuttal_robustness, tone
```

### 1.2 阈值定义

```text
HIGH  >= 80
MID   60–79
LOW   < 60
```

### 1.3 映射规则(按优先级从上到下匹配,命中即停止)

确定性:规则**有序**,取第一条命中的;全部未命中则落到默认档 `#9`。这样保证同一输入唯一输出。

| # | 触发条件 | emoji | 称号(中) | 称号(英) | 一句人设签名 |
|---|----------|-------|-----------|-----------|--------------|
| 1 | specificity≥80 且 actionability≥80 且 evidence≥80 | 🦅 | 实干派 | The Operator | 给得出、改得动、有依据 |
| 2 | evidence≥80 且 rebuttal_robustness≥80 | 🔬 | 较真党 | The Rigorist | 证据扎实,rebuttal 也打不动 |
| 3 | actionability≥80 且 specificity≥80(未命中 1) | 🔧 | 路线指引 | The Guide | 明确告诉你下一步做什么 |
| 4 | tone≥80 且 evidence<60 | 😇 | 嘴甜话空 | The Sweet Cloud | 语气很好,就是没说到点上 |
| 5 | tone<60 且 evidence≥80 | 🌶️ | 刀子嘴实心 | The Hot Take | 话不好听,但说得对 |
| 6 | specificity<60 且(tone<60 或 actionability<60) | ⚡ | 雷声大雨点小 | Vague Thunder | 气势很足,落点模糊 |
| 7 | agreement<60 且 evidence≥80 | 🧭 | 独行侦察 | The Outlier | 和别人不一样,但有据可循(低分≠错) |
| 8 | actionability<60 且 specificity<60 且 evidence<60 | 🌫️ | 飘过型 | The Drifter | 看过了,但没留下什么 |
| 9 | 默认(以上均未命中) | 🐢 | 稳健中庸 | The Steady | 各项都还行,没有明显短板 |

实现要点:
- 规则表以**数据**形式存放(JSON/常量),便于调参,不写死在组件里。
- `#7` 的签名必须显式写出「低分≠错」,呼应 v0.1 决策中 `agreement` 单向语义的澄清。
- 负向档(#4/#6/#8)文案一律自嘲化,**禁止**出现「懒」「差」「水货」等人身贬义词。已淘汰示例:`Lazy Rejector`。

---

## 2. 段位 / Tier 层(可选,M2+)

在 0–100 裸分之外叠一层柔性外壳,降低「给真人打 28 分」的攻击感。

| 区间 | Tier | 标签(中) |
|------|------|-----------|
| 85–100 | S | 良心审稿 |
| 70–84 | A | 靠谱审稿 |
| 55–69 | B | 中规中矩 |
| 40–54 | C | 略显敷衍 |
| 0–39 | D | 有待走心 |

- 主卡片展示 **Tier + 分数**(如 `S · 91`),Tier 给情感,分数给精度。
- 最低档文案用「有待走心」而非「摆烂」,保持对事不对人。
- Tier 仅为展示层,**不参与** `rank_score` 计算。

---

## 3. 情绪反应 / Reactions 层

替代干巴巴的 Like/Dislike,改为共鸣式情绪标签——「我也遇到过这种审稿人」比「点踩」更克制、更易引发社区认同,且语义指向「评论体验」而非「攻击真人」。

固定反应集(MVP 四个):

| key | emoji | 文案 | 计入排名方向 |
|-----|-------|------|--------------|
| `helpful` | 👏 | 这才是好审稿 | + 正向 |
| `same` | 😤 | 我也被这样审过 | 0 中性(纯共鸣) |
| `classic_r2` | 😂 | 经典 Reviewer 2 | − 负向 |
| `confusing` | 🌫️ | 没看懂在说什么 | − 负向 |

排名映射(替换 v0.1 第 4.2 节的 upvotes/downvotes 口径,公式结构不变):

```text
social_vote_score = normalized( (helpful) - (classic_r2 + confusing) )
engagement_score  = log(helpful + same + classic_r2 + confusing + 1)
```

- `same` 不计入正负,只计入 engagement——它是社区共鸣信号,不应左右好坏排名。
- 防刷:MVP 用 localStorage 防本地重复(承接 v0.1 M3);**榜单/排名上线(M4)前必须接 session 去重**,且 `engagement_score` 设上限,避免对冲刷量虚抬排名(承接上一轮决策 B)。

向后兼容:旧 `upvotes/downvotes` 字段可由 `helpful` / (`classic_r2`+`confusing`) 派生,前端对象保留聚合数。

---

## 4. 卡片正面布局

把「金句 + 称号」提为视觉主角,六维数字下沉到详情页。

### 4.1 列表卡(Reputation Board)

```text
┌────────────────────────────────────────────┐
│ [pixel]  🦅 实干派 · Baseline Hawk      S·91 │
│          “Please compare against a standard  │
│           retrieval baseline and report      │
│           runtime.”                          │
│                                              │
│  👏 128   😤 34   😂 9   🌫️ 3        [分享↗] │
└────────────────────────────────────────────┘
```

层级:emoji+称号(主)→ 假名(次)→ Tier·分数(右上角)→ 代表性金句(正面主角)→ 反应条 → 分享。

### 4.2 详情卡(点击展开)

```text
[pixel]  🦅 实干派 · Baseline Hawk
Tier S · Total 91
人设签名:给得出、改得动、有依据

反应:👏 😤 😂 🌫️

详细评分(默认在详情页才展开,承接 v0.1 开放问题 5)
- 明确性 Specificity ........ 92
- 证据 Evidence ............. 88
- 可操作性 Actionability .... 95
- 与其他审稿人一致度 ........ 74  （低不代表错）
- rebuttal 后仍成立 ......... 81
- 语气 Tone ................. 96

代表性评论
“Please compare against a standard retrieval baseline and report runtime.”
```

---

## 5. 分享卡 / Shareable Card(M4,裂变出口)

把单张 reviewer 卡导出为图片,作为对外传播物(X / 小红书)。

- 内容:pixel avatar + emoji 称号 + 假名 + Tier·分数 + 一句金句 + 顶部 tagline `Time to review the reviewers.`
- **硬约束**:仅 paper-scoped 假名;不含真实姓名、OpenReview 链接、reviewer_id;**黑榜内容不进分享卡**(承接上一轮决策 C)。
- 底部加产品边界小字:`Scores the usefulness of review comments, not reviewers as people.`(承接 v0.1 第 7 节)

---

## 6. 前端对象扩展

在 v0.1 第 5 节 `reviewer object` 基础上新增派生字段(均前端可计算,后端无需改):

```json
{
  "archetype": {
    "key": "operator",
    "emoji": "🦅",
    "label_cn": "实干派",
    "label_en": "The Operator",
    "tagline": "给得出、改得动、有依据"
  },
  "tier": { "grade": "S", "label_cn": "良心审稿" },
  "reactions": { "helpful": 128, "same": 34, "classic_r2": 9, "confusing": 3 }
}
```

---

## 7. 落地节奏(并入 v0.1 Milestones)

- **M2**:称号层(§1)+ 段位层(§2)+ 卡片正面新布局(§4)。这是把产品从「评分工具」拉到「社交产品」的最高性价比一步。
- **M3**:反应层(§3)替换 Like/Dislike,localStorage 防重复。
- **M4**:分享卡(§5)+ 榜单 + session 去重 + engagement 上限。

## 8. 待确认

1. 段位标签用中文(良心/靠谱…)还是中英混排?
2. 反应集是否需要支持 i18n 切换(英文社区用 `Classic Reviewer 2` 等)?
3. 称号规则表的阈值(80/60)是否需要按真实分数分布回归校准后再定稿?
