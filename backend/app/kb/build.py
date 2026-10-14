"""Build `kb_<release>` (and its leave-publication-out twin) in FalkorDB (spec §11.1).

`prepare` is pure (rows from parsed files); `write_graph` talks to FalkorDB with batched UNWIND.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from falkordb import FalkorDB
from pydantic import BaseModel, Field

from app.kb.labels import TermLabel, rule_label
from app.kb.parsers.hp import Ontology
from app.kb.parsers.hpoa import HpoaParse
from app.kb.parsers.orphanet import PRIORS, Prevalence, Product1
from app.kb.structure import annotation_stats, build_structure
from app.llm.port import EmbeddingPort

log = logging.getLogger(__name__)

PHENO_ROOT = "HP:0000118"
UNKNOWN_PRIOR = PRIORS["Unknown"]
WRITE_TIMEOUT_MS = 10_000  # server TIMEOUT_MAX (docs/VERIFIED.md)


class KbData(BaseModel):
    terms: list[dict[str, Any]] = Field(default_factory=list[dict[str, Any]])
    is_a: list[dict[str, str]] = Field(default_factory=list[dict[str, str]])
    diseases: list[dict[str, Any]] = Field(default_factory=list[dict[str, Any]])
    has_phenotype: list[dict[str, Any]] = Field(default_factory=list[dict[str, Any]])
    lacks_phenotype: list[dict[str, Any]] = Field(default_factory=list[dict[str, Any]])
    equivalent_to: list[dict[str, str]] = Field(default_factory=list[dict[str, str]])
    stats: dict[str, int] = Field(default_factory=dict[str, int])


def _refs(reference: str) -> set[str]:
    return {r.strip() for r in reference.split(";") if r.strip()}


def prepare(
    ontology: Ontology,
    hpoa: HpoaParse,
    prevalence: Mapping[str, Prevalence],
    product1: Product1,
    *,
    exclude_pmids: frozenset[str] = frozenset(),
    label_overrides: Mapping[str, TermLabel] | None = None,
    pheno_root: str = PHENO_ROOT,
) -> KbData:
    data = KbData()
    live = {tid: t for tid, t in ontology.terms.items() if not t.is_obsolete}
    parents = {tid: [p for p in t.parents if p in live] for tid, t in live.items()}
    structure = build_structure(parents, pheno_root)

    # --- annotations: resolve ids, apply leave-publication-out filter
    kept: list[tuple[Any, str]] = []
    unresolved = lpo_dropped = 0
    for a in hpoa.annotations:
        term = ontology.resolve(a.hpo_id)
        if term is None:
            unresolved += 1
            continue
        if exclude_pmids and _refs(a.reference) & exclude_pmids:
            lpo_dropped += 1
            continue
        kept.append((a, term))
    positives = [(a.disease_id, t, a.freq) for a, t in kept if not a.negated]
    stats = annotation_stats(structure, positives)

    # --- terms (labels + embeddings are attached in write_graph for the embedding step)
    overrides = label_overrides or {}
    for tid, t in sorted(live.items()):
        row: dict[str, Any] = {
            "id": tid,
            "name": t.name,
            "definition": t.definition,
            "synonyms": t.synonyms + t.lay_synonyms,
            "synonyms_text": " | ".join(t.synonyms),
            "is_obsolete": False,
            "depth": structure.depth.get(tid, -1),
        }
        st = stats.get(tid)
        if st:
            row.update(bg=st.bg, ic=st.ic)
        system = structure.system.get(tid)
        if system:
            row["cx_system"] = system
            names = {live[a].name for a in structure.ancestors.get(tid, frozenset()) if a in live}
            label = overrides.get(tid) or rule_label(t.name, t.lay_synonyms, names)
            row.update({k: v for k, v in label.model_dump().items()})
            row["embed_text"] = "; ".join([t.name, *t.lay_synonyms[:10]])
        else:
            row["cx_lay_text"] = " | ".join(t.lay_synonyms)
        data.terms.append(row)
    for tid, plist in sorted(parents.items()):
        data.is_a.extend({"s": tid, "o": p} for p in plist)

    # --- diseases
    exact_omim: dict[str, list[str]] = defaultdict(list)
    exact_orpha: dict[str, list[str]] = defaultdict(list)
    for e in product1.equivalences:
        if e.relation == "E":
            exact_omim[e.orpha_id].append(e.omim_id)
            exact_orpha[e.omim_id].append(e.orpha_id)
    ids: dict[str, str] = {d: r.name for d, r in hpoa.diseases.items()}
    for oid, name in product1.orpha.items():
        ids.setdefault(oid, name)
    for e in product1.equivalences:
        ids.setdefault(e.omim_id, e.omim_id)
    for did in sorted(ids):
        source = did.split(":", 1)[0]
        prev: Prevalence | None = None
        if source == "ORPHA":
            prev = prevalence.get(did)
        elif source == "OMIM":
            cands = [prevalence[o] for o in exact_orpha.get(did, []) if o in prevalence]
            prev = max(cands, key=lambda p: p.prior, default=None)
        rec = hpoa.diseases.get(did)
        inh = [
            ontology.terms[i].name if i in ontology.terms else i
            for i in (rec.inheritance if rec else [])
        ]
        data.diseases.append(
            {
                "id": did,
                "name": ids[did],
                "source": source,
                "prior": prev.prior if prev else UNKNOWN_PRIOR,
                "prevalence_class": prev.prevalence_class if prev else "Unknown",
                "inheritance": sorted(set(inh)),
                "omim_ids": sorted(set(exact_omim.get(did, []))),
            }
        )
    for a, term in kept:
        base = {"d": a.disease_id, "t": term, "evidence": a.evidence, "reference": a.reference}
        if a.negated:
            data.lacks_phenotype.append(base)
        else:
            data.has_phenotype.append(
                {**base, "freq": a.freq, "freq_raw": a.freq_raw, "onset": a.onset, "sex": a.sex}
            )
    known = set(ids)
    data.equivalent_to = [
        {"a": e.orpha_id, "b": e.omim_id, "relation": e.relation}
        for e in product1.equivalences
        if e.orpha_id in known and e.omim_id in known
    ]
    scored = {r["d"] for r in data.has_phenotype}
    data.stats = {
        "terms": len(data.terms),
        "terms_obsolete_skipped": len(ontology.terms) - len(live),
        "is_a": len(data.is_a),
        "diseases": len(data.diseases),
        "diseases_scored": len(scored),
        "has_phenotype": len(data.has_phenotype),
        "lacks_phenotype": len(data.lacks_phenotype),
        "equivalent_to": len(data.equivalent_to),
        "annotations_unresolved_term": unresolved,
        "annotations_lpo_dropped": lpo_dropped,
    }
    return data


def _batches(rows: list[dict[str, Any]], n: int) -> Iterable[list[dict[str, Any]]]:
    for i in range(0, len(rows), n):
        yield rows[i : i + n]


def write_graph(
    db: FalkorDB,
    graph_name: str,
    data: KbData,
    embedder: EmbeddingPort,
    info: Mapping[str, Any],
    *,
    batch: int = 1000,
) -> dict[str, float]:
    """(Re)create the graph. Returns step timings in seconds."""
    timings: dict[str, float] = {}
    t0 = time.monotonic()

    def lap(name: str) -> None:
        nonlocal t0
        now = time.monotonic()
        timings[name] = round(now - t0, 2)
        t0 = now

    if graph_name in db.list_graphs():
        db.select_graph(graph_name).delete()
    g = db.select_graph(graph_name)

    def q(cypher: str, params: dict[str, Any] | None = None) -> None:
        g.query(cypher, params or {}, timeout=WRITE_TIMEOUT_MS)

    q("CREATE INDEX FOR (t:Term) ON (t.id)")
    q("CREATE INDEX FOR (d:Disease) ON (d.id)")

    # embeddings for terms that carry an embed_text
    to_embed = [r for r in data.terms if "embed_text" in r]
    vectors = embedder.embed([r["embed_text"] for r in to_embed])
    for r, v in zip(to_embed, vectors, strict=True):
        r["vec"] = v
    lap("embed")

    for rows in _batches(data.terms, batch):
        q(
            "UNWIND $rows AS r CREATE (t:Term) SET t += r, "
            "t.embedding = CASE WHEN r.vec IS NULL THEN NULL ELSE vecf32(r.vec) END "
            "REMOVE t.embed_text, t.vec",
            {"rows": rows},
        )
    lap("terms")
    for rows in _batches(data.is_a, 5000):
        q(
            "UNWIND $rows AS r MATCH (a:Term {id: r.s}), (b:Term {id: r.o}) "
            "CREATE (a)-[:IS_A]->(b)",
            {"rows": rows},
        )
    lap("is_a")
    for rows in _batches(data.diseases, 5000):
        q("UNWIND $rows AS r CREATE (d:Disease) SET d += r", {"rows": rows})
    lap("diseases")
    for rows in _batches(data.has_phenotype, 5000):
        q(
            "UNWIND $rows AS r MATCH (d:Disease {id: r.d}), (t:Term {id: r.t}) "
            "CREATE (d)-[:HAS_PHENOTYPE {freq: r.freq, freq_raw: r.freq_raw, onset: r.onset, "
            "sex: r.sex, evidence: r.evidence, reference: r.reference}]->(t)",
            {"rows": rows},
        )
    lap("has_phenotype")
    for rows in _batches(data.lacks_phenotype, 5000):
        q(
            "UNWIND $rows AS r MATCH (d:Disease {id: r.d}), (t:Term {id: r.t}) "
            "CREATE (d)-[:LACKS_PHENOTYPE {evidence: r.evidence, reference: r.reference}]->(t)",
            {"rows": rows},
        )
    for rows in _batches(data.equivalent_to, 5000):
        q(
            "UNWIND $rows AS r MATCH (a:Disease {id: r.a}), (b:Disease {id: r.b}) "
            "CREATE (a)-[:EQUIVALENT_TO {relation: r.relation}]->(b)",
            {"rows": rows},
        )
    lap("lacks_equiv")
    q("CREATE FULLTEXT INDEX FOR (t:Term) ON (t.name, t.synonyms_text, t.cx_lay_text)")
    q(
        f"CREATE VECTOR INDEX FOR (t:Term) ON (t.embedding) OPTIONS {{dimension: {embedder.dim}, "
        "similarityFunction: 'cosine', M: 16, efConstruction: 200}"
    )
    lap("indexes")
    q("CREATE (k:KbInfo) SET k += $info", {"info": dict(info)})
    return timings
