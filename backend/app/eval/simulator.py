"""Simulated parent (spec §14, no LLM): answers from a case's recorded features."""

from __future__ import annotations

import random
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from typing import Literal

Answer = Literal["yes", "no", "unsure"]
FLIP_TO_UNSURE = 0.05
STORY_MAX = 3
STORY_MIN = 2


@dataclass(frozen=True)
class SimFeature:
    term: str
    onset_months: float | None = None


class SimParent:
    """`yes` if q or a descendant is present (5% flipped to unsure); `no` if q or an ancestor is
    explicitly excluded; otherwise `unsure` (1 - no_rate) / `no` (no_rate)."""

    def __init__(
        self,
        present: list[SimFeature],
        excluded: Collection[str],
        ancestors: Mapping[str, set[str]],
        *,
        no_rate: float = 0.10,
        seed: int = 0,
    ) -> None:
        self.present = present
        self.excluded = set(excluded)
        self.anc = ancestors
        self.no_rate = no_rate
        self.rng = random.Random(seed)  # noqa: S311 (simulation, not security)

    def _present_at_or_below(self, q: str) -> bool:
        return any(q in self.anc.get(f.term, {f.term}) for f in self.present)

    def _excluded_at_or_above(self, q: str) -> bool:
        return bool((self.anc.get(q, {q}) & self.excluded) or q in self.excluded)

    def answer(self, q: str) -> Answer:
        if self._present_at_or_below(q):
            return "unsure" if self.rng.random() < FLIP_TO_UNSURE else "yes"
        if self._excluded_at_or_above(q):
            return "no"
        return "no" if self.rng.random() < self.no_rate else "unsure"

    def story(self, home_terms: Collection[str]) -> list[str]:
        """2-3 present home-observable features, earliest onset first (unknown onset last)."""
        home = [f for f in self.present if f.term in home_terms]
        pool = home if len(home) >= STORY_MIN else list(self.present)
        pool = sorted(pool, key=lambda f: (f.onset_months is None, f.onset_months or 0.0, f.term))
        return [f.term for f in pool[:STORY_MAX]]
