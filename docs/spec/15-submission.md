<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 18. Submission checklist and README outline

Checklist:
- [ ] Public GitHub repo, MIT licence, no secrets (run gitleaks)
- [ ] README: problem, demo GIF, live URL, 3-command local setup, architecture diagram, **graph data model** (Mermaid for kb/family/centre), **Cypher queries and algorithms used** (table with file links), agents and gates, evaluation headline numbers with CIs and the honest framing, safety design, data sources + exact attributions, limitations, tracks (2 primary, 1 co-primary, 3 secondary), AI-assistant disclosure incl. the human-written parts (Rule 13), team
- [ ] Demo video (≤ 3 min, voiced by the human): problem in 20 s (Priya's story) → Kabir journey with the live inspector → Arjun no-escalation → Maya red flag → clinician view + Phenopacket → centre routing → eval chart → tagline
- [ ] Blog post (side prize): graph model, Cypher, agent loop, eval — written/edited by the human
- [ ] Rules 11–13: `docs/AI_USAGE.md` states truthfully who drafted, decided and reviewed each part
- [ ] Live deployment link in replay mode + local setup instructions
- [ ] `docs/AI_USAGE.md` complete; human can explain every module (`docs/explain/`)
- [ ] All three tracks named in the submission (R5); ask on Discord whether one project can win several

README outline: 1 Why · 2 What it does (GIF) · 3 Try it (3 commands + a 5-minute tour with the example families; link to docs/USER_GUIDE.md) · 4 How it works (agents, gates, safety) · 5 FalkorDB inside (graphs, model, queries, algorithms, checkpointer, MCP) · 6 Evaluation · 7 Data and credits · 8 Limits and what's next · 9 Tracks · 10 Built with AI assistants (disclosure) · 11 Licence.


## 19. Limitations and risks (say these out loud)
- Not clinically validated; simulated answers are cleaner than real parents.
- Knowledge is only as good as HPO annotations; excluding OMIM IEA reduces coverage for some OMIM-only diseases (the bridge maps IDs, it does not add annotations).
- The common-explanation class, multi-system decay and organ dampening are heuristics, tuned on synthetic negatives.
- Possible annotation/test overlap via shared publications: mitigated by the leave-publication-out kb.
- Clinic data (clinicians, protocols, decisions) is synthetic and labelled.
- Published cases may appear in LLM training data (affects the LLM baseline, not our engine's scoring).
- English only in v1. Lay-term coverage depends on HPO layperson synonyms + our generated labels.
- Regulatory path needed before real clinical use.


## 20. References
- EURORDIS Rare Barometer survey on time to diagnosis (2024).
- Nguengang Wakap S et al. Estimating cumulative point prevalence of rare diseases. *Eur J Hum Genet* 2020 (PMC6974615).
- Reese JT et al. LLMs have not reached the accuracy of traditional rare-disease tools (PMC11302616); GPT-4 rare-disease study (medRxiv 2024.07.22.24310816).
- DeepRare (arXiv 2506.20430 v3); RaDaR (arXiv 2606.24510); liteOdyssey (arXiv 2606.16149); MIMIC-RD (arXiv 2601.11559).
- Orphadata alignments `en_product1` (sciences.orphadata.com/alignments/), CC BY 4.0.
- GA4GH Phenopacket schema v2 (phenopacket-schema.readthedocs.io).
- Robinson PN et al. Interpretable clinical genomics with a likelihood ratio paradigm (LIRICAL). *Am J Hum Genet* 2020.
- Human Phenotype Ontology — hpo.jax.org; Gargano MA et al., HPO 2024 update, *Nucleic Acids Res* 2024 **[VERIFY citation]**.
- Orphadata Science, © INSERM 1999, sciences.orphadata.com.
- Danis D et al., Phenopacket Store, *HGG Advances* 2025, 6(1):100371.
- FalkorDB docs: Cypher support, known limitations, indexes (range, full-text, vector), algorithms, configuration, GRAPH.COPY.
- langchain-falkordb 0.2.0 (FalkorDBSaver); LangGraph 1.2.x docs (interrupts, persistence).
- FDA guidance: Clinical Decision Support Software; EU MDR Rule 11.
