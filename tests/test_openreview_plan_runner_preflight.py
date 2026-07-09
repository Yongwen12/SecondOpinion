from secondopinion.openreview_plan_runner import (
    all_path_outputs_exist,
    existing_outputs,
    missing_inputs,
    run_plan_steps,
)


def test_skip_existing_marks_step_when_all_file_outputs_exist(tmp_path):
    output = tmp_path / "data" / "out.json"
    output.parent.mkdir()
    output.write_text("{}", encoding="utf-8")
    steps = [
        {
            "venue_id": "ICLR",
            "name": "quality",
            "status": "pending",
            "command": "python -m tool --input data/in.json --output data/out.json",
            "writes": ["data/out.json"],
        }
    ]

    result = run_plan_steps(steps, cwd=tmp_path, skip_existing=True)

    assert result["status_counts"] == {"skipped_existing": 1}
    assert result["steps"][0]["existing_outputs"] == ["data/out.json"]


def test_database_env_write_is_not_treated_as_file_output(tmp_path):
    step = {
        "venue_id": "ICLR",
        "name": "ingest",
        "status": "pending",
        "command": "python -m tool --input data/in.json",
        "writes": ["SECONDOPINION_DATABASE_URL"],
    }

    assert existing_outputs(step, cwd=tmp_path) == []
    assert all_path_outputs_exist(step, cwd=tmp_path) is False


def test_check_inputs_blocks_missing_command_inputs(tmp_path):
    steps = [
        {
            "venue_id": "ICLR",
            "name": "quality",
            "status": "pending",
            "command": "python -m tool --input data/missing.json --output data/out.json",
            "writes": ["data/out.json"],
        }
    ]

    result = run_plan_steps(steps, cwd=tmp_path, check_inputs=True)

    assert result["status_counts"] == {"blocked_missing_input": 1}
    assert result["steps"][0]["missing_inputs"] == ["data/missing.json"]


def test_missing_inputs_ignores_non_path_placeholders(tmp_path):
    command = "python -m tool --batch-id YOUR_BATCH_ID --output data/out.json"

    assert missing_inputs(command, cwd=tmp_path) == []

def test_runner_blocks_openreview_step_without_auth(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENREVIEW_COOKIE", raising=False)
    monkeypatch.delenv("OPENREVIEW_COOKIE_FILE", raising=False)
    monkeypatch.delenv("OPENREVIEW_TOKEN", raising=False)
    monkeypatch.delenv("OPENREVIEW_TOKEN_FILE", raising=False)
    steps = [
        {
            "venue_id": "ICLR",
            "name": "pull",
            "status": "pending",
            "command": "python -m secondopinion.tools.openreview_pull --venue ICLR",
            "requires_openreview_auth": True,
        }
    ]

    result = run_plan_steps(steps)

    assert result["status_counts"] == {"blocked_missing_openreview_auth": 1}
    assert result["steps"][0]["reason"] == "missing_openreview_cookie_or_token"


def test_runner_blocks_openai_step_without_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    steps = [
        {
            "venue_id": "ICLR",
            "name": "submit_batch_dry_run",
            "status": "pending",
            "command": "python -m secondopinion.tools.submit_scoring_batch --input data/batch.jsonl",
            "requires_openai_key": True,
        }
    ]

    result = run_plan_steps(steps)

    assert result["status_counts"] == {"blocked_missing_openai_key": 1}
    assert result["steps"][0]["reason"] == "missing_openai_api_key"
