
from rps.openai.litellm_runtime import LiteLLMResponses, LLMProviderConfig


def test_litellm_previous_response_replays_tool_calls(monkeypatch):
    captured_messages = []
    call_count = {"count": 0}

    def _fake_completion(**kwargs):
        call_count["count"] += 1
        captured_messages.append(kwargs["messages"])
        if call_count["count"] == 1:
            return {
                "choices": [
                    {
                        "message": {
                            "content": None,
                            "tool_calls": [
                                {
                                    "id": "call_1",
                                    "function": {
                                        "name": "workspace_get_latest",
                                        "arguments": "{\"artifact_type\":\"WEEK_PLAN\"}",
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {},
            }
        return {
            "choices": [
                {
                    "message": {
                        "content": "Coach final reply",
                    }
                }
            ],
            "usage": {},
        }

    monkeypatch.setattr("rps.openai.litellm_runtime.litellm.completion", _fake_completion)

    responses = LiteLLMResponses(
        LLMProviderConfig(
            api_key="test-key",
            base_url=None,
            org_id=None,
            project_id=None,
        )
    )

    first = responses.create(
        model="test-model",
        input=[{"role": "user", "content": "How was my week?"}],
        tools=[
            {
                "type": "function",
                "name": "workspace_get_latest",
                "description": "Fetch latest workspace artifact.",
                "parameters": {"type": "object", "properties": {}},
            }
        ],
    )

    second = responses.create(
        model="test-model",
        input=[
            {
                "type": "function_call_output",
                "call_id": "call_1",
                "name": "workspace_get_latest",
                "output": '{"ok": true}',
            }
        ],
        previous_response_id=first.id,
    )

    assert second.output_text == "Coach final reply"
    assert len(captured_messages) == 2
    assert captured_messages[1][0]["role"] == "assistant"
    assert captured_messages[1][0]["tool_calls"][0]["id"] == "call_1"
    assert captured_messages[1][1]["role"] == "tool"
    assert captured_messages[1][1]["tool_call_id"] == "call_1"
