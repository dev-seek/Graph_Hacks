"""Embedding adapters behind `EmbeddingPort` (spec §10.8): local bge-small (CPU), a deterministic
fake for tests, and an on-disk cache so `make kb` re-runs do not re-embed unchanged text."""

from __future__ import annotations

import hashlib
import math
import re
import struct
from pathlib import Path
from typing import Any

from app.llm.port import EmbeddingPort

BGE_MODEL = "BAAI/bge-small-en-v1.5"
BGE_DIM = 384
_TOKEN = re.compile(r"[a-z0-9]+")


def _normalise(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(x * x for x in vec))
    return [x / norm for x in vec] if norm else vec


class FakeEmbedder:
    """Deterministic hashed bag-of-words vectors: shared words give a positive cosine.

    Needs no model download, so unit and integration tests (and CI) can use it.
    """

    model_id = "fake-hash-384"

    def __init__(self, dim: int = BGE_DIM) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for text in texts:
            vec = [0.0] * self.dim
            for tok in _TOKEN.findall(text.lower()):
                h = hashlib.sha256(tok.encode()).digest()
                idx = int.from_bytes(h[:4], "big") % self.dim
                vec[idx] += 1.0 if h[4] & 1 else -1.0
            out.append(_normalise(vec))
        return out


class FastEmbedder:
    """bge-small-en-v1.5 through fastembed (ONNX, CPU). Imported lazily: it downloads the model."""

    model_id = BGE_MODEL
    dim = BGE_DIM

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir
        self._model: Any = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if self._model is None:
            from fastembed import TextEmbedding

            self._model = TextEmbedding(
                model_name=self.model_id,
                cache_dir=str(self._cache_dir) if self._cache_dir else None,
            )
        return [[float(x) for x in v] for v in self._model.embed(texts)]


class CachedEmbedder:
    """Wraps any embedder with an append-only binary cache keyed by (model, text hash)."""

    def __init__(self, inner: EmbeddingPort, path: Path) -> None:
        self._inner = inner
        self._path = path
        self.dim = inner.dim
        self.model_id = inner.model_id
        self._mem: dict[str, list[float]] = {}
        self._load()

    def _key(self, text: str) -> str:
        return hashlib.sha256(f"{self.model_id}\0{text}".encode()).hexdigest()

    def _load(self) -> None:
        if not self._path.exists():
            return
        rec = 32 + 4 * self.dim
        data = self._path.read_bytes()
        for off in range(0, len(data) - rec + 1, rec):
            key = data[off : off + 32].hex()
            self._mem[key] = list(struct.unpack(f"<{self.dim}f", data[off + 32 : off + rec]))

    def embed(self, texts: list[str]) -> list[list[float]]:
        keys = [self._key(t) for t in texts]
        missing = [i for i, k in enumerate(keys) if k not in self._mem]
        todo: dict[str, str] = {}
        for i in missing:
            todo.setdefault(keys[i], texts[i])
        if todo:
            vecs = self._inner.embed(list(todo.values()))
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("ab") as fh:
                for key, vec in zip(todo, vecs, strict=True):
                    packed = struct.pack(f"<{self.dim}f", *vec)
                    self._mem[key] = list(
                        struct.unpack(f"<{self.dim}f", packed)
                    )  # float32 round-trip
                    fh.write(bytes.fromhex(key) + packed)
        return [self._mem[k] for k in keys]


def get_embedder(kind: str = "bge", cache_path: Path | None = None) -> EmbeddingPort:
    inner: EmbeddingPort = FakeEmbedder() if kind == "fake" else FastEmbedder()
    return CachedEmbedder(inner, cache_path) if cache_path else inner
