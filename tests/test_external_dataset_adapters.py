from secondopinion.external_dataset_adapters import (
    normalize_contrasciview_csv,
    normalize_disapere_records,
    normalize_react_records,
    normalize_rbtact_records,
    normalize_substanreview_records,
)


def test_normalize_contrasciview_maps_labels_and_polarity_baseline(tmp_path):
    csv_path = tmp_path / "contrasciview.csv"
    csv_path.write_text(
        ",Unnamed: 0,paper_id,pair_id,hypothesis,premise,aspect,s1,s2,line_pair,label\n"
        "0,0,ICLR_1,3,Reviewer one likes the method.,Reviewer two dislikes the method.,soundness,positive,negative,\"(1, 2)\",c\n"
        "1,1,ICLR_2,4,Both comments ask for more baselines.,The evaluation needs stronger baselines.,substance,negative,negative,\"(3, 4)\",n\n",
        encoding="utf-8",
    )

    records = normalize_contrasciview_csv(csv_path, baseline="polarity")

    assert len(records) == 2
    assert records[0]["gold_label"] == "contradiction"
    assert records[0]["predicted_label"] == "contradiction"
    assert records[1]["gold_label"] == "not_contradiction"
    assert records[1]["predicted_label"] == "not_contradiction"
    assert records[0]["task_id"] == "contrasciview:ICLR_1:3:0"


def test_normalize_contrasciview_majority_baseline(tmp_path):
    csv_path = tmp_path / "contrasciview.csv"
    csv_path.write_text(
        ",Unnamed: 0,paper_id,pair_id,hypothesis,premise,aspect,s1,s2,line_pair,label\n"
        "0,0,ICLR_1,3,A positive comment.,A negative comment.,soundness,positive,negative,\"(1, 2)\",c\n",
        encoding="utf-8",
    )

    records = normalize_contrasciview_csv(csv_path, baseline="majority")

    assert records[0]["gold_label"] == "contradiction"
    assert records[0]["predicted_label"] == "not_contradiction"


def test_normalize_contrasciview_polarity_overlap_threshold(tmp_path):
    csv_path = tmp_path / "contrasciview.csv"
    csv_path.write_text(
        ",Unnamed: 0,paper_id,pair_id,hypothesis,premise,aspect,s1,s2,line_pair,label\n"
        "0,0,ICLR_1,3,method accuracy improves,method accuracy decreases,soundness,positive,negative,\"(1, 2)\",c\n"
        "1,1,ICLR_2,4,writing is excellent,baseline experiment is flawed,clarity,positive,negative,\"(3, 4)\",n\n",
        encoding="utf-8",
    )

    records = normalize_contrasciview_csv(csv_path, baseline="polarity_overlap", overlap_threshold=0.20)

    assert records[0]["predicted_label"] == "contradiction"
    assert records[1]["predicted_label"] == "not_contradiction"
    assert records[0]["token_jaccard"] > records[1]["token_jaccard"]


def test_normalize_react_actionability_to_shared_schema():
    records = normalize_react_records(
        [
            {
                "id": "react-1",
                "comment_text": "Please add a stronger retrieval baseline and report runtime.",
                "actionability_label": "actionable",
                "aspect": "experiments",
            }
        ]
    )

    assert records[0]["schema_version"] == "external-scoring-record-v0.1"
    assert records[0]["dataset"] == "ReAct"
    assert records[0]["dimension"] == "actionability"
    assert records[0]["gold_label"] == "actionable"
    assert records[0]["mapped_score"] == 0.9
    assert records[0]["predicted_label"] == "actionable"


def test_normalize_react_specificity_when_specificity_label_is_available():
    records = normalize_react_records(
        [
            {
                "id": "react-2",
                "comment_text": "The novelty claim in Section 3 is vague.",
                "specificity_label": "specific",
            }
        ],
        dimension="specificity",
    )

    assert records[0]["dimension"] == "specificity"
    assert records[0]["gold_label"] == "specific"


def test_normalize_substanreview_maps_evidence_labels():
    records = normalize_substanreview_records(
        [
            {
                "task_id": "sub-1",
                "claim_text": "The analysis is under-supported.",
                "evidence_text": "Reviewer cites the missing ablation table.",
                "substantiation_label": "substantiated",
            }
        ]
    )

    assert records[0]["dataset"] == "SubstanReview"
    assert records[0]["dimension"] == "substantiation"
    assert records[0]["context_text"] == "Reviewer cites the missing ablation table."
    assert records[0]["mapped_score"] == 0.9


def test_normalize_disapere_and_rbtact_to_rebuttal_robustness():
    disapere = normalize_disapere_records(
        [
            {
                "task_id": "dis-1",
                "review_comment": "The baseline is missing.",
                "rebuttal_text": "We will add the baseline comparison.",
                "stance": "partially_addresses",
            }
        ]
    )
    rbtact = normalize_rbtact_records(
        [
            {
                "task_id": "rbt-1",
                "review_comment": "Clarify the theorem assumptions.",
                "response_text": "We revised the theorem statement.",
                "rebuttal_action": "revision",
            }
        ]
    )

    assert disapere[0]["dimension"] == "rebuttal_robustness"
    assert disapere[0]["gold_label"] == "partially_addresses"
    assert rbtact[0]["dataset"] == "RbtAct"
    assert rbtact[0]["gold_label"] == "resolved_or_weakened"
