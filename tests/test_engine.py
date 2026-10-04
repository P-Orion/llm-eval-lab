import urllib.error
import pytest
from llm_eval_lab import engine
from llm_eval_lab.engine import Store, digest, extract, run_tasks, make_report


def manifest():
    return {"conditions": ["direct", "reasoned"], "seeds": [42], "timeout": 1}


def questions():
    return [
        {"id": 1, "question": "2+2?", "target": "4"},
        {"id": 2, "question": "3+3?", "target": "6"},
    ]


@pytest.mark.parametrize(
    "text,target",
    [
        ("work: 12\n#### 4", "4"),
        ("#### $1,200", "1.2E+3"),
        ("#### -2.5", "-2.5"),
        ("The answer is 4", None),
        ("#### 4\nextra prose", None),
        ("12, 4, 99", None),
    ],
)
def test_final_answer_is_explicit(text, target):
    assert extract(text) == target


def test_run_identity_changes_with_settings():
    a = manifest()
    b = {**a, "temperature": 0.7}
    assert digest(a) != digest(b)


def test_initialize_is_idempotent(tmp_path):
    store = Store(tmp_path / "runs.sqlite")
    run = store.initialize(manifest(), questions())
    assert (
        store.initialize(manifest(), questions()) == run and len(store.rows(run)) == 4
    )


def test_resume_does_not_repeat_completed_work(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "ROOT", tmp_path)
    store = Store(tmp_path / "runs.sqlite")
    run = store.initialize(manifest(), questions())
    calls = []

    def adapter(row):
        calls.append(row)
        return {"response": "#### " + row["target"], "eval_count": 2}

    report = run_tasks(store, run, adapter)
    run_tasks(store, run, adapter)
    assert len(calls) == 4 and report["summary"]["direct"]["task_success"] == 1


def test_failed_requests_stay_in_denominator(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "ROOT", tmp_path)
    store = Store(tmp_path / "runs.sqlite")
    run = store.initialize(manifest(), questions())

    def adapter(row):
        if row["qid"] == 1:
            raise urllib.error.URLError("transport down")
        return {"response": "#### 6"}

    report = run_tasks(store, run, adapter)
    assert report["summary"]["direct"]["scheduled"] == 2
    assert report["summary"]["direct"]["failed"] == 1
    assert report["summary"]["direct"]["task_success"] == 0.5
    assert report["summary"]["direct"]["accuracy_on_completed"] == 1


def test_crashed_lease_recovers_and_stale_worker_is_fenced(tmp_path, monkeypatch):
    store = Store(tmp_path / "runs.sqlite")
    run = store.initialize({"conditions": ["direct"], "seeds": [42]}, questions()[:1])
    clock = [100.0]
    monkeypatch.setattr(engine.time, "time", lambda: clock[0])
    old = store.claim(run, 10)
    clock[0] = 111.0
    new = store.claim(run, 10)
    assert new["qid"] == old["qid"] and new["attempts"] == 2
    with pytest.raises(RuntimeError):
        store.finish(old, response="#### 999")
    store.finish(new, response="#### 4")
    assert store.rows(run)[0]["response"] == "#### 4"


def test_rescore_uses_saved_responses_only(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "ROOT", tmp_path)
    store = Store(tmp_path / "runs.sqlite")
    run = store.initialize(manifest(), questions())
    run_tasks(store, run, lambda r: {"response": "work 900\n#### " + r["target"]})
    monkeypatch.setattr(
        engine,
        "request",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("No network allowed")),
    )
    assert make_report(store, run)["summary"]["reasoned"]["correct"] == 2


def test_wrong_answer_is_not_retried(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "ROOT", tmp_path)
    store = Store(tmp_path / "runs.sqlite")
    run = store.initialize(manifest(), questions())
    report = run_tasks(store, run, lambda r: {"response": "#### 999"})
    assert all(r["attempts"] == 1 for r in store.rows(run))
    assert report["summary"]["direct"]["correct"] == 0
