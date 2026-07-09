from pathlib import Path


def test_frontend_is_api_first_without_static_demo_fallback():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "SECONDOPINION_API_BASE" in html
    assert "https://secondopinion.smartselling.work" in html
    assert "id=\"topResults\"" in html
    assert "/api/papers?query=" in html
    assert "/api/papers/${encodeURIComponent(paperId)}/scorecard" in html
    assert "./demos/reviewer_public_scorecard_v0.1.json" not in html
    assert "data-paper-result-index" in html
    assert "showUnavailableSearch" in html
    assert "showNotIndexedPaper" in html
    assert "safeJson(response)" in html
    assert "paper_not_found" in html
    assert "apiCredentialsMode" in html
    assert "credentials: apiCredentialsMode()" in html


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
    assert '<option value="TMLR">TMLR</option>' in html
    assert '<option value="COLM">COLM</option>' in html
    assert '<option value="MIDL">MIDL</option>' in html
    assert 'TMLR 2025</option>' in html
    assert 'COLM 2025</option>' in html
    assert 'MIDL 2025</option>' in html
    assert "data-comment-form" in html
    assert "data-sc-comment-form" in html
    assert "/reviewers/${encodeURIComponent(row.reviewerKey)}/comments" in html
    assert "/api/home?year=" in html
    assert "/api/papers?query=" in html
    assert "conference=${encodeURIComponent(selectedVenue)}" in html
    assert "conference=${encodeURIComponent(rateContext.conference)}" in html
    assert "/api/conferences/ICLR/papers?query=" not in html
    assert "/api/conferences/${encodeURIComponent(rateContext.conference)}/papers" not in html
    assert "ICLR 2022-2025 sample papers" not in html
    assert "Current 2025 coverage is ICLR, ICML, NeurIPS, TMLR, COLM, and MIDL" in html
    assert "/api/home?conference=ICLR" not in html
    assert "overall" in html
    assert "toxic" in html
    assert "helpful" in html
    assert "Review quality, ranked by the community." not in html
    assert "Red List" not in html
    assert "Black List" not in html


def test_frontend_discloses_2025_public_review_scope():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "Data coverage and scoring scope" in html
    assert "ICLR, ICML, NeurIPS, TMLR, COLM, and MIDL" in html
    assert "26,749 papers" in html
    assert "99,671 scored official reviews" in html
    assert "title, abstract, decision, and public official reviews only" in html
    assert "No PDF full text, author rebuttals, or admin comments" in html


def test_frontend_detail_view_handles_empty_and_untrusted_review_content():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "Themes will appear here when enough distinct review terms are available." in html
    assert "No public official review comments are available for this paper yet." in html
    assert "escapeHtml(metric.quote)" in html
    assert "escapeHtml(comment.view)" in html
    assert "escapeHtml(comment.ai)" in html
    assert "No reviewer metrics are available for this scorecard yet." in html
    assert "`${reviewers.length} reviewers`" in html
    assert "`${splitComments.length} comments`" in html
    assert "summary.reviewer_count ?? reviewers.length" not in html
    assert "function renderAll()" in html
    assert "renderPaperInfo();" in html


def test_frontend_error_states_use_current_coverage_language():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "Search covers 2025 public official reviews from ICLR, ICML, NeurIPS, TMLR, COLM, and MIDL." in html
    assert "Static leaderboards are still available; try again in a moment." in html
    assert "Paper is outside current 2025 public-review coverage" in html
    assert "Could not load this paper scorecard" in html
    assert "Try an OpenReview id or a shorter title." not in html
    assert "Paper is not indexed yet" not in html


def test_frontend_has_mobile_overflow_guards():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "@media (max-width: 420px)" in html
    assert ".outrage-row {" in html
    assert "grid-template-columns: 36px minmax(0, 1fr)" in html
    assert ".outrage-scorebox" in html
    assert "grid-column: 2" in html
    assert ".comment-row .vote-group" in html
    assert "grid-column: 1 / -1" in html
    assert "overflow-wrap: anywhere" in html
    assert ".score-main" in html
    assert "min-width: 0" in html
    assert "max-width: 100%" in html
    assert "grid-template-columns: 1fr" in html
    assert "grid-template-columns: minmax(0, 1fr)" in html
    assert "width: 100%" in html


def test_frontend_static_home_data_is_real_2025_batch():
    payload = Path("frontend/data/home_2025.json").read_text(encoding="utf-8")

    assert '"audited_count":99671' in payload
    assert '"overall"' in payload
    assert '"toxic"' in payload
    assert '"helpful"' in payload
    assert '"paper_id"' in payload
    assert '"reviewer_key"' in payload
    assert "Thank you for your helpful comments" not in payload
    assert "Author?Reviewer discussion phase" not in payload
    assert "We are delighted that our responses" not in payload

