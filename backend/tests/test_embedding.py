from __future__ import annotations

import math
from pathlib import Path

from app.llm.adapters.embedding import CachedEmbedder, FakeEmbedder, get_embedder


def _cos(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_fake_is_deterministic_unit_norm_and_384d() -> None:
    e = FakeEmbedder()
    v1, v2 = e.embed(["knee pain"]), e.embed(["knee pain"])
    assert v1 == v2
    assert len(v1[0]) == e.dim == 384
    assert math.isclose(_cos(v1[0], v1[0]), 1.0, rel_tol=1e-9)


def test_fake_shared_words_are_closer() -> None:
    a, b, c = FakeEmbedder().embed(["seizure at night", "night seizure", "dry skin"])
    assert _cos(a, b) > _cos(a, c)


class Counting(FakeEmbedder):
    calls = 0

    def embed(self, texts: list[str]) -> list[list[float]]:
        Counting.calls += len(texts)
        return super().embed(texts)


def test_cache_persists_and_avoids_recompute(tmp_path: Path) -> None:
    path = tmp_path / "emb.bin"
    Counting.calls = 0
    first = CachedEmbedder(Counting(), path).embed(["a b", "c d", "a b"])
    assert Counting.calls == 2
    second = CachedEmbedder(Counting(), path).embed(["c d", "a b"])
    assert Counting.calls == 2  # all served from disk
    assert second[1] == first[0] and second[0] == first[1]


def test_factory_returns_fake() -> None:
    assert get_embedder("fake").model_id == "fake-hash-384"
