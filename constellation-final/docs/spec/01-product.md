<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 1. Problem and purpose

**Who it's for.** Children and teenagers aged 0–20 (the parent or caregiver is the user). Of 6,172 Orphanet rare diseases, 71.9% are genetic and 69.9% start only in childhood (Nguengang Wakap et al., 2020). Ages 2–10 wait 8.8 years and ages 10–20 wait 10.4 years for a diagnosis (EURORDIS Rare Barometer).

**The problem, as it happens today.** Priya's son Kabir is 3. He walked late, says few words, had two "funny turns" that might have been seizures, and is unusually floppy. Each issue goes to a different appointment: the GP says "boys talk late", the physio works on his walking, the after-hours doctor sees one turn and says "watch and wait". Nobody sees all of it together, nobody asks the questions that would join the dots (does he laugh a lot? is his sleep unusual? has his head growth slowed?), and Priya doesn't know which details matter. Families with a rare condition wait on average **about 4.7 years** for a diagnosis, longer for adolescents (EURORDIS Rare Barometer 2024). About **300 million** people live with a rare disease.

**Why existing tools don't fix it.** Symptom checkers do one-off triage and aim at common conditions. Clinical tools (Exomiser, LIRICAL, Face2Gene) need a clinician who already suspects something, or genetic data. General chatbots guess diseases from text — the best LLMs reach only ~24% top-1 on rare-disease cases, behind phenotype-driven tools — and they forget the family between chats.

**What Constellation does.** It is the family's long-running memory and evidence collector:
1. The parent tells the story in their own words.
2. The agent turns it into structured findings (HPO terms) and asks small rounds of 3–5 plain questions chosen to separate the remaining possibilities the most.
3. When the evidence is strong enough, or home questions can't learn more, it says **"time to see a doctor"** and prepares a one-page **doctor pack** (timeline, what's present, what's absent, what's still unknown, what a doctor may want to check).
4. Doctor findings come back in (the parent uploads the letter); the agent continues with sharper questions.
5. When the pattern fits rare conditions strongly enough, it prepares a **referral letter** to a genetics / rare-disease clinic, for the family's doctor to send, plus a **GA4GH Phenopacket v2 JSON** that labs and Exomiser/LIRICAL can read.
6. It keeps **watching** for months and years: as the child grows, new questions become answerable; as medical knowledge updates, it re-checks.
7. A **Centre brain** (for a rare-disease clinic) remembers every consented case, **which clinician handled look-alike cases and which diagnostic protocol confirmed them**, bridge findings and clusters, and which open cases a knowledge update affects.

Hackathon fit (we enter all three tracks, R5): **Track 2 Agent Memory — primary** (graph per family for years, checkpointed agent state, agent handoffs through shared state); **Track 1 Agents That Act on Connected Data — co-primary** (multi-hop HPO traversal decides questions and gates, which trigger doctor pack, referral, watcher actions; MCP tools; explanation paths); **Track 3 Company Brain — secondary** (centre: who knows what, decisions traced to source, knowledge kept current). Plus the **best blog post** side prize.


## 2. Product

### 2.1 Users and jobs
| User | Job to be done | What they see |
|---|---|---|
| Parent / caregiver | "Help me know what matters, when to go, and what to say." | Story, questions, next step, doctor pack, timeline, their "constellation" of findings. Never disease names or odds. |
| Family doctor / paediatrician | "Give me the whole picture in two minutes and tell me what to check." | Doctor pack; with the clinician code, the clinician view: findings with sources, candidate patterns for review, explanation paths, suggested checks, referral draft, Phenopacket export. |
| Rare-disease centre (geneticist, coordinator) | "Remember everything we've seen, who solved what and how; tell us which open cases to look at again." | Centre brain dashboard (look-alikes → clinician + protocol routing, bridges, clusters, knowledge-update impact). |
| Judge / first-time visitor | "Show me it works in 3 minutes." | Demo journeys (Kabir, Arjun, Maya) in replay mode with the live FalkorDB inspector. |

### 2.2 Non-goals (do not build)
- Diagnosis, treatment advice, medication advice, emergency triage beyond the red-flag rules.
- Genetic variant interpretation (no VCF upload). Possible future integration with Exomiser.
- Accounts, payments, EHR integration, real patient data.
- Adult rare disease focus (copy and milestones are written for ages 0–20).
- Teenagers using the app alone (consent questions); the parent/caregiver is the user, tone adapts to the child's age.
- LLM-interviewer baseline (B3) — cut.

### 2.3 Business
Out of scope for this build. The README gets one short "What's next" paragraph (spec §18); nothing else about business belongs in code or docs here.

## 3. The journey

States (LangGraph, §9) and what the parent experiences:

```
START
 └─ STORY: parent writes story (+ child age in months, 0–240, optional sex)
     └─ SAFETY CHECK ──(emergency)──► URGENT (stop; show urgent message)
     └─ EXTRACT + CONFIRM: "Here's what we understood" — parent ticks / edits / removes each item
         └─ ROUND n (home): 3–5 questions, answers Yes / No / Not sure
             └─ SAFETY CHECK on answers
             └─ SCORE + GATES
                 ├─ continue ─► ROUND n+1 (max 4 home rounds before see-doctor is forced)
                 ├─ SEE_DOCTOR: doctor pack ready; "what to ask your doctor"
                 │    └─ DOCTOR FINDINGS: parent uploads letter / enters findings ─► confirm
                 │         └─ ROUND (post-doctor): questions may include "ask your doctor to check…"
                 │              └─ SCORE + GATES
                 │                   ├─ REFERRAL_READY: referral letter + Phenopacket v2 JSON for the doctor; then WATCH
                 │                   └─ continue / WATCH
                 └─ WATCH: periodic re-check (age milestones, knowledge updates) ─► new ROUND if useful
```

Rules:
- At least one home round before any gate other than safety.
- See-doctor is forced after 4 home rounds even if no threshold is met ("we've learned what we can at home").
- URGENT_SOON safety flags (e.g., loss of skills) set a banner and push to SEE_DOCTOR immediately, but the journey continues.
- The parent can stop, leave, and resume at any time (checkpointer); can delete everything (one button, confirmed).
- Every finding records its source: `parent_story`, `parent_answer`, `doctor_exam`, `lab_or_test`.
- Questions are age-gated by `cx_min_age_months` (no school or puberty questions for a toddler).
