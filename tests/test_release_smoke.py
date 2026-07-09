import json

from secondopinion.release_smoke import HttpResponse, render_release_smoke_markdown, run_release_smoke


def response(payload, status=200):
    body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
    return HttpResponse(status=status, body=body, headers={}, elapsed_ms=7)


def test_release_smoke_passes_for_publishable_frontend_and_api():
    calls = []

    def getter(url, timeout=20.0):
        calls.append(url)
        if url == "https://pages.example/":
            return response(
                b"ICLR, ICML, NeurIPS, TMLR, COLM, and MIDL 99,671 scored official reviews https://secondopinion.smartselling.work"
            )
        if url == "https://api.example/health":
            return response({"status": "ok"})
        if url.startswith("https://api.example/api/home"):
            return response(
                {
                    "source": "static_home_2025",
                    "stats": {
                        "paper_count": 26749,
                        "review_count": 128723,
                        "scored_review_count": 99671,
                        "audited_count": 99671,
                    },
                    "leaderboards": {
                        "overall": [{}] * 8,
                        "toxic": [{}] * 8,
                        "helpful": [{}] * 8,
                        "red": [],
                        "black": [],
                    },
                }
            )
        if url.startswith("https://api.example/api/papers?query="):
            return response({"items": [{"paper_id": "p1"}]})
        if url == "https://api.example/api/papers/Ni4jNyroJZ/scorecard":
            return response({"reviewers": [{"reviewer_key": "R1"}], "comments": [{"chunk_id": "C1"}]})
        raise AssertionError(url)

    report = run_release_smoke(frontend_url="https://pages.example/", api_url="https://api.example", getter=getter)

    assert report["status"] == "passed"
    assert report["summary"] == {"check_count": 9, "failed_count": 0}
    assert any("/api/home" in call for call in calls)
    assert "api_home_static" in render_release_smoke_markdown(report)


def test_release_smoke_fails_for_stale_home_or_missing_copy():
    def getter(url, timeout=20.0):
        if url == "https://pages.example/":
            return response(b"old homepage")
        if url == "https://api.example/health":
            return response({"status": "ok"})
        if url.startswith("https://api.example/api/home"):
            return response({"source": "dynamic", "stats": {}, "leaderboards": {}})
        if url.startswith("https://api.example/api/papers?query="):
            return response({"items": []})
        if url == "https://api.example/api/papers/Ni4jNyroJZ/scorecard":
            return response({"reviewers": [], "comments": []})
        raise AssertionError(url)

    report = run_release_smoke(frontend_url="https://pages.example/", api_url="https://api.example", getter=getter)

    assert report["status"] == "failed"
    failed = {check["name"] for check in report["checks"] if not check["ok"]}
    assert {"frontend_coverage_copy", "api_home_static", "api_home_stats", "api_global_search", "api_scorecard"} <= failed
