from pathlib import Path


def test_frontend_is_api_first_with_static_public_scorecard_fallback():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "SECONDOPINION_API_BASE" in html
    assert "https://secondopinion.smartselling.work" in html
    assert "id=\"topResults\"" in html
    assert "/api/conferences/ICLR/papers" in html
    assert "/api/papers/${encodeURIComponent(paperId)}/scorecard" in html
    assert "./demos/reviewer_public_scorecard_v0.1.json" in html
    assert "data-paper-result-index" in html

def test_frontend_search_does_not_treat_plain_words_as_paper_ids():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "looksLikeOpenReviewId" in html
    assert "{10,}" in html
    assert "/[A-Z0-9_-]/" in html
