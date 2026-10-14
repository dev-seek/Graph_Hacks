"""Port 1 of 5 (spec §17.1): LLMPort and EmbeddingPort live in app.llm.port; re-exported here."""

from app.llm.port import EmbeddingPort, LLMPort

__all__ = ["EmbeddingPort", "LLMPort"]
