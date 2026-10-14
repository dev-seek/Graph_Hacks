<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 5. Data sources, licences, attribution

Pin every file by version and SHA-256 in `data/manifest.yaml`. `make data` downloads and verifies. Raw files are git-ignored. **Never commit real HPO, Orphanet or Phenopacket files.** Unit-test fixtures use a tiny *synthetic* ontology with fake IDs (`TEST:0001…`); integration tests download the pinned real files (cached in CI).

| Source | File(s) | Use | Licence / conditions |
|---|---|---|---|
| Human Phenotype Ontology | `hp.json` (pin release), `phenotype.hpoa` (same release) | Terms, IS_A hierarchy, synonyms (incl. layperson synonyms **[VERIFY]**), disease–phenotype annotations with frequencies | HPO licence: free use with citation; display HPO version; do not alter content or logical relationships; HPO requests a statement + logo **[VERIFY exact wording on the HPO licence page; copy it verbatim into DATA_LICENSES.md and the footer]**. OMIM-sourced IEA annotations require OMIM permission → rows with `database_id` starting `OMIM:` **and** `evidence = IEA` are excluded unless `KB_INCLUDE_OMIM_IEA=true`; all ORPHA/DECIPHER rows and curated OMIM `PCS`/`TAS` rows are kept. |
| Orphanet (Orphadata Science) | `en_product9_prev.xml` (prevalence); **`en_product1.json.tar.gz`** (2.79 MB; alignments with OMIM, ICD-10/11, MONDO and others; 11,645 entries; CC BY 4.0 — verified) **[VERIFY JSON field names and mapping-relation codes, e.g. E / NTBT / BTNT]** | Disease priors; `EQUIVALENT_TO` edges ORPHA↔OMIM (relation stored) for evaluation hits and candidate de-duplication | CC BY 4.0. Required citation, verbatim: "Orphadata Science: Free access data from Orphanet. © INSERM 1999. Available on http://sciences.orphadata.com/. Data version [date]." State changes made ("prevalence classes converted to approximate numeric priors"). No endorsement claim, no Orphanet logo, don't deep-link to PDF/XML files on the website (link the Orphadata home). Note their data caveats on /about. |
| Phenopacket Store | release `0.1.27`, `all_phenopackets.zip` (~18.5 MB) | Evaluation cases (real published case reports, de-identified) and synthetic demo/centre seeds | BSD-3-Clause: keep the copyright notice and licence in `DATA_LICENSES.md` and any redistributed derivative; no Monarch/endorsement claims. Cite Danis et al., *HGG Advances* 2025, 6(1):100371 **[copy title from the repo's CITATION file]**. |
| Embedding model | `BAAI/bge-small-en-v1.5` (384-dim, MIT) | Term embeddings for vector search | Open licence; runs on CPU; no paid API |

HPOA parsing notes: 12 tab-separated columns (`database_id, disease_name, qualifier, hpo_id, reference, evidence, onset, frequency, sex, modifier, aspect, biocuration`) **[VERIFY header in pinned release]**. `qualifier = NOT` → negative annotation. Aspects: `P` phenotype (scored), `I` inheritance (disease property), `C` onset (disease property), `M` modifier and `H` past history (ignore in v1). Frequency may be an HPO frequency term, `n/m`, or `x%`:

| Frequency term | Meaning | Value used |
|---|---|---|
| HP:0040280 Obligate | 100% | 1.0 |
| HP:0040281 Very frequent | 80–99% | 0.90 |
| HP:0040282 Frequent | 30–79% | 0.545 |
| HP:0040283 Occasional | 5–29% | 0.17 |
| HP:0040284 Very rare | 1–4% | 0.025 |
| HP:0040285 Excluded | 0% | treat as NOT |
| missing | — | 0.5 (ADR-0003; tune on dev) |

Orphanet prevalence → prior (use point prevalence, worldwide or Europe, prefer "Validated" **[VERIFY field names]**):

| Class | Prior |
|---|---|
| >1 / 1,000 | 1.5e-3 |
| 6–9 / 10,000 | 7.5e-4 |
| 1–5 / 10,000 | 3e-4 |
| 1–9 / 100,000 | 5e-5 |
| 1–9 / 1,000,000 | 5e-6 |
| <1 / 1,000,000 | 5e-7 |
| Unknown / missing | 1e-6 |

Disease IDs: ORPHA and OMIM nodes both exist, linked by `EQUIVALENT_TO`. Evaluation counts a hit if the predicted ID equals the target or is an *exact* (`E`) mapping of it; broader/narrower mappings are reported separately. A bridge maps IDs but adds no annotations, so the Phase 1 report must state: share of Phenopacket Store diagnoses that resolve to a scored disease node (target ≥ 90%), and how many have ≥ 5 phenotype annotations under the default OMIM flag.

**Leakage guard:** build `kb_<release>_lpo` without HPOA rows whose `reference` cites a test-case PMID; the test-split evaluation uses it (§14).

Footer (every page): "Uses the Human Phenotype Ontology (version {HPO_VERSION}) · Orphadata Science © INSERM 1999, data version {ORPHA_VERSION} · Example cases derived from Phenopacket Store {PS_VERSION} · Not a diagnosis." Full credits on /about.
