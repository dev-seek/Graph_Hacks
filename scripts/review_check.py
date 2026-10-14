"""make review-check: validate the human-reviewed inputs in review/ (exit 1, a reason per file).

Checks: first-line status, no FILL_ME leftovers, required rule ids, 40 cases / 3 stories /
2 letters, schema, and the safety corpus run through the real matcher. Cross-file checks:
Maya's story must fire `seizure_long_or_repeated`, Arjun's nothing, Kabir's no EMERGENCY rule;
no_escalation negatives fire no flag and no negative fires an EMERGENCY rule.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.safety.rules import RuleFile, match  # noqa: E402

NOT_REVIEWED = "not yet REVIEWED"
REVIEWED_RE = re.compile(r"^# STATUS: REVIEWED by \S.* on \S+")
STORY_FILE = "demo_stories.md"
LETTER_FILE = "doctor_letters.md"


def _status_problem(path: Path) -> str | None:
    first = path.read_text(encoding="utf-8").splitlines()[0] if path.stat().st_size else ""
    return None if REVIEWED_RE.match(first) else NOT_REVIEWED


def _check_rules(path: Path) -> tuple[list[str], RuleFile | None]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")
    if "FILL_ME" in text:
        return ["FILL_ME leftovers"], None
    try:
        rf = RuleFile.model_validate(yaml.safe_load(text))
    except Exception as exc:  # noqa: BLE001
        return [f"schema: {str(exc).splitlines()[0]}"], None
    ids = {r.id for r in rf.rules}
    for level, required in rf.required_ids.items():
        for rid in required:
            if rid not in ids:
                problems.append(f"missing rule {rid}")
            elif next(r for r in rf.rules if r.id == rid).level != level:
                problems.append(f"rule {rid} has wrong level")
    for r in rf.rules:
        for p in [*r.patterns, *r.negations]:
            try:
                re.compile(p)
            except re.error as exc:
                problems.append(f"{r.id}: bad regex {p!r}: {exc}")
        if any(".*" in n or ".+" in n for n in r.negations):
            problems.append(f"{r.id}: negation with unbounded wildcard")
        if not r.source.startswith("https://"):
            problems.append(f"{r.id}: source must be an https URL")
    if len(rf.corpus.should_flag) < 30 or len(rf.corpus.should_not_flag) < 30:
        problems.append("corpus needs >= 30 should_flag and >= 30 should_not_flag")
    for c in rf.corpus.should_flag:
        if c.expect_id not in [h.rule_id for h in match(rf.rules, c.text, c.age_months)]:
            problems.append(f"corpus miss: {c.expect_id}: {c.text[:50]}")
    for n in rf.corpus.should_not_flag:
        t, a = (n, None) if isinstance(n, str) else (n.text, n.age_months)
        if match(rf.rules, t, a):
            problems.append(f"corpus false alarm: {t[:50]}")
    return problems, rf


def _check_negatives(path: Path, rf: RuleFile | None) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if "FILL_ME" in text:
        return ["FILL_ME leftovers"]
    cases = yaml.safe_load(text).get("cases", [])
    problems: list[str] = []
    if len(cases) != 40:
        problems.append(f"need 40 cases, found {len(cases)}")
    seen: set[str] = set()
    for c in cases:
        cid = c.get("id", "?")
        if cid in seen:
            problems.append(f"duplicate id {cid}")
        seen.add(cid)
        if c.get("expected") not in ("no_escalation", "see_doctor_ok"):
            problems.append(f"{cid}: bad expected")
        if not isinstance(c.get("age_months"), int) or not 0 <= c["age_months"] <= 240:
            problems.append(f"{cid}: age_months must be 0-240")
        if not c.get("present") or not c.get("summary"):
            problems.append(f"{cid}: needs summary and present")
        if rf is not None:
            hits = match(rf.rules, ". ".join([c["summary"], *c["present"]]), c.get("age_months"))
            bad = (
                hits
                if c.get("expected") == "no_escalation"
                else [h for h in hits if h.level == "EMERGENCY"]
            )
            if bad:
                problems.append(f"{cid}: safety rule fires ({bad[0].rule_id})")
    return problems


def _split_sections(text: str) -> dict[str, str]:
    parts = re.split(r"^## ", text, flags=re.M)[1:]
    return {p.splitlines()[0].strip(): p for p in parts}


def _story(section: str) -> str:
    m = re.search(r"- story: \|\n(.*?)(?=\n- \w|\Z)", section, re.S)
    return " ".join(line.strip() for line in m.group(1).splitlines()) if m else ""


def _check_stories(path: Path, rf: RuleFile | None, neg_expected: dict[str, str]) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if "FILL_ME" in text:
        return ["FILL_ME leftovers"]
    problems: list[str] = []
    sections = _split_sections(text)
    for name in ("Kabir", "Arjun", "Maya"):
        sec = sections.get(name)
        if sec is None:
            problems.append(f"missing story {name}")
            continue
        m = re.search(r"- age_months: (\d+)", sec)
        story = _story(sec)
        words = len(story.split())
        if not m:
            problems.append(f"{name}: age_months missing")
        if not 80 <= words <= 150:
            problems.append(f"{name}: story is {words} words (need 80-150)")
        if rf is None or not m or not story:
            continue
        ids = [h for h in match(rf.rules, story, int(m.group(1)))]
        if name == "Maya" and "seizure_long_or_repeated" not in [h.rule_id for h in ids]:
            problems.append("Maya: story must fire seizure_long_or_repeated")
        if name == "Arjun":
            if ids:
                problems.append(f"Arjun: story fires {ids[0].rule_id}")
            nc = re.search(r"- negatives_case: (\S+)", sec)
            if not nc or neg_expected.get(nc.group(1)) != "no_escalation":
                problems.append("Arjun: negatives_case must name a no_escalation case")
        if name == "Kabir" and any(h.level == "EMERGENCY" for h in ids):
            problems.append("Kabir: story must not fire an EMERGENCY rule")
    return problems


def _check_letters(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if "FILL_ME" in text:
        return ["FILL_ME leftovers"]
    letters = [h for h in _split_sections(text) if h.startswith("Letter")]
    return [] if len(letters) == 2 else [f"need 2 letters, found {len(letters)}"]


def check_all(review_dir: Path) -> dict[str, list[str]]:
    results: dict[str, list[str]] = {}
    rules_path = review_dir / "safety_rules.yaml"
    neg_path = review_dir / "negatives.yaml"
    rf: RuleFile | None = None
    for name in ("safety_rules.yaml", "negatives.yaml", STORY_FILE, LETTER_FILE):
        if not (review_dir / name).exists():
            results[name] = ["file missing"]
    if "safety_rules.yaml" not in results:
        results["safety_rules.yaml"], rf = _check_rules(rules_path)
    neg_expected: dict[str, str] = {}
    if "negatives.yaml" not in results:
        results["negatives.yaml"] = _check_negatives(neg_path, rf)
        if "FILL_ME" not in neg_path.read_text(encoding="utf-8"):
            neg_expected = {
                c["id"]: c["expected"]
                for c in yaml.safe_load(neg_path.read_text()).get("cases", [])
            }
    if STORY_FILE not in results:
        results[STORY_FILE] = _check_stories(review_dir / STORY_FILE, rf, neg_expected)
    if LETTER_FILE not in results:
        results[LETTER_FILE] = _check_letters(review_dir / LETTER_FILE)
    for name, probs in results.items():
        path = review_dir / name
        if path.exists() and path.stat().st_size and (s := _status_problem(path)):
            probs.append(s)
    return results


def main(argv: list[str]) -> int:
    review_dir = Path(argv[1]) if len(argv) > 1 else ROOT / "review"
    results = check_all(review_dir)
    bad = False
    for name, probs in results.items():
        if probs:
            bad = True
            print(
                f"review/{name}: "
                + "; ".join(probs[:6])
                + (f" (+{len(probs) - 6} more)" if len(probs) > 6 else "")
            )
        else:
            print(f"review/{name}: ok (REVIEWED)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
