"""MCP server (spec §12): four read-only tools over the same graph-first engine as the API.

Run: `python -m app.mcp.server` (stdio) or `python -m app.mcp.server http` (streamable HTTP).
Output is clinician-style and always carries the decision-support disclaimer.
"""

from __future__ import annotations

import sys
from typing import Any

from mcp.server.mcpserver import MCPServer
from redis.exceptions import ResponseError

from app.agents.deps import AgentDeps
from app.agents.reasoning import disease_names, term_names
from app.api.schemas import CLINICIAN_DISCLAIMER
from app.engine.scoring import Finding
from app.graph.client import rows

MAX_FINDINGS = 40
TOP = 10


def _findings(items: list[dict[str, str]]) -> list[Finding]:
    out: list[Finding] = []
    for it in items[:MAX_FINDINGS]:
        status = it.get("status", "present")
        if status not in ("present", "absent"):
            raise ValueError("status must be 'present' or 'absent'")
        out.append(Finding(str(it["term_id"]), status, "doctor_exam"))  # type: ignore[arg-type]
    return out


def resolve_phenotype(deps: AgentDeps, text: str) -> list[dict[str, Any]]:
    return [
        {"term_id": r.id, "name": r.name, "score": round(r.score, 4), "via": r.via}
        for r in deps.resolver.resolve(text[:500], k=5)
    ]


def rank_candidates(deps: AgentDeps, findings: list[dict[str, str]]) -> dict[str, Any]:
    _, res = deps.reasoner.score(_findings(findings))
    top = res.candidates[:TOP]
    names = disease_names(deps, [c.disease for c in top])
    return {
        "kb_version": deps.kb_version,
        "rare_mass": round(res.rare_mass, 6),
        "candidates": [
            {
                "rank": i + 1,
                "disease_id": c.disease,
                "name": names.get(c.disease, c.disease),
                "posterior": round(c.posterior, 6),
            }
            for i, c in enumerate(top)
        ],  # fmt: skip
        "disclaimer": CLINICIAN_DISCLAIMER,
    }


def explain_candidate(
    deps: AgentDeps, findings: list[dict[str, str]], disease_id: str
) -> dict[str, Any]:
    _, res = deps.reasoner.score(_findings(findings))
    cand = next((c for c in res.candidates if c.disease == disease_id), None)
    if cand is None:
        return {"disease_id": disease_id, "found": False, "disclaimer": CLINICIAN_DISCLAIMER}
    labels = term_names(deps, [t for t, _ in cand.support])
    items: list[dict[str, Any]] = []
    for term, lr in sorted(cand.support, key=lambda s: -abs(s[1]))[:8]:
        path: list[str] = []
        if lr > 0:
            r = rows(deps.kb, "q4_explain_path", {"finding": term, "disease": disease_id})
            if r:
                ids = [str(p) for p in r[0]["path"]]
                pn = term_names(deps, ids)
                path = [pn.get(p, p) for p in ids]
        items.append(
            {"term_id": term, "label": labels.get(term, term), "log_lr": round(lr, 3), "path": path}
        )
    name = disease_names(deps, [disease_id]).get(disease_id, disease_id)
    return {
        "disease_id": disease_id, "name": name, "found": True,
        "supporting": [i for i in items if i["log_lr"] > 0],
        "opposing": [i for i in items if i["log_lr"] <= 0],
        "disclaimer": CLINICIAN_DISCLAIMER,
    }  # fmt: skip


def centre_route_case(deps: AgentDeps, hpo_ids: list[str]) -> dict[str, Any]:
    """Look-alike cases + who solved them + protocol, from the `centre` graph (Q7)."""
    from app.centre.service import CentreService, suggest

    svc = CentreService(deps.db, lambda _n: deps.reasoner, None, deps.reasoner.cache.ancestors)
    try:
        look = svc.lookalikes_for(hpo_ids[:MAX_FINDINGS])
    except (ResponseError, FileNotFoundError):
        return {"available": False, "reason": "centre graph not loaded", "lookalikes": [],
                "disclaimer": CLINICIAN_DISCLAIMER}  # fmt: skip
    return {
        "available": True,
        "lookalikes": [x.model_dump() for x in look],
        **suggest(look),
        "note": "Illustrative clinic data (synthetic).",
        "disclaimer": CLINICIAN_DISCLAIMER,
    }


def build_server(deps: AgentDeps) -> MCPServer:
    server = MCPServer("constellation")

    @server.tool(name="resolve_phenotype")
    def resolve_phenotype_tool(text: str) -> list[dict[str, Any]]:
        """Map plain-language words to HPO terms (graph full-text + vector search)."""
        return resolve_phenotype(deps, text)

    @server.tool(name="rank_candidates")
    def rank_candidates_tool(findings: list[dict[str, str]]) -> dict[str, Any]:
        """Rank candidate conditions for [{term_id, status}] findings. Decision support only."""
        return rank_candidates(deps, findings)

    @server.tool(name="explain_candidate")
    def explain_candidate_tool(findings: list[dict[str, str]], disease_id: str) -> dict[str, Any]:
        """Show which findings support or oppose one candidate, with graph paths."""
        return explain_candidate(deps, findings, disease_id)

    @server.tool(name="centre_route_case")
    def centre_route_case_tool(hpo_ids: list[str]) -> dict[str, Any]:
        """Find look-alike cases at the centre, who solved them and with which protocol."""
        return centre_route_case(deps, hpo_ids)

    return server


def main() -> None:
    server = build_server(AgentDeps.build())
    server.run("streamable-http" if "http" in sys.argv[1:] else "stdio")


if __name__ == "__main__":
    main()
