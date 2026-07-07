from pathlib import Path


def test_frontend_is_api_first_without_static_demo_fallback():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "SECONDOPINION_API_BASE" in html
    assert "https://secondopinion.smartselling.work" in html
    assert "id=\"topResults\"" in html
    assert "/api/conferences/${encodeURIComponent(conference)}/papers" in html
    assert "/api/papers/${encodeURIComponent(paperId)}/scorecard" in html
    assert "./demos/reviewer_public_scorecard_v0.1.json" not in html
    assert "data-paper-result-index" in html
    assert "showUnavailableSearch" in html
    assert "showNotIndexedPaper" in html


def test_frontend_search_does_not_treat_plain_words_as_paper_ids():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "looksLikeOpenReviewId" in html
    assert "{10,}" in html
    assert "/[A-Z0-9_-]/" in html


def test_frontend_has_community_home_entrypoint():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "Judge My Reviewers" in html
    assert 'id="outrageTitle"' not in html
    assert 'id="outrageSub"' not in html
    assert 'The <mark>Verdict</mark>' not in html
    assert "id=\"outrageBoard\"" in html
    assert "id=\"boardTabs\"" in html
    assert "data-board-tab" in html
    assert "data-board-row" in html
    assert "data-row-rate" in html
    assert "Rate a reviewer" in html
    assert "data-comment-form" in html
    assert "data-sc-comment-form" in html
    assert "/reviewers/${encodeURIComponent(row.reviewerKey)}/comments" in html
    assert "/api/home?conference=ICLR" in html
    assert "overall" in html
    assert "toxic" in html
    assert "helpful" in html
    assert "Review quality, ranked by the community." not in html
    assert "Red List" not in html
    assert "Black List" not in html
