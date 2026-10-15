from app.llm.adapters.fake import FakeAdapter
from app.llm.contract import ProfileResult, cheapest_passing, run_profile
from app.llm.settings import load_settings


def test_fake_plumbing_passes_for_text_tasks() -> None:
    s = load_settings()
    for task in ("extract_story", "read_document", "phrase_question", "safety_extra"):
        r = run_profile(FakeAdapter(), task, s.profile_name_for(task), s)  # type: ignore[arg-type]
        assert r.passes and r.n == 20


def test_cheapest_passing_ignores_failures() -> None:
    a = ProfileResult("t", "fast", n=20, valid=10, lexicon_ok=10, cost_usd=1.0)
    b = ProfileResult("t", "smart", n=20, valid=20, lexicon_ok=20, cost_usd=5.0)
    c = ProfileResult("t", "fast_advised", n=20, valid=20, lexicon_ok=20, cost_usd=3.0)
    assert cheapest_passing([a, b, c]) == {"t": "fast_advised"}
