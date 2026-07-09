# OpenReview 2025 Second-Round Venue Probe

## Summary

- Already completed and scored: ICLR, ICML, NeurIPS.
- Newly confirmed public-review venue: MIDL 2025.
- TMLR is viable, but not with the normal latest-submission probe. It needs a rolling extractor over decided/activity-2025 papers and paper-level `Official_Comment` threads.
- ACL, NAACL, EMNLP, AISTATS, CVPR, and AAAI AI Alignment did not expose a public review corpus through the sampled 2025 OpenReview invitations.

## Confirmed

| Venue | Invitation / source | Probe result | Next step |
| --- | --- | --- | --- |
| MIDL 2025 | `MIDL.io/2025/Conference/-/Post_Submission` | 50 sampled papers, 163 public reviews, 100% sampled coverage | Full pull, batch score, import |
| TMLR | `TMLR/-/Submission` plus `TMLR/Paper*/-/Official_Comment` | Latest submissions have no public replies, but older/decided offsets do. Offset 1000/2000/4000 returned 186/205/247 replies per 20 sampled submissions. | Build custom rolling extractor and score 2025 decided/activity papers |

## Not Confirmed In Second-Round Sample

| Venue | Probe result |
| --- | --- |
| ACL 2025 | Discovered ARR/Post_Submission invitations, but sampled notes/reviews were not publicly available. |
| NAACL 2025 | Discovered ARR/Post_Submission invitations, but sampled notes/reviews were not publicly available. |
| EMNLP 2025 | Post_Submission invitation discovered, but no public review sample. |
| AISTATS 2025 | 50 visible post-submission papers, 0 public reviews in sample. |
| CVPR 2025 | Post_Submission invitation discovered, but no public review sample. |
| AAAI AI Alignment 2025 | Post_Submission invitation discovered, but no public review sample. |

## Execution Plan

1. Add MIDL to the normal venue scoring path and run a full pull on `MIDL.io/2025/Conference/-/Post_Submission`.
2. Score MIDL reviews with the same batch scorer used for ICLR/ICML/NeurIPS.
3. Build a TMLR-specific extractor that pages through `TMLR/-/Submission`, filters to 2025 decision/activity, and extracts `Official_Comment` content from paper-level threads.
4. Run a small TMLR dry run first, then batch score/import once the extractor proves review/comment quality is suitable.
