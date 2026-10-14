"""IS_A structure maths at kb build time: ancestors, depth, system, bg and ic (spec §7)."""

from __future__ import annotations

import math
from collections import deque
from collections.abc import Iterable

from pydantic import BaseModel


class Structure(BaseModel):
    ancestors: dict[str, frozenset[str]]
    depth: dict[str, int]
    system: dict[str, str]


class TermStats(BaseModel):
    bg: float
    ic: float
    n_diseases: int


def build_structure(parents: dict[str, list[str]], pheno_root: str) -> Structure:
    ancestors: dict[str, frozenset[str]] = {}

    def anc(term: str, stack: frozenset[str] = frozenset()) -> frozenset[str]:
        if term in ancestors:
            return ancestors[term]
        out: set[str] = set()
        for p in parents.get(term, []):
            if p in stack or p == term:
                continue
            out.add(p)
            out |= anc(p, stack | {term})
        ancestors[term] = frozenset(out)
        return ancestors[term]

    for t in parents:
        anc(t)

    children: dict[str, list[str]] = {}
    for child, plist in parents.items():
        for p in plist:
            children.setdefault(p, []).append(child)
    depth: dict[str, int] = {pheno_root: 0}
    queue: deque[str] = deque([pheno_root])
    while queue:
        cur = queue.popleft()
        for ch in children.get(cur, []):
            if ch not in depth:
                depth[ch] = depth[cur] + 1
                queue.append(ch)

    top = sorted(c for c in children.get(pheno_root, []))
    system: dict[str, str] = {}
    for t in depth:
        if t == pheno_root:
            continue
        if t in top:
            system[t] = t
            continue
        reach = ancestors.get(t, frozenset()) | {t}
        system[t] = min(x for x in top if x in reach)
    return Structure(ancestors=ancestors, depth=depth, system=system)


def annotation_stats(
    structure: Structure, annotations: Iterable[tuple[str, str, float]], floor: float = 1e-4
) -> dict[str, TermStats]:
    best: dict[str, dict[str, float]] = {}  # term -> disease -> max freq (propagated upward)
    diseases: set[str] = set()
    for disease, term, freq in annotations:
        if term not in structure.ancestors:
            continue
        diseases.add(disease)
        for t in (term, *structure.ancestors[term]):
            per = best.setdefault(t, {})
            if freq > per.get(disease, 0.0):
                per[disease] = freq
    n = max(len(diseases), 1)
    out: dict[str, TermStats] = {}
    for t in structure.ancestors:
        per = best.get(t, {})
        n_d = sum(1 for f in per.values() if f > 0)
        bg = max(sum(per.values()) / n, floor)
        out[t] = TermStats(bg=bg, ic=-math.log(max(n_d, 1) / n), n_diseases=n_d)
    return out
