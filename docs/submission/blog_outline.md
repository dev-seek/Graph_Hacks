# Blog post outline (side prize); the human writes the prose

Draft outline by Claude. No finished prose on purpose: the post should be written or heavily edited by the human (hackathon Rules 11-13).
Say in the post that Claude Code helped build the project, and which parts you wrote and decided.

## Title options
1. Join the dots: a graph memory for children with unexplained symptoms
2. Why we made FalkorDB do the thinking and the LLM do the talking
3. 4.7 years to a diagnosis: building an evidence agent on a phenotype ontology graph
4. Code decides, the LLM talks: a safe agent on FalkorDB
5. One graph per family: long-running agent memory that a parent can delete

## Outline
1. The problem in one family (Priya and Kabir) and why chatbots and symptom checkers are the wrong tool.
2. The rule that shapes everything: never a diagnosis for the parent; code decides, the model only talks; safety rules run first.
3. The graph model: `kb_<release>` (HPO, annotations, Orphanet), `family_<id>`, `centre`; why one graph per family (privacy, `GRAPH.DELETE`, years of history).
4. The agent loop: story → safety → findings → Cypher round → gate → planner → next questions; checkpointing with `FalkorDBSaver`; resuming after a restart.
5. Scoring as Cypher plus arithmetic: pruning redundant findings, multi-hop retrieval, likelihood ratios; what stayed in Python and why.
6. The centre brain: look-alikes, who solved them, with which protocol; bridges and groups with graph algorithms; `GRAPH.COPY` what-if.
7. Evaluation honestly: leave-publication-out, frozen split, simulated parents, baselines. We do **not** beat the frequent-questions baseline; what we do claim.
8. Things FalkorDB taught us (bugs, workarounds, performance): see `docs/VERIFIED.md` and ADR-0008 (Q2 rewrite) and ADR-0014 (UNWIND vs IN).
9. Building with AI assistants, truthfully: what Claude drafted, what the human decided and reviewed.
10. Limits and what is next.

## Three diagrams to include
1. The three graphs and their main relationships (the Mermaid in the README section 5).
2. The round loop (the flowchart in README section 4), annotated with which step is Cypher.
3. The evaluation chart `eval/reports/2026-10-16-test-top10.png`, or the centre routing result.

## Four key Cypher queries (one line each)
1. [`q2a_exact_or_specific.cypher`](../../backend/app/graph/queries/q2a_exact_or_specific.cypher): finds every disease annotated with a finding or anything more specific, in one multi-hop traversal over `IS_A`.
2. [`q1a_redundant_present.cypher`](../../backend/app/graph/queries/q1a_redundant_present.cypher): removes findings that are ancestors of other findings, so a general sign never double-counts.
3. [`q7_centre_routing.cypher`](../../backend/app/graph/queries/q7_centre_routing.cypher): the five closest solved look-alike cases by information-weighted shared ancestors, with the clinician and protocol that solved each.
4. [`q8a_bridges.cypher`](../../backend/app/graph/queries/q8a_bridges.cypher): `algo.betweenness` over cases and signs to find the signs that connect groups of cases.
