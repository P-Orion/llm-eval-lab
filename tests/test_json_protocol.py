import json
import pytest
from llm_eval_lab import engine
from llm_eval_lab.engine import extract_json, Store, run_tasks


@pytest.mark.parametrize(
    "answer,expected",
    [("12", "12"), ("-2.5", "-2.5"), ("1,200", "1.2E+3"), ("NaN", None), ("1/2", None)],
)
def test_json_answer_is_numerical_and_finite(answer, expected):
    assert (
        extract_json(json.dumps({"work": "Ignored reasoning", "answer": answer}))
        == expected
    )


def test_json_does_not_fall_back_to_reasoning():
    assert extract_json('{"work":"the answer is 12","answer":"unknown"}') is None


def test_recorded_prompts_not_current_defaults_are_sent(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "ROOT", tmp_path)
    manifest = {
        "conditions": ["direct"],
        "seeds": [42],
        "timeout": 10,
        "model": "fixture",
        "model_digest": "digest",
        "base_url": "http://local",
        "prompts": {"direct": "IMMUTABLE PROMPT"},
        "temperature": 0.6,
        "num_predict": 32,
        "num_ctx": 100,
        "think": False,
    }
    store = Store(tmp_path / "runs.sqlite")
    run = store.initialize(manifest, [{"id": 1, "question": "2+2?", "target": "4"}])
    requests = []
    monkeypatch.setattr(engine, "model_digest", lambda *a: "digest")

    def request(url, body, timeout):
        requests.append(body)
        return {"response": "#### 4"}

    monkeypatch.setattr(engine, "request", request)
    run_tasks(store, run)
    assert requests[0]["prompt"] == "IMMUTABLE PROMPT\n\n2+2?"
