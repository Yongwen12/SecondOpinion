from pathlib import Path


def test_frontend_is_api_first_without_static_demo_fallback():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "SECONDOPINION_API_BASE" in html
    assert "https://secondopinion.smartselling.work" in html
    assert "id=\"topResults\"" in html
    assert "/api/conferences/ICLR/papers" in html
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

    assert "Review quality, ranked by the community." in html
    assert "id=\"homeRedList\"" in html
    assert "id=\"homeBlackList\"" in html
    assert "id=\"latestPaperList\"" in html
    assert "class=\"community-grid\"" in html
    assert "data-home-panel=\"recent\"" in html
    assert "data-home-panel=\"red\"" in html
    assert "data-home-board=\"recent\"" in html
    assert "Least Useful" in html
    assert "plainBand" in html
    assert "/api/home?conference=ICLR" in html
    assert "data-home-board-paper" in html
    assert "Needs Scrutiny" not in html
    assert "Red List" not in html
    assert "Black List" not in html
