# Judge My Reviewers：离谱社区 v1 实施规格

状态：`IMPLEMENTED`（2026-08-06）

适用对象：Terra 级实现模型。本文档已经完成产品决策；实现过程中不得重新发明信息架构、榜单维度、评分口径或视觉语言。

---

## 1. 唯一产品定义

Judge My Reviewers 只做一件事：

> 展示公开同行评审里最离谱的内容，让读者投票、评论和争论。

首页的完整用户路径只有：

1. 看见一条离谱评审原文。
2. 选择 `OUTRAGEOUS` 或 `NOT REALLY`。
3. 看真实票数和评论。
4. 进入帖子继续讨论。

不得在首页解释 AI 如何判断，不得展示多维评分，不得引导用户理解论文质量。

---

## 2. 已锁定的产品决策

### 2.1 榜单入口

首页主入口固定为：

```text
LATEST        ALL-TIME                              🔥 HOT THREADS →
```

- `LATEST` 与 `ALL-TIME` 是两个同级主 Tab。
- 默认选中 `LATEST`。
- `HOT THREADS` 是右侧次级链接，不得做成第三个同级 Tab。
- 不使用下拉菜单。
- 不出现 `Worst Review Failures`、`Personal / Toxic`、`Reviews Worth Keeping` 等旧榜单。
- URL 状态必须可复制：`?board=latest`、`?board=all-time`、`?view=hot`。
- 浏览器前进/后退必须恢复对应状态。

### 2.2 唯一公开判断

公开判断只有：

- `OUTRAGEOUS`：离谱。
- `NOT REALLY`：不算离谱。

数据库第一阶段可继续保存 `up/down`，但公共接口与前端组件不得继续使用“helpful/disputed”语义：

- `up` 在边界层映射为 `outrageous`。
- `down` 在边界层映射为 `not_really`。
- 旧客户端传入 `up/down` 仍兼容；新客户端只传公开语义。

### 2.3 AI 的位置

- 首页、帖子页均不显示 `/100`、`AI score`、`risk score`、维度条或 AI 解释。
- AI 的离谱分只允许用于候选筛选和冷启动补位，不直接展示。
- 每条内容允许一条编辑式短评，字段沿用 `verdict`，前台不标记为 AI。
- 短评缺失时直接省略，不渲染解释性 fallback。

### 2.4 评论与投票

- 投票是主要动作，评论是可选动作。
- 用户可以只投票，不评论。
- 用户可以公开阅读评论。
- 用户提交评论前必须已经选择一边；未投票时提交，显示 `Vote first to join the thread.`。
- 没有评论的榜单项不渲染空评论框、`No comments yet` 或占位评论。
- 无评论时仍保留 `OPEN THREAD →`，用于查看完整来源或发起讨论。

---

## 3. 榜单语义与排序

### 3.1 LATEST

问题：今天新出现了什么离谱评审？

排序：

1. 只保留当前最新 scorecard 中、通过隐藏离谱候选阈值的 reviewer row。
2. 按 `ReviewerScore.created_at DESC`。
3. 相同时间按 `paper_id ASC, reviewer_key ASC`，保证稳定排序。
4. 同一 `(paper_id, reviewer_key)` 只出现一次。
5. 评论、投票或 reaction 的更新时间不得把旧内容顶回 LATEST。

每行右上角只显示相对上榜时间，例如 `18 MIN AGO`、`2 DAYS AGO`，不显示 AI 分数。

### 3.2 ALL-TIME

问题：到目前为止，社区公认最离谱的是哪些？

正式排名仅使用真实社区投票：

```text
positive = outrageous_votes
negative = not_really_votes
n = positive + negative
rank_score = Wilson lower bound(positive, n, z = 1.96)
```

规则：

- `n >= 5` 才进入正式社区排名。
- 先按 `rank_score DESC`。
- 再按 `n DESC`。
- 再按 `ReviewerScore.created_at DESC`。
- 如果正式排名不足 12 条，在尾部追加隐藏 AI 离谱分最高的候选作为冷启动补位。
- 冷启动补位必须排在所有 `n >= 5` 的正式排名之后；前台只标 `NEW`，不得显示 AI 分数。
- 数据达到 12 条正式排名后，自动停止冷启动补位。

前台显示原始真实票数，不显示 Wilson 计算结果，也不解释算法。

### 3.3 HOT THREADS

`HOT THREADS` 是独立互动视图，不是离谱程度维度。

统计窗口：最近 48 小时。

第一版热度公式：

```text
hot_score =
  4 × distinct_commenters_48h
  + 2 × comments_48h
  + 1 × vote_changes_48h
  + 1 × reactions_48h
  + controversy_bonus

controversy_bonus =
  min(10, vote_total) × (1 - abs(outrageous - not_really) / max(1, vote_total))
```

约束：

- 至少有 `2` 位不同评论者，或最近 48 小时至少 `3` 条评论，才进入 HOT。
- 同一 session 的重复行为不能无限增加热度。
- 前台不展示 `hot_score`，只展示 `36 COMMENTS · 8 NEW TODAY` 等真实互动信息。
- v1 没有评论回复表时，使用平铺评论；不要假造回复关系。

---

## 4. 页面架构

### 4.1 首页 `/`

从上到下严格为：

1. Masthead：品牌、archive 元信息、搜索、账户。
2. 一行产品标题：`OUTRAGEOUS PEER REVIEW, RANKED BY READERS.`
3. 榜单导航：`LATEST / ALL-TIME`，右侧 `HOT THREADS →`。
4. 榜单列表。
5. 精简 footer：来源、Methodology、Privacy、Terms、Report。

首页删除：

- Venue risk ranking。
- 大号统计数字。
- 三类旧榜单。
- `MORE ABOUT THIS PAPER` 大按钮。
- `Machine judgment, not a verdict.` 大段提示。
- 所有可见 AI 分数、质量分和维度。
- 旧 `community ticker`。

安全/来源说明可以保留在 footer 或 Methodology 页面，不得夹在榜单正文里抢占注意力。

### 4.2 帖子页 `/thread/{paper_id}/{reviewer_key}`

这是旧 scorecard 详情的公共替代入口。结构：

1. `← BACK TO LEADERBOARD`
2. Rank/发布时间和 venue 元信息。
3. 评审原文。
4. 论文标题与 OpenReview 来源链接。
5. 一句短评。
6. `OUTRAGEOUS / NOT REALLY` 投票。
7. emoji reactions。
8. 评论列表。
9. 评论输入框；提交前必须投票。

不得默认展示整篇 AI scorecard。现有深度 scorecard 如仍需保留，只能作为 Methodology/内部入口，不能成为首页榜单的默认落点。

### 4.3 HOT 视图 `/?view=hot`

保持相同 masthead。榜单导航仍可见，但 HOT 入口使用红色文字和下划线表示当前状态。

正文标题：

```text
HOT THREADS
THE ARGUMENTS MOVING FASTEST IN THE LAST 48 HOURS.
```

每项以讨论为中心：评审原文缩短为两行，评论数量与最近两条评论提升到主要位置。仍保留投票按钮，但不出现第三种判断。

---

## 5. 视觉系统

方向：CS 学术期刊 × 老论坛。禁止 SaaS dashboard、圆角卡片墙和渐变营销页。

### 5.1 色彩

```css
--paper: #f6f3ea;
--surface: #ffffff;
--ink: #111111;
--muted: #68655f;
--line: #c9c4b9;
--line-strong: #111111;
--outrage: #ff2a14;
--outrage-dark: #c91a09;
--soft-red: #fff0ed;
```

规则：

- 页面以纸白、黑、鲜红为主。
- 红色只用于选中投票、排名强调、HOT 入口和关键链接。
- 未选中的两个投票按钮都必须是白底黑框。
- 不使用绿色表达另一方。
- 不使用阴影；边框组织层级。
- 结构区域圆角为 `0–2px`，不得使用大圆角卡片。

### 5.2 字体

```css
--display: Georgia, "Times New Roman", serif;
--ui: Arial, Helvetica, sans-serif;
--meta: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
```

- 品牌、评审原文：`--display`。
- 按钮、Tab、正文：`--ui`。
- venue、时间、用户名、票数元信息：`--meta`。
- 字重只使用 400、700、900；避免全页粗体。

### 5.3 尺寸与网格

- 页面最大宽度：`1120px`。
- 桌面左右边距：`32px`；移动端：`16px`。
- 基础间距：`8px`。
- Masthead 高度：约 `64px`。
- 桌面榜单行网格：`64px minmax(0, 1fr) 150px`。
- 行上下内边距：`24px`。
- 行之间用 `1px solid var(--line-strong)`。
- 不把每行包成独立卡片。

---

## 6. 首页具体 UI

### 6.1 Masthead

桌面：

```text
JUDGE MY REVIEWERS        PUBLIC REVIEW ARCHIVE · VOL. 01        Search    Sign in
```

- 品牌：28px serif，900。
- Archive 元信息：11px monospace，大写，字间距 0.08em。
- `Search` 与 `Sign in`：小型文本按钮，不使用实心大按钮。
- 点击 Search 展开现有搜索框；搜索结果只用于定位 paper/review thread。

移动端：品牌在第一行；archive 元信息隐藏；Search/Sign in 保持右侧。

### 6.2 标题

```text
OUTRAGEOUS PEER REVIEW,
RANKED BY READERS.
```

- 桌面 36–42px serif。
- 移动端 28–32px。
- 只有标题，不跟一段解释文案。

### 6.3 榜单导航

HTML 语义：

```html
<div class="outrage-board-nav">
  <div role="tablist" aria-label="Outrage leaderboard">
    <button role="tab" aria-selected="true">LATEST</button>
    <button role="tab" aria-selected="false">ALL-TIME</button>
  </div>
  <a href="/?view=hot">🔥 HOT THREADS <span>12</span> →</a>
</div>
```

视觉：

- 整体底部 `2px` 黑线。
- Tab 无外框、无胶囊背景。
- 选中 Tab：红色文字，底部 `4px` 红线。
- 未选中：黑色文字。
- HOT：右对齐，12px monospace，红色 flame，其余黑色。
- HOT 后的小数字只在真实 hot thread 数量大于 0 时显示。

移动端：Tab 第一行占左侧；HOT 换到第二行右对齐。仍然不能把 HOT 放进 tablist。

### 6.4 榜单行结构

桌面：

```text
┌──────┬───────────────────────────────────────────────┬──────────────┐
│ #01  │ “This paper is only a template...”            │ 18 MIN AGO   │
│      │ Balancing Differential... · ICLR 2025 · R4   │              │
│      │ This is not a review. It is a vibe with a 3.  │ OPEN THREAD →│
│      │ [▲ OUTRAGEOUS 87] [▼ NOT REALLY 12] 💀 14 😂 8│              │
│      │ @anon-b65fab  “The confidence is doing work.” │              │
└──────┴───────────────────────────────────────────────┴──────────────┘
```

DOM 约束：

- `<article>` 本身不是 button，不设置 `role="button"`。
- 原文标题使用真实 `<a>` 进入 thread。
- 投票与 reaction 是独立 `<button>`，避免嵌套交互元素。
- 右侧只放相对时间和 `OPEN THREAD →`；不放分数。

内容顺序：

1. 排名：`#01`，前 3 名红色，其他黑色。
2. 原文：最多 3 行；原始引号保留。
3. 论文元信息：`Paper title · Venue Year · Reviewer N`。
4. 短评：最多 1 行；存在才显示。
5. 投票、reaction 和评论数。
6. 评论预览：存在才显示，最多 2 条。

### 6.5 投票按钮

默认：

```text
[ ▲ OUTRAGEOUS 87 ]  [ ▼ NOT REALLY 12 ]
```

- 同一行，间距 `8px`。
- 高度 `36px`。
- 未选择：白底、黑框、黑字；三角形使用鲜红色。
- 选择：鲜红底、鲜红框、白字、白色三角形。
- hover 不得把未选项变黑；仅使用 `soft-red`。
- focus 保留清晰 outline。
- 点击已选项表示撤销；点击另一项表示切换，不新增第二票。
- 计数使用 tabular numbers。

移动端：两按钮仍在同一排，各占 `minmax(0, 1fr)`；文案可以缩为 `OUTRAGEOUS` / `NOT REALLY`，数字不可隐藏。

### 6.6 评论预览

有评论时：

```text
@anon-b65fab · 14 MIN
The confidence is doing most of the reviewing here.
```

- 最多显示 2 条。
- 用户名、时间用 11px monospace。
- 正文 14px。
- 评论之间只用浅灰横线。
- 总评论数大于预览数时显示 `+ 14 MORE IN THREAD →`。

无评论时：

- 完全不渲染 `.comment-preview`。
- 不显示空白占位或虚线输入框。
- 右侧 `OPEN THREAD →` 保留。

### 6.7 Reaction

- 首页默认最多显示 3 个已有 reaction，例如 `💀 14  😂 8  🤡 3`。
- 数量为 0 的 emoji 不常驻首页。
- `+` 打开完整 reaction 选择器。
- reaction 不替代离谱投票，不允许使用 👍/👎 造成判断语义重复。

---

## 7. 帖子页具体 UI

桌面最大正文宽度 `820px`，不做左右 dashboard。

### 7.1 主帖

```text
← BACK TO LATEST

#01 · ICLR 2025 · POSTED 18 MIN AGO

“This paper is only a template, which shows no respect for ICLR.”

Balancing Differential Discriminative Knowledge...
Reviewer 4 · View original on OpenReview ↗

This is not a review. It is a vibe with a 3.

[ ▲ OUTRAGEOUS 87 ] [ ▼ NOT REALLY 12 ]   💀14 😂8 +
```

- 原文 28–36px serif。
- 论文标题次级，不得比原文更醒目。
- 短评使用粗体 16px，但不得加 `AI TAKE` 标签。
- 投票组件与首页复用同一个函数和状态源。

### 7.2 评论区

标题：`DISCUSSION · 36 COMMENTS`

排序第一版：`NEWEST` 默认，可切换 `OLDEST`；不要增加 Best/Controversial，避免无数据支持的排序。

评论项：

```text
@anon-b65fab                                      14 MIN AGO
The confidence is doing most of the reviewing here.
REPLY
```

第一版不实现嵌套回复时，`REPLY` 只预填 `@handle`，仍作为平铺评论提交。不得伪造树状关系。

### 7.3 评论输入

- 已投票：显示 textarea 和 `POST COMMENT`。
- 未投票：textarea 可见但提交按钮文案为 `VOTE FIRST`，点击后聚焦投票区并显示行内提示。
- 评论可为空以外不得阻止单独投票。
- 提交成功后追加真实服务端返回评论，不使用本地假评论。

---

## 8. 短评文案规格

`verdict` 是编辑式 punchline，不是解释。

必须：

- 英文 4–16 个词，最多 90 个字符。
- 一句话。
- 针对评审文本或论证方式，不针对 reviewer 的人格。
- 可以尖锐、口语、有节奏。
- 没有足够依据时省略。

禁止：

- `AI thinks...`
- `Our analysis shows...`
- `This review scores highly because...`
- 复述多维 rubric。
- 推断匿名 reviewer 身份、动机或能力。
- 针对作者或 reviewer 的人身攻击。

可接受示例：

- `Three words. Zero actionable detail.`
- `“Not novel” is not a citation.`
- `The confidence is doing most of the reviewing here.`
- `A rejection wearing the costume of feedback.`
- `Right neighborhood. No address.`

不可接受示例：

- `The reviewer is clearly incompetent.`
- `AI toxicity score: 87.`
- `This is problematic due to low specificity and actionability.`

---

## 9. API 合同

### 9.1 首页

保留 `GET /api/home`，增加新的 board keys，旧 keys 暂不删除以兼容已有客户端：

```json
{
  "leaderboards": {
    "outrage_latest": [],
    "outrage_all": [],
    "outrage_hot": []
  }
}
```

每一行必须返回：

```json
{
  "paper_id": "...",
  "reviewer_key": "R4",
  "paper_title": "...",
  "venue": "ICLR",
  "year": 2025,
  "quote": "...",
  "verdict": "...",
  "surfaced_at": "2026-08-06T10:20:00Z",
  "votes": {
    "outrageous": 87,
    "not_really": 12,
    "total": 99
  },
  "viewer_vote": "outrageous",
  "comment_count": 36,
  "latest_comments": [],
  "reactions": {}
}
```

约束：

- `votes` 必须来自 `votes` 表，不能从 AI score 或 snapshot 合成。
- 静态 `home_2025.json` 加载后，服务端必须覆盖实时票数、viewer vote、评论和 reactions。
- `latest_comments` 最多 2 条。
- 不向公共 payload 新增 Wilson score、hot score 或隐藏 AI score。

### 9.2 投票

请求：

```http
POST /api/papers/{paper_id}/reviewers/{reviewer_key}/votes
Content-Type: application/json

{"vote":"outrageous"}
```

允许值：`outrageous`、`not_really`、`none`；兼容旧值 `up/down`。

响应必须是当前服务端真值：

```json
{
  "selected": "outrageous",
  "votes": {
    "outrageous": 88,
    "not_really": 12,
    "total": 100
  }
}
```

前端不得在成功后继续使用自行加减的本地计数；必须以响应覆盖。失败时恢复点击前状态并显示轻量 toast。

### 9.3 帖子评论

沿用现有 reviewer comment 接口。新增验证：提交评论时服务端确认该 session 对本 review 存在 vote；否则返回：

```json
{"detail":{"code":"vote_required"}}
```

HTTP 状态：`409 Conflict`。

---

## 10. 前端状态模型

替换 `homeBoardKind = overall/toxic/helpful`：

```js
const BOARD_ORDER = ['latest', 'all-time'];
let homeBoardKind = initialHomeBoard();
```

统一 row 主键：

```js
function reviewKey(row) {
  return `${row.paperId}:${row.reviewerKey}`;
}
```

所有位置共享：

- `votesByReview[reviewKey]`
- `commentsByReview[reviewKey]`
- `reactionsByReview[reviewKey]`

不得让首页、弹窗和帖子页各自维护不同的票数副本。

投票状态机：

```text
none --click outrageous--> outrageous
none --click not really--> not_really
outrageous --click outrageous--> none
outrageous --click not really--> not_really
not_really --click not really--> none
not_really --click outrageous--> outrageous
```

每次状态变化：

1. 保存 previous snapshot。
2. optimistic 更新当前 review 的唯一 store。
3. 立即重渲染所有引用该 review 的组件。
4. POST。
5. 成功：使用服务端响应覆盖 store。
6. 失败：恢复 snapshot，提示错误。

---

## 11. 当前代码的具体改造点

### 11.1 `frontend/index.html`

必须修改的现有锚点：

- `BOARD_ORDER`：从三类旧榜单改为 `latest/all-time`。
- `BOARD_COPY`：删除 overall/toxic/helpful 的 score、tier、rate 文案，建立 latest/all-time 文案。
- `DEMO_HOME_BOARDS`：只保留与新 API 结构一致的 outrage demo rows。
- `normalizeBoardRow`：移除 toxicity/helpfulness/attention 的公开分支，改为标准化 `votes`、`viewer_vote`、`surfaced_at`。
- `normalizeHomeBoards`：读取 `outrage_latest/outrage_all`；旧 `overall` 只作为临时 fallback。
- `renderCommunityBoard`：只渲染两个 Tab，并在 tablist 外渲染 HOT 链接。
- `boardRowHtml`：移除 `.outrage-scorebox`、`/100`、meter 和 `MORE ABOUT THIS PAPER`。
- `boardRowSocialHtml`：改为 `OUTRAGEOUS/NOT REALLY`；无评论时不渲染 take 容器。
- 投票 click handler：直接发送公开 vote 值，并用服务端返回覆盖共享状态。
- `venue-ranking`、`communityTicker`、旧 trust paragraph：从首页正文移除。
- 旧 resolved scorecard 不再作为榜单默认点击目标；新增 thread render state 或独立 thread route。

不要通过只改 visible label 的方式保留旧三榜逻辑；数据归一化和状态 key 也必须一起收敛。

### 11.2 `src/secondopinion/server/repository.py`

新增或重构为三个职责清晰的函数：

```python
build_outrage_latest(...)
build_outrage_all_time(...)
build_hot_threads(...)
```

公共 row 组装提取为一个 helper，避免三个列表对 votes/comments/reactions 使用不同字段。

必须：

- 只选择最新 scorecard 的 `(paper_id, reviewer_key)`。
- votes 只读 Vote 表。
- latest 使用 ReviewerScore.created_at。
- all-time 使用 Wilson 下界并执行 `n >= 5`。
- hot 使用真实 48h 行为。
- 数据库不支持窗口函数的测试环境需有等价 fallback。

### 11.3 `src/secondopinion/server/api.py`

- `/api/home` 返回新 board keys。
- `enrich_home_community_signals` 同时覆盖 votes、viewer_vote、comments 和 reactions，不能只覆盖后两者。
- vote endpoint 接受新语义并兼容旧值。
- vote endpoint 返回选中状态与最新计数。
- comment endpoint 增加 vote-required 验证。

### 11.4 `frontend/data/home_2025.json`

- 重新生成 `outrage_latest` 和冷启动候选。
- 静态文件中的票数必须为 0 或构建时真实快照；运行时由 API 覆盖。
- 删除前台依赖的 toxic/helpful tabs；旧字段可暂时保留一版，但不得渲染。

### 11.5 测试

更新并增加：

- `tests/test_frontend_api_wiring.py`
- `tests/test_server_api.py`
- 必要时新增 `tests/test_outrage_leaderboards.py`

---

## 12. 实施提交顺序

Terra 必须按以下顺序执行，每一步单独验证：

### Commit 1：社区真值与榜单接口

- 新 vote 公共语义。
- 服务端返回 authoritative counts 和 viewer vote。
- latest/all-time/hot builder。
- API 单元测试。

完成条件：无前端改动时，接口已能稳定返回三份真实列表。

### Commit 2：首页结构和视觉

- 新 masthead、标题、两 Tab、HOT 次级入口。
- 新榜单行。
- 删除可见 AI score 和旧榜单。
- 响应式布局。

完成条件：桌面和 360px 都能完整浏览；未选按钮保持白色。

### Commit 3：统一投票闭环

- 首页、帖子页复用一个 vote store/component。
- optimistic update + server reconciliation + rollback。
- 切换、撤销、刷新状态验证。

完成条件：三个位置显示一致计数，不重复计票。

### Commit 4：帖子与评论

- thread route/view。
- 评论读取和提交。
- 未投票时阻止评论提交。
- 空评论预览不渲染。

完成条件：只投票路径和投票后评论路径都成功。

### Commit 5：清理与回归

- 删除首页不可达的旧榜单代码/CSS。
- 更新静态 snapshot。
- 全量相关测试和截图 QA。

---

## 13. 明确不做

Terra 不得顺手增加：

- 第三个同级榜单 Tab。
- 下拉榜单选择器。
- 论文质量评分。
- reviewer 人格标签或身份猜测。
- 多维 AI 图表。
- AI 聊天框或解释按钮。
- 用户声望、等级、徽章。
- 私信、关注 reviewer。
- 评论点赞排序。
- 无限 emoji 常驻条。
- 新设计系统依赖、前端框架迁移。
- 在这一轮重写整套后端。

---

## 14. 验收标准

### 产品

- [ ] 第一次访问默认看到 `LATEST`。
- [ ] 只有 `LATEST` 与 `ALL-TIME` 两个主 Tab。
- [ ] `HOT THREADS` 位于 Tab 右侧且不在 tablist 中。
- [ ] 页面承诺始终围绕“离谱评审”。
- [ ] 不出现 helpful/toxic/quality 等竞争维度。

### UI

- [ ] 无 `/100`、AI score、risk meter。
- [ ] 两个投票按钮始终同排。
- [ ] 未选择按钮为白色，选择按钮为鲜红色。
- [ ] 三角形颜色醒目。
- [ ] 右侧只显示时间和轻量 thread 链接。
- [ ] 无评论时没有空评论区域。
- [ ] 桌面、768px、360px 无横向溢出。

### 数据

- [ ] 票数全部来自 Vote 表。
- [ ] 同 session 同 review 最多一票。
- [ ] 切换投票不会让总票数增加 1。
- [ ] 撤销投票会让总票数减少 1。
- [ ] API 响应、首页、帖子页计数一致。
- [ ] 刷新后计数和选择状态保持。
- [ ] LATEST 不受新评论影响排序。
- [ ] ALL-TIME 对 1 票内容不会排到第一。

### 评论

- [ ] 用户可以投票后不评论。
- [ ] 未投票不能提交评论。
- [ ] 有评论时最多预览两条。
- [ ] 无评论时不显示 placeholder。
- [ ] 评论成功后列表与计数同步。

### 回归

- [ ] 搜索仍可定位 paper/review。
- [ ] OpenReview 来源链接正常。
- [ ] 登录与匿名 session 均可投票。
- [ ] reaction 仍是一人一个，可切换/撤销。
- [ ] Methodology、Privacy、Terms、Report 链接正常。

---

## 15. Terra 执行提示

实现时以本文档为决策源，不要根据旧页面文案推断产品意图。旧代码里的 `overall/toxic/helpful`、`useful/disputed`、`scorebox` 都是待删除的历史结构，不是需要保留的产品需求。

任何无法一次完成的部分，优先保证以下闭环：

```text
LATEST / ALL-TIME → 原文 → OUTRAGEOUS / NOT REALLY → 真实票数 → thread 评论
```

不得以保留 AI 分数、第三 Tab 或旧 scorecard 默认入口作为“临时方案”。
