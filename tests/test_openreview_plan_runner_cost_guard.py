from secondopinion.openreview_plan_runner import render_plan_runner_markdown, run_plan_steps, submit_batch_cost


def submit_step():
    return {
        "venue_id": "ICLR",
        "name": "submit_batch",
        "status": "pending",
        "command": "python -m secondopinion.tools.submit_scoring_batch --input data/batch.jsonl --manifest data/manifest.json --output data/submission.json",
        "writes": ["data/submission.json"],
    }


def test_submit_batch_cost_reads_manifest(tmp_path):
    manifest = tmp_path / "data" / "manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"estimated_batch_cost_usd": 1.25}', encoding="utf-8")

    cost, reason = submit_batch_cost(submit_step(), cwd=tmp_path)

    assert cost == 1.25
    assert reason == ""


def test_runner_blocks_submit_batch_over_cost_limit(tmp_path):
    manifest = tmp_path / "data" / "manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"estimated_batch_cost_usd": 12.5}', encoding="utf-8")

    result = run_plan_steps([submit_step()], cwd=tmp_path, max_submit_cost_usd=10)

    assert result["status_counts"] == {"blocked_cost_limit": 1}
    assert result["steps"][0]["estimated_batch_cost_usd"] == 12.5
    assert result["steps"][0]["max_submit_cost_usd"] == 10


def test_runner_allows_submit_batch_below_cost_limit_dry_run(tmp_path):
    manifest = tmp_path / "data" / "manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"estimated_batch_cost_usd": 2.5}', encoding="utf-8")

    result = run_plan_steps([submit_step()], cwd=tmp_path, max_submit_cost_usd=10)

    assert result["status_counts"] == {"dry_run": 1}
    assert result["steps"][0]["estimated_batch_cost_usd"] == 2.5


def test_runner_blocks_unknown_submit_batch_cost(tmp_path):
    result = run_plan_steps([submit_step()], cwd=tmp_path, max_submit_cost_usd=10)

    assert result["status_counts"] == {"blocked_cost_unknown": 1}
    assert result["steps"][0]["reason"] == "missing_manifest"


def test_plan_runner_markdown_includes_cost_block(tmp_path):
    manifest = tmp_path / "data" / "manifest.json"
    manifest.parent.mkdir()
    manifest.write_text('{"estimated_batch_cost_usd": 12.5}', encoding="utf-8")
    result = run_plan_steps([submit_step()], cwd=tmp_path, max_submit_cost_usd=10)

    markdown = render_plan_runner_markdown(result)

    assert "blocked_cost_limit" in markdown
    assert "12.5000" in markdown
