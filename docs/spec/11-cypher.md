<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 13. FalkorDB usage checklist and core Cypher

Exact procedure signatures and guardrails: `docs/FALKORDB_CHEATSHEET.md`. Every query below lives in the query registry (`backend/app/graph/queries/*.cypher`), is parameterised, runs with `ro_query` (reads) and a timeout, and has an integration test on a small real kb before it is relied on.

Checklist (README must show where each is used):
- [ ] Multi-graph: `kb_*`, `kb_*_lpo`, `family_*`, `centre`, `centre_whatif`
- [ ] Range, full-text and vector (HNSW, cosine) indexes
- [ ] Variable-length IS_A traversals every round (prune, retrieve, explain)
- [ ] Algorithms: betweenness (fixed `samplingSeed`), WCC, label propagation
- [ ] `GRAPH.COPY` (what-if), `GRAPH.DELETE` (erasure)
- [ ] Read-only queries + timeouts; `TIMEOUT_MAX` set in compose **[VERIFY config mechanism for the pinned image]**
- [ ] FalkorDBSaver checkpointer; FalkorDB Browser for judges; MCP server for agents

**Q0 — resolve words to terms**
```cypher
CALL db.idx.fulltext.queryNodes('Term', $q) YIELD node, score
RETURN node.id AS id, node.name AS name, score ORDER BY score DESC LIMIT 10

CALL db.idx.vector.queryNodes('Term', 'embedding', 10, vecf32($vec)) YIELD node, score
RETURN node.id AS id, node.name AS name, score
// [VERIFY] whether score is a distance (lower = closer) or a similarity in the pinned version; test with a known synonym
```

**Q1 — prune (upward walks only; cheap)**
```cypher
// Q1a: present terms that are ancestors of another present term → drop them
UNWIND $present AS pid
MATCH (t:Term {id: pid})-[:IS_A*1..]->(a:Term)
WHERE a.id IN $present
RETURN DISTINCT a.id AS redundant

// Q1b: absent terms that have an absent ancestor → drop the more specific one
UNWIND $absent AS aid
MATCH (t:Term {id: aid})-[:IS_A*1..]->(a:Term)
WHERE a.id IN $absent
RETURN DISTINCT t.id AS redundant
```

**Q2 — candidate retrieval (every round)**
```cypher
// Q2a: exact or more-specific annotations → F(D,f)
UNWIND $present AS fid
MATCH (f:Term {id: fid})<-[:IS_A*0..10]-(x:Term)<-[r:HAS_PHENOTYPE]-(d:Disease)
WHERE ID(r) >= 0
RETURN fid AS finding, d.id AS disease, d.prior AS prior, max(r.freq) AS F

// Q2b: broader annotations within 4 hops (patient sign more specific than the disease annotation)
UNWIND $present AS fid
MATCH p = (f:Term {id: fid})-[:IS_A*1..4]->(a:Term)<-[r:HAS_PHENOTYPE]-(d:Disease)
WHERE a.depth >= 3 AND ID(r) >= 0
RETURN fid AS finding, d.id AS disease, d.prior AS prior, a.id AS via, r.freq AS freq, a.bg AS bg_via, length(p) - 1 AS hops

// Q2c: NOT annotations covering a present sign
UNWIND $present AS fid
MATCH (f:Term {id: fid})-[:IS_A*0..]->(a:Term)<-[r:LACKS_PHENOTYPE]-(d:Disease)
WHERE ID(r) >= 0
RETURN DISTINCT fid AS finding, d.id AS disease

// Q2d: absent signs, only for already-retrieved candidates
UNWIND $absent AS fid
MATCH (f:Term {id: fid})<-[:IS_A*0..10]-(x:Term)<-[r:HAS_PHENOTYPE]-(d:Disease)
WHERE d.id IN $candidates AND ID(r) >= 0
RETURN fid AS finding, d.id AS disease, max(r.freq) AS F
```
Python merges rows per (finding, disease): exact (Q2a) wins over broader (Q2b); NOT (Q2c) overrides both. Python never computes a frequency the graph didn't return.

**Q3 — planner inputs (top 50 candidates)**
```cypher
MATCH (d:Disease)-[r:HAS_PHENOTYPE]->(t:Term)
WHERE d.id IN $top AND ID(r) >= 0
RETURN d.id AS disease, t.id AS term, r.freq AS freq

MATCH (t:Term) WHERE t.id IN $askable
RETURN t.id AS id, t.cx_obs AS obs, t.cx_min_age_months AS min_age, t.cx_system AS system, t.cx_question AS question, t.bg AS bg
```

**Q4 — explanation path for the clinician view**
```cypher
MATCH p = (f:Term {id: $finding})-[:IS_A*0..6]->(a:Term)<-[:HAS_PHENOTYPE]-(d:Disease {id: $disease})
RETURN [n IN nodes(p) | n.id] AS path, length(p) AS len ORDER BY len ASC LIMIT 1
// if none: the downward direction (f)<-[:IS_A*0..6]-(x)<-[:HAS_PHENOTYPE]-(d)
```

**Q5 — evaluation hit test via the OMIM↔ORPHA bridge**
```cypher
MATCH (t:Disease {id: $target})
OPTIONAL MATCH (t)-[e:EQUIVALENT_TO]-(o:Disease)
WHERE e.relation = 'E'
RETURN t.id AS target, collect(o.id) AS exact_equivalents
```

**Q6 — family memory writes**
```cypher
MATCH (q:Question {id: $qid})
CREATE (q)-[:ANSWERED]->(a:Answer {value: $value, at: $at})
WITH a
FOREACH (_ IN CASE WHEN $value <> 'unsure' THEN [1] ELSE [] END |
  CREATE (a)-[:PRODUCED]->(:Finding {id: $fid, term_id: $term, status: $status, source: 'parent_answer', recorded_at: $at, active: true}))
```

**Q7 — centre routing: look-alikes, who solved them, with which protocol**
```cypher
UNWIND $case_anc_terms AS tid
MATCH (t:Term {id: tid})<-[:HAS_ANC]-(c:Case {status: 'resolved'})
WITH c, collect(t.name) AS shared, sum(t.ic) AS shared_ic
ORDER BY shared_ic DESC LIMIT 5
MATCH (cl:Clinician)-[m:MANAGED]->(c)
WHERE ID(m) >= 0
OPTIONAL MATCH (c)-[:RESULTED_IN]->(dec:CaseDecision)-[:USED_PROTOCOL]->(p:DiagnosticProtocol)
RETURN c.case_id AS case_id, c.diagnosis_name AS diagnosis, shared, shared_ic,
       cl.pseudonym AS clinician, cl.specialty AS specialty,
       p.name AS protocol, p.tests AS tests, dec.turnaround_days AS turnaround_days
```

**Q8 — centre algorithms** (signatures from the cheat sheet; confirm by test)
```cypher
CALL algo.betweenness({nodeLabels: ['Case', 'Term'], relationshipTypes: ['PRESENTED_WITH'], samplingSize: 64, samplingSeed: 42})
YIELD node, score
WITH node, score WHERE 'Term' IN labels(node)
RETURN node.id AS term, node.name AS name, score ORDER BY score DESC LIMIT 10

CALL algo.WCC({nodeLabels: ['Case'], relationshipTypes: ['SIMILAR_TO']}) YIELD node, componentId
RETURN componentId, collect(node.case_id) AS cases, count(*) AS size ORDER BY size DESC

CALL algo.labelPropagation({nodeLabels: ['Case'], relationshipTypes: ['SIMILAR_TO'], maxIterations: 10}) YIELD node, communityId
RETURN communityId, collect(node.case_id) AS cases, count(*) AS size ORDER BY size DESC
```

Guardrails (FalkorDB known limitations): reference every relationship variable you count or aggregate over (`WHERE ID(r) >= 0`); no aggregates inside pattern comprehensions; `LIMIT` inside a `WITH` before any write; `<>` filters skip indexes. Avoid unbounded `*0..` downward walks from very general terms in hot paths (intake maps to specific terms; Q2 caps at 10).
