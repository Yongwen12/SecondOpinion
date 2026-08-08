import json

from pathlib import Path


def test_frontend_is_api_first_without_static_demo_fallback():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "SECONDOPINION_API_BASE" in html
    assert "configuredApiBase" in html
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
    assert "Outrageous peer review,<br />ranked by readers." in html
    assert 'id="outrageBoard"' in html
    assert 'id="boardTabs"' in html
    assert 'id="hotThreadsLink"' in html
    assert "const BOARD_ORDER = ['latest', 'all-time']" in html
    assert "data-board-tab" in html
    assert "data-hot-threads" in html
    assert "data-row-rate" in html
    assert 'data-board-vote="outrageous"' in html
    assert 'data-board-vote="not_really"' in html
    assert '<span class="outrage-vote-label">Outrageous</span>' in html
    assert '<span class="outrage-vote-label">Not really</span>' in html
    assert "row.viewerVote" in html
    assert "outrage_latest" in html
    assert "outrage_all" in html
    assert "outrage_hot" in html
    assert "Vote before joining the discussion." in html
    assert "Vote before commenting" in html
    assert "data-comment-form" in html
    assert "data-sc-comment-form" in html
    assert "/reviewers/${encodeURIComponent(row.reviewerKey)}/comments" in html
    assert "/api/home?year=" in html
    assert '<option value="TMLR">TMLR</option>' in html
    assert '<option value="COLM">COLM</option>' in html
    assert '<option value="MIDL">MIDL</option>' in html
    assert "Review quality, ranked by the community." not in html
    assert "Red List" not in html
    assert "Black List" not in html
    assert "source.ai_take || source.aiTake" in html
    assert '<span>AI TAKE</span>' in html
    assert "outrage-ai-take" in html

def test_frontend_keeps_the_public_review_scope_concise():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "The public leaderboard for outrageous peer reviews" in html
    assert "Public official review excerpts via OpenReview" in html
    assert "ICLR" in html
    assert "ICML" in html
    assert "NeurIPS" in html
    assert "TMLR" in html
    assert "COLM" in html
    assert "MIDL" in html
    assert "Data coverage and scoring scope" not in html

def test_frontend_detail_view_is_an_outrage_thread_not_an_ai_scorecard():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert '.app-view .score-overview, .app-view .cloud-section, .app-view .trust-note { display: none; }' in html
    assert 'aria-label="Outrage discussion threads"' in html
    assert "OUTRAGE THREAD &middot;" in html
    assert "escapeHtml(comment.view)" in html
    assert "escapeHtml(reviewer.summary)" in html
    assert "renderScorecardCommentsHtml(reviewer)" in html
    assert "Read the full review on OpenReview &rarr;" in html
    assert "Why this score &middot; AI dimensions" not in html
    assert "AI-scored review usefulness" not in html
    assert "`${reviewers.length} review threads`" in html
    assert "`${splitComments.length} public excerpts`" in html
    assert "function renderAll()" in html
    assert "renderPaperInfo();" in html

def test_frontend_error_states_use_current_coverage_language():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "Search covers 2025 public official reviews from ICLR, ICML, NeurIPS, TMLR, COLM, and MIDL." in html
    assert "Static leaderboards are still available; try again in a moment." in html
    assert "Paper is outside current 2025 public-review coverage" in html
    assert "const queued = await requestScoringJob" not in html
    assert "Could not load this paper's review threads" in html
    assert "Try an OpenReview id or a shorter title." not in html
    assert "Paper is not indexed yet" not in html


def test_frontend_keeps_votes_aligned_and_unselected_buttons_white_on_mobile():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "@media (max-width: 700px)" in html
    assert ".outrage-row { display: grid; grid-template-columns: 60px minmax(0, 1fr) 132px" in html
    assert ".outrage-social .outrage-votes { display: grid; grid-template-columns: repeat(2" in html
    assert "background: #fff; color: #111" in html
    assert ".outrage-social .outrage-vote.is-on" in html
    assert "background: #ff2a14; color: #fff" in html
    assert ".outrage-social .outrage-vote b { color: #ff2a14" in html
    assert "grid-template-areas: 'rank main' '. aside'" in html
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in html
    assert "overflow-wrap: anywhere" in html
    assert "min-width: 0" in html
    assert "width: 100%" in html

def test_frontend_static_home_data_is_real_2025_outrage_batch():
    payload = Path("frontend/data/home_2025.json").read_text(encoding="utf-8")
    data = json.loads(payload)

    assert data["audited_count"] == 99671
    assert set(data["leaderboards"]) == {"outrage_latest", "outrage_all", "outrage_hot"}
    assert len(data["leaderboards"]["outrage_latest"]) == 12
    assert len(data["leaderboards"]["outrage_all"]) == 12
    assert all("paper_id" in row and "reviewer_key" in row for row in data["leaderboards"]["outrage_latest"])
    assert all("votes" in row for row in data["leaderboards"]["outrage_all"])
    assert all(row.get("ai_take") for row in data["leaderboards"]["outrage_all"])
    latest_dates = [row["surfaced_at"] for row in data["leaderboards"]["outrage_latest"]]
    assert latest_dates == sorted(latest_dates, reverse=True)
    assert "Thank you for your helpful comments" not in payload
    assert "Updating Updating Updating Updating" not in payload
    assert "Author?Reviewer discussion phase" not in payload
    assert "We are delighted that our responses" not in payload


def test_frontend_has_optional_account_saved_paper_and_comment_controls():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "id=\"accountButton\"" in html
    assert "id=\"topAccountButton\"" in html
    assert "id=\"authModal\"" in html
    assert "data-auth-form" in html
    assert "data-auth-open" in html
    assert "data-auth-logout" in html
    assert "secondOpinion-userToken" in html
    assert "secondOpinion-sessionId" in html
    assert "X-SecondOpinion-Session" in html
    assert "Authorization = `Bearer ${authState.token}`" in html
    assert "`/api/auth/${authMode}`" in html
    assert "/api/auth/logout" in html
    assert "/api/me" in html

    assert "data-save-paper" in html
    assert "data-follow-venue" in html
    assert "/api/me/saved-papers/${encodeURIComponent(paperId)}" in html
    assert "/api/me/venue-subscriptions/${encodeURIComponent(venue)}" in html
    assert "renderPaperActions();" in html

    assert "can_edit" in html
    assert "data-comment-edit" in html
    assert "data-comment-delete" in html
    assert "mutateCommentFor(context.row, commentId, 'PATCH'" in html
    assert "mutateCommentFor(context.row, commentId, 'DELETE'" in html
    assert "/comments/${encodeURIComponent(commentId)}" in html
    assert "data-account-paper" in html
    assert "setPaperDeepLink" in html
    assert "window.addEventListener('popstate'" in html
    assert "publicReviewerQuality" in html
    assert "|| fb.humanCount" not in html
    assert "data-auth-delete" in html
    assert "/api/auth/account" in html

def test_frontend_exposes_source_attribution_disputes_and_trust_pages():
    html = Path("frontend/index.html").read_text(encoding="utf-8")

    assert "not the reviewer as a person" in html
    assert "Public official review excerpts via OpenReview" in html
    assert "Excerpt via OpenReview, CC BY 4.0" in html
    assert "openReviewUrl(reviewer.reviewId)" in html
    assert "score-dispute.yml" in html
    assert "./methodology.html" in html
    assert "./privacy.html" in html
    assert "./terms.html" in html

    methodology = Path("frontend/methodology.html").read_text(encoding="utf-8")
    privacy = Path("frontend/privacy.html").read_text(encoding="utf-8")
    terms = Path("frontend/terms.html").read_text(encoding="utf-8")
    assert "gpt-5.6-luna" in methodology
    assert "not yet a representative human gold-standard" in methodology
    assert "We do not attempt to identify anonymous reviewers" in privacy
    assert "Scores evaluate review text, not reviewers as people" in terms

def test_static_home_only_publishes_safe_outrage_surfaces():
    data = json.loads(Path("frontend/data/home_2025.json").read_text(encoding="utf-8"))
    rendered = json.dumps(data)

    assert set(data["leaderboards"]) == {"outrage_latest", "outrage_all", "outrage_hot"}
    assert len(data["leaderboards"]["outrage_latest"]) >= 8
    assert len(data["leaderboards"]["outrage_all"]) >= 8
    assert "Outrage Index" not in rendered
    assert "Weak Reject" not in rendered
    assert "first author suffered" not in rendered.lower()
    assert "kill a granny" not in rendered.lower()
    assert "will not be able to perform my reviews" not in rendered.lower()


def test_curated_outrage_feed_is_publishable_and_concise():
    data = json.loads(Path("frontend/data/outrage_feed_v2.json").read_text(encoding="utf-8"))

    assert data["schema_version"].startswith("outrage-feed-v2")
    assert data["count"] == 66 == len(data["items"])
    assert [row["feed_rank"] for row in data["items"]] == list(range(1, 67))
    assert all(row["outrage_score"] >= 70 for row in data["items"])
    assert all(4 <= len(row["ai_take"].split()) <= 15 for row in data["items"])
    assert len({row["ai_take"].lower() for row in data["items"]}) == 66
