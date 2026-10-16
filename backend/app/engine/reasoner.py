"""Graph-first reasoner (AGENTS.md rule 4): runs the Cypher registry every round, then maths.

Fails closed: if FalkorDB is unreachable or a query errors or times out, `GraphUnavailable` is
raised (the API maps it to HTTP 503). No code path produces candidates without the graph.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from falkordb import Graph
from redis.exceptions import RedisError

from app.engine.config import tuned_params
from app.engine.planner import Askable, Plan, PlannerInput, plan_round
from app.engine.scoring import (
    Finding,
    Params,
    Rows,
    ScoreResult,
    TermMeta,
    candidate_ids,
    score_round,
)
from app.graph.client import rows as run
from app.llm.lexicon import violations

MAX_DEPTH = 20
MIN_ASKABLE_DEPTH = 3
TOP_CANDIDATES = 50
ANCESTOR_TIMEOUT_MS = 10_000


def parent_askable(row: dict[str, Any]) -> bool:
    """A question a parent can be shown (ADR-0011).

    Wording must pass the lexicon; a home question also needs a real lay synonym, otherwise its
    label is raw medical jargon that a parent cannot answer.
    """
    text = f"{row['question']} {row.get('plain') or ''}"
    if violations(text):
        return False
    return row["obs"] != "home" or " | " in (row.get("lay") or "")


class GraphUnavailable(RuntimeError):
    """FalkorDB cannot answer: the API returns 503 rather than guessing."""


def _run(graph: Graph, name: str, params: dict[str, Any], timeout_ms: int | None = None):
    try:
        return run(graph, name, params, timeout_ms)
    except (RedisError, OSError, TimeoutError) as exc:
        raise GraphUnavailable(f"{name}: {exc}") from exc


@dataclass
class AncestorCache:
    """The one in-memory structure the rules allow (spec §7): term -> {term} + ancestors."""

    ancestors: dict[str, set[str]] = field(default_factory=dict[str, set[str]])

    @classmethod
    def load(cls, graph: Graph) -> AncestorCache:
        out: dict[str, set[str]] = {}
        for depth in range(MAX_DEPTH):
            batch = _run(
                graph,
                "q3d_ancestor_cache",
                {"min_depth": depth, "max_depth": depth + 1},
                ANCESTOR_TIMEOUT_MS,
            )
            for r in batch:
                out[str(r["id"])] = {str(a) for a in r["ancestors"]}
        if not out:
            raise GraphUnavailable("ancestor cache is empty: kb not loaded")
        return cls(out)


class Reasoner:
    def __init__(
        self, graph: Graph, cache: AncestorCache | None = None, params: Params | None = None
    ) -> None:
        self.graph = graph
        self.params = params or tuned_params()
        self.cache = cache or AncestorCache.load(graph)
        self._prior_total: float | None = None

    @property
    def prior_total(self) -> float:
        if self._prior_total is None:
            r = _run(self.graph, "q2g_prior_total", {})
            self._prior_total = float(r[0]["total"])
        return self._prior_total

    def prune(self, findings: Sequence[Finding]) -> list[Finding]:
        """Q1: drop present ancestors of other present terms, absent descendants of absent terms."""
        present = sorted({f.term for f in findings if f.status == "present"})
        absent = sorted({f.term for f in findings if f.status == "absent"})
        drop: set[tuple[str, str]] = set()
        if len(present) > 1:
            red = _run(self.graph, "q1a_redundant_present", {"present": present})
            drop |= {("present", str(r["redundant"])) for r in red}
        if len(absent) > 1:
            red = _run(self.graph, "q1b_redundant_absent", {"absent": absent})
            drop |= {("absent", str(r["redundant"])) for r in red}
        return [f for f in findings if (f.status, f.term) not in drop]

    def retrieve(self, findings: Sequence[Finding]) -> Rows:
        present = sorted({f.term for f in findings if f.status == "present"})
        absent = sorted({f.term for f in findings if f.status == "absent"})
        out = Rows(prior_total_raw=self.prior_total)
        if present:
            for fid in present:  # one query per finding: see docs/VERIFIED.md (UNWIND quirk)
                for r in _run(self.graph, "q2a_exact_or_specific", {"fid": fid}):
                    key = (str(r["finding"]), str(r["disease"]))
                    out.exact[key] = float(r["F"])
                    out.prior_raw[key[1]] = float(r["prior"])
            for r in _run(self.graph, "q2b_broader", {"present": present}):
                out.broader.append(r)
                out.prior_raw.setdefault(str(r["disease"]), float(r["prior"]))
            for r in _run(self.graph, "q2c_not_present", {"present": present}):
                out.not_present.add((str(r["finding"]), str(r["disease"])))
                out.prior_raw.setdefault(str(r["disease"]), float(r["prior"]))
        cands = sorted(candidate_ids(out))
        if absent and cands:
            for fid in absent:
                for r in _run(self.graph, "q2d_absent", {"fid": fid, "candidates": cands}):
                    out.absent_F[(str(r["finding"]), str(r["disease"]))] = float(r["F"])
            for r in _run(self.graph, "q2e_not_absent", {"absent": absent, "candidates": cands}):
                out.not_absent.add((str(r["finding"]), str(r["disease"])))
        terms = sorted(set(present) | set(absent))
        if terms:
            for r in _run(self.graph, "q2f_term_meta", {"ids": terms}):
                out.meta[str(r["id"])] = TermMeta(float(r["bg"]), r["system"])
        return out

    def score(self, findings: Sequence[Finding]) -> tuple[list[Finding], ScoreResult]:
        pruned = self.prune(findings)
        return pruned, score_round(pruned, self.retrieve(pruned), self.params)

    def plan(
        self,
        findings: Sequence[Finding],
        result: ScoreResult,
        asked: set[str],
        age_months: int | None,
        round_kind: str,
    ) -> Plan:
        return plan_round(self.plan_input(findings, result, asked, age_months, round_kind))

    def plan_input(
        self,
        findings: Sequence[Finding],
        result: ScoreResult,
        asked: set[str],
        age_months: int | None,
        round_kind: str,
    ) -> PlannerInput:
        top = result.candidates[:TOP_CANDIDATES]
        annotations: dict[str, dict[str, float]] = {}
        if top:
            for r in _run(self.graph, "q3a_annotations", {"top": [c.disease for c in top]}):
                annotations.setdefault(str(r["disease"]), {})[str(r["term"])] = float(r["freq"])
        anc = self.cache.ancestors
        candidates_terms = {a for d in annotations.values() for t in d for a in anc.get(t, {t})}
        askable: dict[str, Askable] = {}
        if candidates_terms:
            ids = sorted(candidates_terms)
            for r in _run(self.graph, "q3b_askable", {"askable": ids}):
                if (
                    r["question"]
                    and r["obs"]
                    and (r["depth"] or 0) >= MIN_ASKABLE_DEPTH
                    and parent_askable(r)
                ):
                    askable[str(r["id"])] = Askable(
                        str(r["id"]),
                        r["obs"],
                        r["min_age"],
                        r["system"],
                        str(r["question"]),
                        float(r["bg"]),
                    )
        return PlannerInput(
            posteriors={c.disease: c.posterior for c in top},
            p_d0=result.p_d0,
            annotations=annotations,
            askable=askable,
            ancestors=anc,
            present={f.term for f in findings if f.status == "present"},
            absent={f.term for f in findings if f.status == "absent"},
            asked=asked,
            age_months=age_months,
            round_kind="post_doctor" if round_kind == "post_doctor" else "home",
            eps=self.params.eps,
        )
