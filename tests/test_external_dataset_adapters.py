from secondopinion.external_dataset_adapters import normalize_contrasciview_csv


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
