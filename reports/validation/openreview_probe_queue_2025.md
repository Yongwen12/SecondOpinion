# OpenReview Probe Queue

- Created: `2026-07-07T10:33:50+00:00`
- Sample limit: `50`
- Probe count: `11`
- Multi-candidate probes: `6`
- Core priority 1: `ICLR, ICML, NEURIPS, TMLR`
- Probe priority 2: `AISTATS, COLM, CORL, UAI`

## Queue

| Venue | Priority | Candidate | Purpose | Invitation | Group URL |
| --- | ---: | ---: | --- | --- | --- |
| ICLR | 1 | 1/1 | confirm_public_reviews | `ICLR.cc/2025/Conference/-/Submission` | `https://openreview.net/group?id=ICLR.cc/2025/Conference` |
| ICML | 1 | 1/1 | confirm_public_reviews | `ICML.cc/2025/Conference/-/Submission` | `https://openreview.net/group?id=ICML.cc/2025/Conference` |
| NEURIPS | 1 | 1/1 | confirm_public_reviews | `NeurIPS.cc/2025/Conference/-/Submission` | `https://openreview.net/group?id=NeurIPS.cc/2025/Conference` |
| TMLR | 1 | 1/1 | confirm_public_reviews | `TMLR/-/Submission` | `https://openreview.net/group?id=TMLR` |
| AISTATS | 2 | 1/2 | resolve_multi_candidate | `AISTATS.cc/2025/Conference/-/Submission` | `https://openreview.net/group?id=AISTATS.cc/2025/Conference` |
| AISTATS | 2 | 2/2 | resolve_multi_candidate | `aistats.org/AISTATS/2025/Conference/-/Submission` | `https://openreview.net/group?id=aistats.org/AISTATS/2025/Conference` |
| COLM | 2 | 1/1 | confirm_public_reviews | `colmweb.org/2025/Conference/-/Submission` | `https://openreview.net/group?id=colmweb.org/2025/Conference` |
| CORL | 2 | 1/2 | resolve_multi_candidate | `robot-learning.org/CoRL/2025/Conference/-/Submission` | `https://openreview.net/group?id=robot-learning.org/CoRL/2025/Conference` |
| CORL | 2 | 2/2 | resolve_multi_candidate | `CoRL.cc/2025/Conference/-/Submission` | `https://openreview.net/group?id=CoRL.cc/2025/Conference` |
| UAI | 2 | 1/2 | resolve_multi_candidate | `auai.org/UAI/2025/Conference/-/Submission` | `https://openreview.net/group?id=auai.org/UAI/2025/Conference` |
| UAI | 2 | 2/2 | resolve_multi_candidate | `UAI.cc/2025/Conference/-/Submission` | `https://openreview.net/group?id=UAI.cc/2025/Conference` |

## Commands

```powershell
python -m secondopinion.tools.openreview_probe_invitation --venue ICLR --invitation "ICLR.cc/2025/Conference/-/Submission" --sample-limit 50 --out data/validation/openreview_probe_iclr_c1_50.json --markdown reports/validation/openreview_probe_iclr_c1_50.md
python -m secondopinion.tools.openreview_probe_invitation --venue ICML --invitation "ICML.cc/2025/Conference/-/Submission" --sample-limit 50 --out data/validation/openreview_probe_icml_c1_50.json --markdown reports/validation/openreview_probe_icml_c1_50.md
python -m secondopinion.tools.openreview_probe_invitation --venue NEURIPS --invitation "NeurIPS.cc/2025/Conference/-/Submission" --sample-limit 50 --out data/validation/openreview_probe_neurips_c1_50.json --markdown reports/validation/openreview_probe_neurips_c1_50.md
python -m secondopinion.tools.openreview_probe_invitation --venue TMLR --invitation "TMLR/-/Submission" --sample-limit 50 --out data/validation/openreview_probe_tmlr_c1_50.json --markdown reports/validation/openreview_probe_tmlr_c1_50.md
python -m secondopinion.tools.openreview_probe_invitation --venue AISTATS --invitation "AISTATS.cc/2025/Conference/-/Submission" --sample-limit 50 --out data/validation/openreview_probe_aistats_c1_50.json --markdown reports/validation/openreview_probe_aistats_c1_50.md
python -m secondopinion.tools.openreview_probe_invitation --venue AISTATS --invitation "aistats.org/AISTATS/2025/Conference/-/Submission" --sample-limit 50 --out data/validation/openreview_probe_aistats_c2_50.json --markdown reports/validation/openreview_probe_aistats_c2_50.md
python -m secondopinion.tools.openreview_probe_invitation --venue COLM --invitation "colmweb.org/2025/Conference/-/Submission" --sample-limit 50 --out data/validation/openreview_probe_colm_c1_50.json --markdown reports/validation/openreview_probe_colm_c1_50.md
python -m secondopinion.tools.openreview_probe_invitation --venue CORL --invitation "robot-learning.org/CoRL/2025/Conference/-/Submission" --sample-limit 50 --out data/validation/openreview_probe_corl_c1_50.json --markdown reports/validation/openreview_probe_corl_c1_50.md
python -m secondopinion.tools.openreview_probe_invitation --venue CORL --invitation "CoRL.cc/2025/Conference/-/Submission" --sample-limit 50 --out data/validation/openreview_probe_corl_c2_50.json --markdown reports/validation/openreview_probe_corl_c2_50.md
python -m secondopinion.tools.openreview_probe_invitation --venue UAI --invitation "auai.org/UAI/2025/Conference/-/Submission" --sample-limit 50 --out data/validation/openreview_probe_uai_c1_50.json --markdown reports/validation/openreview_probe_uai_c1_50.md
python -m secondopinion.tools.openreview_probe_invitation --venue UAI --invitation "UAI.cc/2025/Conference/-/Submission" --sample-limit 50 --out data/validation/openreview_probe_uai_c2_50.json --markdown reports/validation/openreview_probe_uai_c2_50.md
```
