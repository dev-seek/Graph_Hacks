# Data licences and attributions

Status: P1. Wording below was copied from the source pages/repositories on 2026-10-15; raw files are never committed. Pinned releases: HPO v2026-09-01 (HPOA 2026-09-02), Orphadata products dated 2026-06-23 (files fetched 2026-06-29), Phenopacket Store 0.1.27.

## Human Phenotype Ontology (HPO)
- Files: `hp.json`, `phenotype.hpoa` (same pinned release; version shown in the app footer).
- Conditions: free use with citation; display the HPO version; never alter HPO content or logical relationships (our own labels are separate `cx_*` properties). HPO requests a statement and logo.
- Licence page (https://hpo.jax.org/app/license), verbatim: "All of the following license restrictions apply to all files provided by the HPO project: The HPO vocabularies, annotation files, tools and documentation are freely available. The HPO is copyrighted to protect the integrity of the vocabularies, which means that changes to the HPO vocabularies need to be done by HPO developers. However, anyone can download the HPO and use the ontologies or other HPO files under three conditions: (1) That the Human Phenotype Ontology Consortium is acknowledged and cited properly. (2) That any HPO Consortium file(s) displayed publicly include the date(s) and/or version number(s) of the relevant HPO file(s). (3) That neither the content of the HPO file(s) nor the logical relationships embedded within the HPO file(s) be altered in any way. (Content additions and modifications have to be suggested using our issue tracker.) We suggest that you follow standard scientific citation practice if you use the HPO in publications. Users of the HPO should add the following statement to their online presence. This service/product uses the Human Phenotype Ontology (version information). Find out more at http://www.human-phenotype-ontology.org We request that the HPO logo be included as well."
- Statement used in the footer and /about: "This service/product uses the Human Phenotype Ontology (version 2026-09-01). Find out more at http://www.human-phenotype-ontology.org". (Logo: not added; HPO asks for it but does not require it. Needs the official file from the HPO site: listed under "Needs from human".)
- Citation (HPO "Cite" page): Gargano MA, et al. The Human Phenotype Ontology in 2024: phenotypes around the world. Nucleic Acids Res. 2024 Jan 5;52(D1):D1333-D1346. doi: 10.1093/nar/gkad1005. PMID: 37953324.
- How we comply: HPO files are loaded unmodified; our own labels are separate `cx_*` properties; the version is shown in the footer and `/api/version`.
- OMIM-sourced IEA annotations (`database_id` starts `OMIM:` and `evidence = IEA`) are excluded unless `KB_INCLUDE_OMIM_IEA=true`.

## Orphanet (Orphadata Science)
- Files: `en_product9_prev.xml`, `en_product1.json.tar.gz`. Licence: CC BY 4.0.
- Required citation, verbatim: "Orphadata Science: Free access data from Orphanet. © INSERM 1999. Available on http://sciences.orphadata.com/. Data version [date]."
- Changes made: prevalence classes converted to approximate numeric priors.
- No endorsement claim, no Orphanet logo, no deep links to PDF/XML files (link the Orphadata home only).

## Phenopacket Store
- Release `0.1.27`, `all_phenopackets.zip`. Licence: BSD-3-Clause.
- Copyright notice and licence text (repository `LICENSE`, verbatim): "BSD 3-Clause License. Copyright (c) 2022, Monarch Initiative. Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met: 1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer. 2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution. 3. Neither the name of the copyright holder nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission. THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE."
- Citation: Danis et al., *HGG Advances* 2025, 6(1):100371 (title, from the repository README: "A corpus of GA4GH phenopackets: Case-level phenotyping for genomic diagnostics and discovery"; Danis et al., Human Genetics and Genomics Advances, Volume 6, Issue 1, 100371).
- No Monarch or endorsement claims.

## Embedding model
- `BAAI/bge-small-en-v1.5` (384-dim). Licence: MIT. Runs locally on CPU.
