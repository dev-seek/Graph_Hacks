"""Thin alias so `service` imports one name (keeps graph.py's relaxed typing in one module)."""

from app.agents.graph import build_agent as build_agent_graph

__all__ = ["build_agent_graph"]
