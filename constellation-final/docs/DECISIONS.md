# DECISIONS.md — locked decisions (v2, 14 Oct 2026)

The plan is locked. Agents must not reopen these. Only values marked *tuned* in the spec (`docs/spec/`) change, through ADRs, using the dev split and synthetic negatives only. If evidence shows a locked decision is wrong, stop and ask the human with the evidence.

## Locked decisions
| # | Topic | Decision |
|---|---|---|
| 1 | Product | Constellation: long-running, parent-safe evidence agent for ages 0–20; doctor pack; referral + GA4GH Phenopacket v2 export; watcher; Centre brain |
| 2 | Tracks | Enter all three (R5): Track 2 primary, Track 1 co-primary, Track 3 secondary; plus the blog-post side prize. Ask on Discord whether one project can win several |
| 3 | Graph centrality (R3) | Graph-first rounds: prune, retrieve candidates, planner annotations, explanations all run as Cypher every round; Python does arithmetic only; only cache = HPO ancestor sets |
| 4 | Data | HPO + HPOA (exclude only OMIM-sourced IEA rows), Orphanet product9 (priors) + product1 (OMIM↔ORPHA `EQUIVALENT_TO`), Phenopacket Store 0.1.27, bge-small-en-v1.5 |
| 5 | Scoring | LIRICAL-style LR; prune ancestors; broad-match decay `λ`; NOT = 0.001; noise `ε`; absent `(1−F)/(1−bg)` with F ≤ 0.999; source weights; ±ln 100 cap; optional organ dampening γ (1, 0.6, 0.35); D₀ prior 0.97 with multi-system decay β = 0.45; unlinked-mass term |
| 6 | Gates | Emergency, urgent soon, see doctor (τ1 = 0.30), referral (τ2 = 0.70 + 2 doctor/test findings + top-10 share ≥ 0.6), no escalation (τ0 = 0.05) — thresholds *tuned* |
| 7 | Evaluation | Split by PMID 30/70; leave-publication-out kb for test; exact-mapping hits only; simulator unmentioned → 90% unsure / 10% no (+ 0/30% sweep); B0/B1/B2 vs ours; B3 cut; published figures as context only |
| 8 | Centre (Track 3) | Cases + Clinician (pseudonyms) + DiagnosticProtocol + CaseDecision, all synthetic and labelled; routing, bridges, clusters, what-if |
| 9 | Teen scope | Ages 0–20; age-gated questions; teen self-harm rules; parent remains the user |
| 10 | Rules 11–13 | Honest disclosure. The human's contribution: problem choice, research, product and technical design, locked decisions, reviewing and approving every `review/` input (Claude drafts them), and presenting (video, blog, Q&A). AI_USAGE.md records truthfully who drafted and who reviewed each part. No attempt to disguise AI authorship |
| 10b | LLM | Claude only, behind `LLMPort`: Haiku 5.5 for fast tasks, Haiku 5.5 + Sonnet 5.5 advisor for doctor letters, Sonnet 5.5 for referral drafts, Message Batches (50% off) for offline labelling; the contract suite keeps the cheapest passing profile per task; deterministic fallback per task; demos replay with no key; local embeddings (Claude has no embeddings endpoint) |
| 10d | Build tooling | Claude Code only: Sonnet 5.5 main model + Opus 5.5 advisor for every phase (cheaper than Opus throughout, stronger than Sonnet alone); Haiku for Explore; optional Fable advisor via `ADVISOR_MODEL` |
| 10c | Build process | Autonomous: Claude works from `.build/STATE.md` + one phase work order at a time; tuned values chosen by pre-declared rules (no human choice needed); stops only for human inputs or blockers |
| 11 | Deployment | Docker Compose + Caddy on 2 vCPU / 4 GB VPS; FalkorDB pinned tag, internal network only; replay mode default |
| 12 | Name | "Constellation" for the hackathon; trademark-checked brand later |
| 13 | Business | Not part of this build. Lives in a separate document outside the repo |

## Corrections applied to the pre-kickoff research
| Claim | Correction |
|---|---|
| Each track awards its own prize to the same project (R5, R14) | R5 allows entering all tracks; winning several is not addressed |
| DeepRare: 6,401 cases, 33.39% Claude baseline, clinician agreement | Abstract: 57.18% average Recall@1 over 9 datasets, +23.79 over next-best; 69.1% vs Exomiser 55.9% with genetic data (168 cases); 95.4% *expert* agreement |
| Phenopackets raise lab yield 33% → 63–69% | Unsupported; removed |
| Zero coverage loss after the OMIM bridge | Bridge maps IDs, adds no annotations; measured in Phase 1 |
| "Validated by" Saventic / Citizen Health | Comparable business models only |
| Organ dampening 1/0.5/0.25 vs 1/0.6/0.35 | Default 1/0.6/0.35; kept only if it helps on dev |
| Candidate retrieval query | Unanchored path scan + AND/OR precedence bug; replaced by spec §13 Q2a–d |
| Centre routing query | Guard on the wrong clause; replaced by spec §13 Q7 |
| `falkordb/falkordb:latest` | Pin an exact tag |
| Atropos uses hospital EHR claims | Article says "real-world data"; first target PNH |

## Still open (do not block the build)
- Can one project win several tracks? (Discord)
- Real-parent behaviour (post-hackathon hallway tests)
- Clinician review of red-flag rules (post-hackathon)
- Willingness to pay of labs / pharma / foundations (customer interviews)
