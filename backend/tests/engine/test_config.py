from app.engine.config import tuned_params, tuned_taus


def test_tuned_values_load_and_are_sane() -> None:
    p, t = tuned_params(), tuned_taus()
    assert 0 < p.eps < 1 and 0.5 <= p.pi0 < 1 and set(p.w) >= {"parent_story", "doctor_exam"}
    assert 0 < t.t0 < t.t1 <= t.t2 < 1
