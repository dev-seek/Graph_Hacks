import importlib.util
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("review_check", ROOT / "scripts" / "review_check.py")
assert spec and spec.loader
rc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rc)


def _staged(tmp: Path) -> Path:
    d = tmp / "review"
    d.mkdir()
    shutil.copy(ROOT / "review" / "safety_rules.yaml", d)
    shutil.copy(ROOT / "review" / "negatives.yaml", d)
    for name in ("demo_stories.md", "doctor_letters.md"):
        src = ROOT / "review" / name
        if "FILL_ME" in src.read_text(encoding="utf-8"):
            src = ROOT / ".build" / "drafts" / name
        shutil.copy(src, d)
    return d


def test_drafts_only_fail_for_not_reviewed(tmp_path: Path) -> None:
    results = rc.check_all(_staged(tmp_path))
    assert all(p == ["not yet REVIEWED"] for p in results.values()), results


def test_reviewed_line_passes_status(tmp_path: Path) -> None:
    d = _staged(tmp_path)
    for f in d.iterdir():
        lines = f.read_text(encoding="utf-8").splitlines()
        lines[0] = "# STATUS: REVIEWED by Tester on 2026-10-20"
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert all(not p for p in rc.check_all(d).values())


def test_fill_me_and_wildcard_negation_detected(tmp_path: Path) -> None:
    d = _staged(tmp_path)
    neg = d / "negatives.yaml"
    neg.write_text(neg.read_text(encoding="utf-8") + "# FILL_ME\n", encoding="utf-8")
    assert "FILL_ME leftovers" in rc.check_all(d)["negatives.yaml"]
    rules = d / "safety_rules.yaml"
    rules.write_text(
        rules.read_text(encoding="utf-8").replace(r"\bno rash\b", r"\bno .* rash\b"),
        encoding="utf-8",
    )
    assert any("wildcard" in p for p in rc.check_all(d)["safety_rules.yaml"])
