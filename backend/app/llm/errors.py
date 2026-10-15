from __future__ import annotations


class LLMUnavailable(RuntimeError):
    """The adapter cannot answer (no key, cache miss, refusal, truncation, budget...)."""


class CacheMiss(LLMUnavailable):
    pass
