<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 11. Graph data model (FalkorDB)

Multiple graphs in one FalkorDB instance (pinned image tag):
- `kb_<release>` — shared medical knowledge (read-only at runtime). Plus `kb_<release>_lpo` — the **leave-publication-out** variant used only for test-split evaluation (HPOA rows whose `reference` cites any test-case PMID removed).
- `family_<id>` — one per family (isolation; `GRAPH.DELETE` on erasure).
- `centre` — consented, de-identified case memory + organisational knowledge (Track 3). `centre_whatif` — a `GRAPH.COPY` for knowledge-update simulations.
- FalkorDBSaver checkpoint data (managed by the library; thread_id = `family_<id>`).

### 11.1 `kb_<release>`
```
(:Term {id, name, definition, synonyms: [..], synonyms_text, cx_lay_text, is_obsolete,
        depth, ic, bg, embedding: vecf32(384),
        cx_system,              // top-level HPO branch id under HP:0000118
        cx_obs,                 // 'home' | 'exam' | 'test'
        cx_min_age_months,      // youngest age the question makes sense
        cx_question, cx_why, cx_how_to_check, cx_plain_label})
(:Term)-[:IS_A]->(:Term)
(:Disease {id, name, source: 'ORPHA'|'OMIM'|'DECIPHER', prior, prevalence_class, inheritance: [..], omim_ids: [..]})
(:Disease)-[:HAS_PHENOTYPE {freq, freq_raw, onset, sex, evidence, reference}]->(:Term)
(:Disease)-[:LACKS_PHENOTYPE {evidence, reference}]->(:Term)          // HPOA qualifier NOT
(:Disease)-[:EQUIVALENT_TO {relation}]->(:Disease)                     // Orphanet en_product1; relation 'E' = exact [VERIFY codes]
(:KbInfo {kb_version, hpo_version, hpoa_version, orpha_version, product1_version, built_at,
          include_omim_iea, lpo_excluded_pmids_count})
```
HPOA filter: drop rows where `database_id` starts with `OMIM:` **and** `evidence == 'IEA'` (unless `KB_INCLUDE_OMIM_IEA=true`). Keep all ORPHA and DECIPHER rows and curated OMIM `PCS`/`TAS` rows.
Indexes: range on `Term.id`, `Disease.id`; full-text on `Term(name, synonyms_text, cx_lay_text)`; vector on `Term.embedding` (384, cosine).

### 11.2 `family_<id>`
```
(:Family {id, created_at, kb_version, consent_centre})
(:Child {age_months_at_start, sex?})                       // no name, no DOB, no location
(:Story {text_hash, at})  (:Document {id, kind, sha256, uploaded_at})
(:Finding {id, term_id, plain_label, status: 'present'|'absent', source: 'parent_story'|'parent_answer'|'doctor_exam'|'lab_or_test',
           onset_months, recorded_at, active})
(:Finding)-[:SUPPORTED_BY]->(:Evidence {kind: 'story'|'answer'|'document', quote, start, end, at})
(:Evidence)-[:IN_DOCUMENT]->(:Document)   (:Evidence)-[:IN_STORY]->(:Story)
(:Finding)-[:OBSERVED_AS]->(:TermRef {id})-[:IS_A]->(:TermRef)  // local copy of used terms + ancestors: self-explaining graph
(:Round {n, kind: 'home'|'post_doctor', asked_at})-[:ASKED]->(:Question {id, term_id, text, observability, ig})
(:Question)-[:ANSWERED]->(:Answer {value: 'yes'|'no'|'unsure', at})-[:PRODUCED]->(:Finding)
(:Snapshot {round, at, kb_version, rare_mass, n_findings})-[:CANDIDATE {rank, post}]->(:DiseaseRef {id})
(:Gate {kind, at, inputs_json, rule})-[:BASED_ON]->(:Snapshot)
(:Artifact {kind: 'doctor_pack'|'referral_letter'|'phenopacket', version, at})-[:CITES]->(:Finding)
(:Flag {rule_id, level, at, quote})
(:Finding)-[:REPLACED_BY]->(:Finding)                      // corrections never delete history
```

### 11.3 `centre` (Track 3: an organisation's brain)
```
(:Case {case_id, status: 'open'|'referred'|'resolved', age_band, kb_version, diagnosis_id?, diagnosis_name?, synthetic: true})
(:Case)-[:PRESENTED_WITH {status, source}]->(:Term {id, name, ic})-[:IS_A]->(:Term)
(:Case)-[:HAS_ANC]->(:Term)                                // materialised ancestor closure of present terms (fast similarity)
(:Case)-[:SIMILAR_TO {score}]->(:Case)                     // top-5 per case, IC-weighted overlap computed in Python, written back
(:Clinician {id, pseudonym, specialty, synthetic: true})-[:MANAGED {from, to}]->(:Case)   // role pseudonyms, never real names
(:Case)-[:RESULTED_IN]->(:CaseDecision {id, outcome, decided_at, turnaround_days, synthetic: true})
(:CaseDecision)-[:USED_PROTOCOL]->(:DiagnosticProtocol {id, name, tests: [..], version, synthetic: true})
(:CaseDecision)-[:DECIDED_BY]->(:Clinician)
(:Note {text, at, by_role})-[:ABOUT]->(:Case|:Term|:DiagnosticProtocol)
(:KbUpdate {from_version, to_version, at})-[:AFFECTED]->(:Case)
```
Seed (Phase 5): ~300 cases from the **dev** split (diagnosis kept for ~250 "resolved", hidden for ~50 "open"); 6–8 clinician pseudonyms with specialties (e.g. "Clinician A — neurogenetics"); 5–8 protocols (e.g. chromosomal microarray, methylation test, gene panel, exome) assigned by plausible rules from the diagnosis type; all `synthetic: true` and labelled "illustrative clinic data" in the UI.

Centre features (each a registry query, timed, shown in the inspector): 1) look-alikes + **who solved them and with which protocol** (routing); 2) bridge signs (betweenness); 3) clusters (WCC; label propagation); 4) knowledge-update impact (`GRAPH.COPY centre centre_whatif`, rescore open cases on the newer kb, list cases crossing τ2, write `KbUpdate`); 5) "ask the centre" (template choice, never free Cypher); 6) notes attached to cases, terms or protocols.
