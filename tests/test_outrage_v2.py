from secondopinion.outrage_v2 import MODEL, normalize_result, request_for_task, schema


def test_schema_has_strict_outage_types():
    value = schema()
    assert value["additionalProperties"] is False
    assert "NOT_OUTRAGEOUS" in value["properties"]["primary_type"]["enum"]
    assert "EMPTY_REVIEW" in value["properties"]["primary_type"]["enum"]


def test_normalize_result_enforces_threshold_and_type():
    value = normalize_result(
        {
            "outrageous": True,
            "outrage_score": 61,
            "primary_type": "PERSONAL_ATTACK",
            "secondary_type": "EMPTY_REVIEW",
            "quote": " x ",
            "roast": " y ",
            "reason": " z ",
        }
    )
    assert value["outrageous"] is False
    assert value["primary_type"] == "NOT_OUTRAGEOUS"
    assert value["secondary_type"] is None


def test_batch_request_uses_explicit_luna_model():
    request = request_for_task({"custom_id": "x", "messages": [{"role": "user", "content": "x"}]})
    assert request["body"]["model"] == MODEL == "gpt-5.6-luna"
    assert request["body"]["reasoning_effort"] == "none"
    assert request["url"] == "/v1/chat/completions"
