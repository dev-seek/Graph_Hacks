"""Demo journeys (spec §4.5): pick dev cases, record the three families, replay them offline.

Recording drives the real service like a parent would, using a dev-split case as the simulated
parent (answers) and the REVIEWED story/letter texts. `LLM_MODE=record` stores model outputs in
`data/llm_cache`; with `LLM_MODE=off` the deterministic fallbacks are recorded instead. Query
embeddings are cached too, so replay needs no model download and no network.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agents.intake import fallback_doc, fallback_story, resolve_items
from app.agents.journey import JourneyResult, JourneyScript, run_journey
from app.agents.service import FamilyService
from app.agents.stories import load_letters, load_stories
from app.api.schemas import ParentExtractedFinding
from app.eval.cases import DevCase, load_dev_cases
from app.eval.cli import home_terms, make_sim
from app.eval.negatives import load_resolved
from app.eval.paths import ROOT
from app.eval.simulator import SimFeature, SimParent
from app.llm.port import EmbeddingPort

DEMO_DIR = ROOT / "data" / "demo"
EMBED_CACHE = DEMO_DIR / "query_embeddings.json"
NERVOUS_SYSTEM = "HP:0000707"
TOP_TRIES = 25
MIN_KABIR_ROUNDS = 2

JOURNEYS: dict[str, dict[str, str]] = {
    "kabir": {
        "name": "Kabir",
        "title": "Kabir: from a worried story to a specialist referral",
        "blurb": "Two home rounds, a doctor's letter, then notes ready for a specialist.",
        "expected": "specialist_step",
    },
    "arjun": {
        "name": "Arjun",
        "title": "Arjun: reassurance without an extra appointment",
        "blurb": "A common toddler habit that has settled; nothing needs a special visit.",
        "expected": "watching",
    },
    "maya": {
        "name": "Maya",
        "title": "Maya: an emergency stops everything else",
        "blurb": "A long seizure triggers the urgent screen first.",
        "expected": "urgent",
    },
}


class CachedEmbedder:
    """Query-vector cache: record with a real model once, replay with none (no network)."""

    dim = 384
    model_id = "demo-cached"

    def __init__(self, inner: EmbeddingPort | None, path: Path = EMBED_CACHE) -> None:
        self.inner = inner
        self.path = path
        self.cache: dict[str, list[float]] = (
            json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        )
        self.dirty = False

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            if t not in self.cache:
                if self.inner is None:
                    raise RuntimeError("query embedding not recorded")
                self.cache[t] = [round(x, 5) for x in self.inner.embed([t])[0]]
                self.dirty = True
            out.append(self.cache[t])
        return out

    def save(self) -> None:
        if self.dirty:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.cache, sort_keys=True), encoding="utf-8")


def related(a: str, b: str, anc: Mapping[str, set[str]]) -> bool:
    return a == b or b in anc.get(a, {a}) or a in anc.get(b, {b})


def related_to_any(term: str, others: list[str], anc: Mapping[str, set[str]]) -> bool:
    return any(related(term, o, anc) for o in others)


def accept_related(known: list[str], anc: Mapping[str, set[str]]) -> Any:
    """The parent keeps list items that sound right (here: related to the simulated child)."""

    def accept(items: list[ParentExtractedFinding], terms: dict[str, str]) -> list[str]:
        return [i.id for i in items if related_to_any(terms.get(i.id, ""), known, anc)]

    return accept


@dataclass
class Pick:
    case_id: str
    similarity: float
    n_present: int
    reached: str


def _systems(svc: FamilyService, dc: DevCase) -> set[str]:
    from app.graph.client import rows

    ids = [f.term_id for f in dc.case.present]
    return {
        str(r["system"]) for r in rows(svc.deps.kb, "q2f_term_meta", {"ids": ids}) if r["system"]
    }


def candidate_cases(
    svc: FamilyService, story_terms: list[str], limit: int
) -> list[tuple[float, DevCase]]:
    """Dev cases meeting Kabir's match criteria, best story overlap first."""
    anc = svc.deps.reasoner.cache.ancestors
    homes = home_terms(svc.deps.kb, load_dev_cases(svc.deps.kb))
    scored: list[tuple[float, DevCase]] = []
    for dc in load_dev_cases(svc.deps.kb):
        present = [f.term_id for f in dc.case.present]
        if len(present) < 8 or (dc.case.age_months or 0) > 240:
            continue
        sys_ = _systems(svc, dc)
        if NERVOUS_SYSTEM not in sys_ or len(sys_) < 2:
            continue
        if sum(1 for t in present if t in homes) < 3:
            continue
        prec = sum(related_to_any(t, present, anc) for t in story_terms) / max(len(story_terms), 1)
        cov = sum(related_to_any(t, story_terms, anc) for t in present) / len(present)
        f1 = 0.0 if prec + cov == 0 else 2 * prec * cov / (prec + cov)
        scored.append((round(f1, 4), dc))
    scored.sort(key=lambda x: (-x[0], x[1].case.case_id))
    return scored[:limit]


def story_terms_of(svc: FamilyService, *texts: str) -> list[str]:
    out: list[str] = []
    for i, t in enumerate(texts):
        items = fallback_story(t).items if i == 0 else fallback_doc(t).items
        out += [p.term_id for p in resolve_items(svc.deps, t, items, "x")]  # type: ignore[arg-type]
    return sorted(set(out))


def kabir_script(svc: FamilyService, dc: DevCase) -> JourneyScript:
    st, letter = load_stories()["Kabir"], load_letters()[1]
    sim = make_sim(dc, svc.deps.reasoner)
    known = [f.term_id for f in dc.case.present] + [f.term_id for f in dc.case.excluded]
    return JourneyScript(
        name="Kabir",
        story=st.story,
        age_months=st.age_months,
        sex="male",
        accept=accept_related(known, svc.deps.reasoner.cache.ancestors),
        answer=lambda term, text: sim.answer(term),
        letter=lambda s, fid: letter,
        advance_months=6,
        max_rounds=4,
    )


def arjun_script(svc: FamilyService) -> tuple[JourneyScript, str]:
    st = load_stories()["Arjun"]
    case = next(c for c in load_resolved() if c.id == st.negatives_case)
    present = [s.term for s in case.present if s.term]
    excluded = [s.term for s in case.absent if s.term]
    anc = svc.deps.reasoner.cache.ancestors
    sim = SimParent([SimFeature(t) for t in present], excluded, anc, no_rate=0.1, seed=7)
    return (
        JourneyScript(
            name="Arjun",
            story=st.story,
            age_months=st.age_months,
            sex="male",
            accept=accept_related(present + excluded, anc),
            answer=lambda term, text: sim.answer(term),
            max_rounds=3,
        ),
        case.id,
    )


def maya_script() -> JourneyScript:
    st = load_stories()["Maya"]
    return JourneyScript(name="Maya", story=st.story, age_months=st.age_months, sex="female")


def _record(
    jid: str, res: JourneyResult, mode: str, kb: str, extra: dict[str, Any]
) -> dict[str, Any]:
    meta = JOURNEYS[jid]
    return {
        "id": jid, "title": meta["title"], "blurb": meta["blurb"], "llm_mode": mode,
        "kb_version": kb, "final_phase": res.final_phase, "expected_phase": meta["expected"],
        "steps": res.steps, **extra,
    }  # fmt: skip


def run_all(svc: FamilyService, mode: str) -> tuple[dict[str, dict[str, Any]], dict[str, Pick]]:
    """Run the three journeys; returns recorded documents and the dev-case choices."""
    picks: dict[str, Pick] = {}
    out: dict[str, dict[str, Any]] = {}
    kb = svc.deps.kb_version
    st = load_stories()["Kabir"]
    terms = story_terms_of(svc, st.story, load_letters()[1])
    best: dict[str, Any] | None = None
    fallback: tuple[dict[str, Any], Pick] | None = None
    for sim_score, dc in candidate_cases(svc, terms, TOP_TRIES):
        res = run_journey(svc, kabir_script(svc, dc))
        pick = Pick(dc.case.case_id, sim_score, len(dc.case.present), res.final_phase)
        doc = _record("kabir", res, mode, kb, {"case_id": dc.case.case_id, "similarity": sim_score})
        if res.final_phase == JOURNEYS["kabir"]["expected"]:
            if res.rounds >= MIN_KABIR_ROUNDS:  # the reviewed path says "2 home rounds"
                best, picks["kabir"] = doc, pick
                break
            fallback = fallback or (doc, pick)
        svc.delete_family(res.family_id)
    if best is None and fallback is not None:
        best, picks["kabir"] = fallback[0], fallback[1]
    if best is None:
        raise RuntimeError("no dev case matched the Kabir criteria")
    out["kabir"] = best
    script, neg_id = arjun_script(svc)
    res = run_journey(svc, script)
    picks["arjun"] = Pick(neg_id, 1.0, 1, res.final_phase)
    out["arjun"] = _record("arjun", res, mode, kb, {"case_id": neg_id})
    res = run_journey(svc, maya_script())
    picks["maya"] = Pick("-", 1.0, 0, res.final_phase)
    out["maya"] = _record("maya", res, mode, kb, {"case_id": None})
    return out, picks


def save(docs: dict[str, dict[str, Any]]) -> None:
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    for jid, doc in docs.items():
        (DEMO_DIR / f"{jid}.json").write_text(
            json.dumps(doc, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8"
        )


def load_demo(jid: str) -> dict[str, Any]:
    return json.loads((DEMO_DIR / f"{jid}.json").read_text(encoding="utf-8"))


def fingerprint(doc: dict[str, Any]) -> list[tuple[str, str, str]]:
    """What a viewer would see, stripped of ids/timings: (screen, caption, key text)."""
    out: list[tuple[str, str, str]] = []
    for s in doc["steps"]:
        p = s["payload"]
        key = ""
        if "extraction_to_confirm" in p:
            key = "|".join(i["plain_label"] for i in p["extraction_to_confirm"])
        elif "questions" in p:
            key = "|".join(q["text"] for q in p["questions"])
        elif "gate" in p:
            key = p["gate"]["state"]
        elif "phase" in p:
            key = p["phase"]
        out.append((s["screen"], s["caption"], key))
    return out
