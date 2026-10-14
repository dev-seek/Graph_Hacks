"""Rank metrics with bootstrap 95% CIs (spec §14)."""

from __future__ import annotations

import random
import statistics
from collections.abc import Callable, Sequence

Rank = int | None  # 1-based rank of the target; None = not retrieved
BOOTSTRAP_N = 1000
SEED = 20260901


def top_k(ranks: Sequence[Rank], k: int) -> float:
    return sum(1 for r in ranks if r is not None and r <= k) / len(ranks) if ranks else 0.0


def mrr(ranks: Sequence[Rank]) -> float:
    return sum(1.0 / r for r in ranks if r is not None) / len(ranks) if ranks else 0.0


def median_rank(ranks: Sequence[Rank]) -> float:
    if not ranks:
        return float("nan")
    return float(statistics.median(float("inf") if r is None else r for r in ranks))


def bootstrap_ci(
    ranks: Sequence[Rank],
    stat: Callable[[Sequence[Rank]], float],
    n: int = BOOTSTRAP_N,
    seed: int = SEED,
) -> tuple[float, float]:
    if not ranks:
        return (float("nan"), float("nan"))
    rng = random.Random(seed)  # noqa: S311 (statistics, not security)
    m = len(ranks)
    vals = sorted(stat([ranks[rng.randrange(m)] for _ in range(m)]) for _ in range(n))
    return (vals[int(0.025 * n)], vals[min(n - 1, int(0.975 * n))])


def summarise(ranks: Sequence[Rank]) -> dict[str, float]:
    out: dict[str, float] = {"n": float(len(ranks))}
    fns: list[tuple[str, Callable[[Sequence[Rank]], float]]] = [
        ("top1", lambda r: top_k(r, 1)),
        ("top3", lambda r: top_k(r, 3)),
        ("top10", lambda r: top_k(r, 10)),
        ("mrr", mrr),
    ]
    for name, fn in fns:
        out[name] = fn(ranks)
        lo, hi = bootstrap_ci(ranks, fn)
        out[f"{name}_lo"], out[f"{name}_hi"] = lo, hi
    out["median_rank"] = median_rank(ranks)
    return out


def paired_diff_ci(
    a: Sequence[Rank],
    b: Sequence[Rank],
    stat: Callable[[Sequence[Rank]], float],
    n: int = BOOTSTRAP_N,
    seed: int = SEED,
) -> tuple[float, float]:
    """95% CI of stat(a) - stat(b) over the same cases (paired bootstrap)."""
    if not a or len(a) != len(b):
        return (float("nan"), float("nan"))
    rng = random.Random(seed)  # noqa: S311
    m = len(a)
    diffs: list[float] = []
    for _ in range(n):
        idx = [rng.randrange(m) for _ in range(m)]
        diffs.append(stat([a[i] for i in idx]) - stat([b[i] for i in idx]))
    diffs.sort()
    return (diffs[int(0.025 * n)], diffs[min(n - 1, int(0.975 * n))])
