# Data licences and attributions

Status: skeleton (P0). Exact wording is filled in P1 when the pinned releases are downloaded; items marked **TODO(P1)** must be verified against the source page and copied verbatim. Raw files are never committed.

## Human Phenotype Ontology (HPO)
- Files: `hp.json`, `phenotype.hpoa` (same pinned release; version shown in the app footer).
- Conditions: free use with citation; display the HPO version; never alter HPO content or logical relationships (our own labels are separate `cx_*` properties). HPO requests a statement and logo.
- Statement (verbatim): **TODO(P1)** copy from the HPO licence page.
- OMIM-sourced IEA annotations (`database_id` starts `OMIM:` and `evidence = IEA`) are excluded unless `KB_INCLUDE_OMIM_IEA=true`.

## Orphanet (Orphadata Science)
- Files: `en_product9_prev.xml`, `en_product1.json.tar.gz`. Licence: CC BY 4.0.
- Required citation, verbatim: "Orphadata Science: Free access data from Orphanet. © INSERM 1999. Available on http://sciences.orphadata.com/. Data version [date]."
- Changes made: prevalence classes converted to approximate numeric priors.
- No endorsement claim, no Orphanet logo, no deep links to PDF/XML files (link the Orphadata home only).

## Phenopacket Store
- Release `0.1.27`, `all_phenopackets.zip`. Licence: BSD-3-Clause.
- Copyright notice and licence text: **TODO(P1)** copy from the repository.
- Citation: Danis et al., *HGG Advances* 2025, 6(1):100371 (title: **TODO(P1)** from the repo's CITATION file).
- No Monarch or endorsement claims.

## Embedding model
- `BAAI/bge-small-en-v1.5` (384-dim). Licence: MIT. Runs locally on CPU.
