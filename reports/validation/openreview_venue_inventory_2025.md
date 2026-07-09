# OpenReview Venue Inventory

- Created: `2026-07-08T19:26:47+00:00`
- Sample limit: `20` papers per venue candidate

## Summary

| Status | Venues |
| --- | ---: |
| excluded_no_public_reviews | 6 |
| no_public_reviews | 1 |
| open_reviews_available | 5 |

## Venues

| Venue | Category | Scope | Status | Recommendation | Invitation | Papers | Reviews | Review coverage | Decision coverage | Review invitation samples |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| ICLR | top_conference | all_submissions | open_reviews_available | pull_and_score | `ICLR.cc/2025/Conference/-/Submission` | 20 | 76 | 95.0% | 75.0% | `ICLR.cc/2025/Conference/Submission14255/-/Official_Review ICLR.cc/2025/Conference/-/Edit, ICLR.cc/2025/Conference/Submission14257/-/Official_Review ICLR.cc/2025/Conference/-/Edit, ICLR.cc/2025/Conference/Submission14258/-/Official_Review ICLR.cc/2025/Conference/-/Edit` |
| ICML | top_conference | accepted_plus_public_opt_in | open_reviews_available | pull_and_score | `ICML.cc/2025/Conference/-/Submission` | 20 | 76 | 100.0% | 100.0% | `ICML.cc/2025/Conference/Submission16225/-/Official_Review ICML.cc/2025/Conference/-/Edit, ICML.cc/2025/Conference/Submission16227/-/Official_Review ICML.cc/2025/Conference/-/Edit, ICML.cc/2025/Conference/Submission16254/-/Official_Review ICML.cc/2025/Conference/-/Edit` |
| NEURIPS | top_conference | accepted_plus_public_opt_in | open_reviews_available | pull_and_score | `NeurIPS.cc/2025/Conference/-/Submission` | 20 | 80 | 100.0% | 100.0% | `NeurIPS.cc/2025/Conference/Submission29012/-/Official_Review NeurIPS.cc/2025/Conference/-/Edit, NeurIPS.cc/2025/Conference/Submission29012/-/Official_Review NeurIPS.cc/2025/Conference/-/Edit NeurIPS.cc/2025/Conference/Submission29012/Official_Review1/-/Review_Revision, NeurIPS.cc/2025/Conference/Submission29012/-/Official_Review NeurIPS.cc/2025/Conference/-/Edit NeurIPS.cc/2025/Conference/Submission29012/Official_Review2/-/Review_Revision` |
| TMLR | top_journal | rolling_2025_decision_or_activity | no_public_reviews | skip_scoring | `TMLR/-/Submission` | 20 | 0 | 0.0% | 0.0% | `-` |
| AISTATS | top_conference | public_openreview_submissions | excluded_no_public_reviews | skip_no_public_reviews | `AISTATS.cc/2025/Conference/-/Submission` | 0 | 0 | 0.0% | 0.0% | `-` |
| COLM | top_conference | public_openreview_submissions | open_reviews_available | pull_and_score | `colmweb.org/COLM/2025/Conference/-/Submission` | 20 | 75 | 100.0% | 100.0% | `colmweb.org/COLM/2025/Conference/Submission1766/-/Official_Review colmweb.org/COLM/2025/Conference/-/Edit, colmweb.org/COLM/2025/Conference/Submission1770/-/Official_Review colmweb.org/COLM/2025/Conference/-/Edit, colmweb.org/COLM/2025/Conference/Submission1781/-/Official_Review colmweb.org/COLM/2025/Conference/-/Edit` |
| CORL | top_conference | public_openreview_submissions | excluded_no_public_reviews | skip_no_public_reviews | `robot-learning.org/CoRL/2025/Conference/-/Submission` | 0 | 0 | 0.0% | 0.0% | `-` |
| MIDL | top_domain_conference | public_openreview_submissions | open_reviews_available | pull_and_score | `MIDL.io/2025/Conference/-/Post_Submission` | 20 | 62 | 100.0% | 0.0% | `MIDL.io/2025/Conference/Submission205/-/Official_Review MIDL.io/2025/Conference/-/Edit, MIDL.io/2025/Conference/Submission205/-/Official_Review MIDL.io/2025/Conference/-/Edit MIDL.io/2025/Conference/Submission205/Official_Review2/-/Review_Revision, MIDL.io/2025/Conference/Submission207/-/Official_Review MIDL.io/2025/Conference/-/Edit MIDL.io/2025/Conference/Submission207/Official_Review1/-/Review_Revision` |
| UAI | top_conference | public_openreview_submissions | excluded_no_public_reviews | skip_no_public_reviews | `auai.org/UAI/2025/Conference/-/Submission` | 0 | 0 | 0.0% | 0.0% | `-` |
| JAIR | top_journal | excluded_no_public_openreview_reviews | excluded_no_public_reviews | skip_no_public_reviews | `` | 0 | 0 | 0.0% | 0.0% | `-` |
| JMLR | top_journal | excluded_no_public_openreview_reviews | excluded_no_public_reviews | skip_no_public_reviews | `` | 0 | 0 | 0.0% | 0.0% | `-` |
| MLJ | top_journal | excluded_no_public_openreview_reviews | excluded_no_public_reviews | skip_no_public_reviews | `` | 0 | 0 | 0.0% | 0.0% | `-` |

## Attempt Details

### ICLR

- `ICLR.cc/2025/Conference/-/Submission`: `success`
- Note: Spec target: full 2025 ICLR public OpenReview corpus.
- Note: ICLR is treated as fully open public review scope; API probe confirms concrete review availability once OpenReview auth/challenge is satisfied.

### ICML

- `ICML.cc/2025/Conference/-/Submission`: `success`
- Note: Spec target: public ICML 2025 reviews, accepted plus public opt-in rejected papers where visible.
- Note: ICML is treated as partial public review scope; API probe determines exact public coverage after OpenReview auth/challenge is satisfied.

### NEURIPS

- `NeurIPS.cc/2025/Conference/-/Submission`: `success`
- Note: Spec target: public NeurIPS 2025 reviews, accepted plus public opt-in rejected papers where visible.
- Note: NeurIPS is treated as partial public review scope; API probe determines exact public coverage after OpenReview auth/challenge is satisfied.

### TMLR

- `TMLR/-/Submission`: `success`
- Note: Rolling OpenReview journal: pull all public submissions, then filter by 2025 decision/activity.
- Note: Second-round probe confirms public replies exist on older/decided submissions, but latest under-review submissions have no public replies.
- Note: TMLR needs a rolling extractor that filters decided/activity-2025 submissions and reads paper-level Official_Comment threads.
- Note: Rolling venue: full pull must filter by 2025 decision or activity date after download.

### COLM

- `colmweb.org/COLM/2025/Conference/-/Submission`: `success`
- Note: Probe on 2026-07-08 found public official reviews on colmweb.org/COLM/2025/Conference/-/Submission: 20/20 sampled papers, 75 reviews.

### AISTATS

- Note: Recheck on 2026-07-08: AISTATS.cc Submission/Post_Submission returned 0 papers; aistats.org/AISTATS Submission/Post_Submission each sampled 50 papers with 0 replies and 0 official reviews. Mark excluded until public official reviews become visible.
- Note: Excluded from scoring queue: no public OpenReview review corpus is expected for this venue.

### UAI

- Note: Recheck on 2026-07-08: auai.org/UAI/2025/Conference/-/Submission sampled 50 papers with 0 public official reviews. Mark excluded until public official reviews become visible.
- Note: Excluded from scoring queue: no public OpenReview review corpus is expected for this venue.

### CORL

- Note: Recheck on 2026-07-08: robot-learning.org/CoRL/2025/Conference/-/Submission sampled 50 papers and 50 decision replies with 0 public official reviews. Mark excluded until public official reviews become visible.
- Note: Excluded from scoring queue: no public OpenReview review corpus is expected for this venue.

### MIDL

- `MIDL.io/2025/Conference/-/Post_Submission`: `success`
- Note: Second-round probe found public reviews on MIDL.io/2025/Conference/-/Post_Submission.
- Note: Sample of 50 submissions returned 163 public reviews with 100% sample coverage.

### JMLR

- Note: Top ML journal tracked for scope control; no public OpenReview official-review corpus is expected for 2025 scoring.
- Note: Excluded from scoring queue: no public OpenReview review corpus is expected for this venue.

### JAIR

- Note: Top AI journal tracked for scope control; no public OpenReview official-review corpus is expected for 2025 scoring.
- Note: Excluded from scoring queue: no public OpenReview review corpus is expected for this venue.

### MLJ

- Note: Top ML journal tracked for scope control; no public OpenReview official-review corpus is expected for 2025 scoring.
- Note: Excluded from scoring queue: no public OpenReview review corpus is expected for this venue.
