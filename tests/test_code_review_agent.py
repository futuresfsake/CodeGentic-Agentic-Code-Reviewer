"""Agent loop tests with a scripted client. No API key or network needed."""

import json
from contextlib import contextmanager
from types import SimpleNamespace

from code_review_agent import get_structured_review, run_review_agent
from review_schema import REVIEW_FORMAT
from review_tools import TOOLS, ReviewTarget


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []
        self.messages = SimpleNamespace(stream=self.stream)

    @contextmanager
    def stream(self, **params):
        self.requests.append({**params, "messages": list(params["messages"])})
        response = self.responses.pop(0)

        class Stream(list):
            def get_final_message(self):
                return response

        yield Stream()


def reply(stop_reason, *content):
    usage = SimpleNamespace(cache_read_input_tokens=0)
    return SimpleNamespace(stop_reason=stop_reason, content=list(content), usage=usage)


def tool_call():
    return SimpleNamespace(type="tool_use", id="t1", name="list_files", input={"path": "."})


def test_loop_returns_tool_results_then_stops(tmp_path):
    client = FakeClient(reply("tool_use", tool_call()), reply("end_turn"))
    messages = run_review_agent(client, ReviewTarget(str(tmp_path)))

    assert [m["role"] for m in messages] == ["user", "assistant", "user", "assistant"]
    assert messages[2]["content"][0]["tool_use_id"] == "t1"


def test_cut_off_turn_is_not_kept(tmp_path):
    client = FakeClient(reply("max_tokens", tool_call()))
    messages = run_review_agent(client, ReviewTarget(str(tmp_path)))

    assert [m["role"] for m in messages] == ["user"]


def test_structured_review_keeps_tools_and_sends_the_schema():
    review = {"overall_quality": "good", "findings": [], "summary": "ok"}
    text = SimpleNamespace(type="text", text=json.dumps(review))
    client = FakeClient(reply("end_turn", text))

    assert get_structured_review(client, [{"role": "user", "content": "hi"}]) == review
    request = client.requests[0]
    assert request["tools"] == TOOLS
    assert request["output_config"] == {"format": REVIEW_FORMAT}
    assert set(REVIEW_FORMAT) == {"type", "schema"}


def test_incomplete_review_is_reported():
    client = FakeClient(reply("max_tokens"))
    assert "max_tokens" in get_structured_review(client, [])["error"]
