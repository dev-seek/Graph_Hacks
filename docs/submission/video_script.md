# Demo video script (3 minutes; voiced by the human)

Draft by Claude, **to be recorded and voiced by the human**. Say it in your own words; the lines below are plain-English suggestions.
Record at 1280×800, browser zoom 100%. Start the app first (`make up`, `make seed`; for the live URL use the deployed site).
The spec order (§18) is kept. Total: about 2:55.

**Before recording:** `make demo-replay` must pass; open `/demo/kabir?judge=1` once to warm the page. Do not linger on the clinician view's
"Findings" list: without a language-model key some recorded findings are noisy (see STATE.md, P4 handoff). Keep the cursor still while talking.

| Time | Screen and exact clicks | Say |
|---|---|---|
| 0:00–0:20 | Landing page `/` (stay on it, scroll once). | "Priya's son Kabir is three. He walked late, says few words, had two funny turns, and is floppy. Each problem goes to a different appointment, and nobody sees all of it together. Families with a rare condition wait on average about 4.7 years for a diagnosis. [Source: EURORDIS Rare Barometer 2024; check it before you say it.] Constellation helps families gather the right evidence and reach the right specialist sooner. It is not a diagnosis tool." |
| 0:20–1:05 | Click **Use an example story** → first round of questions appears. Answer two questions with **Yes** and one **Not sure**. Click **Show the FalkorDB inspector** if visible, otherwise open `/demo/kabir?judge=1` and step with **Next**. | "The parent tells the story in her own words. Safety rules run first, as plain code. Then the agent asks a few simple questions. Every round is Cypher on FalkorDB: pruning, candidate retrieval, which question to ask next. Here are the actual queries, with timings. Python only does arithmetic on the rows." |
| 1:05–1:25 | Still on `/demo/kabir?judge=1`: step to the **see a doctor** step, then show the one-page **doctor pack** (the pack page of the example family, or `docs/explain/P4-screens/pack-print-a4.pdf`). | "When the evidence is strong enough, it says see a doctor and prints a one-page pack in plain words. The parent never sees a disease name or a probability." |
| 1:25–1:40 | Open `/demo/arjun`. Step to the last screen. | "Arjun walked on tiptoes for a few months. The app asks a couple of questions and says: mention it at the next routine visit. Knowing when not to escalate matters as much." |
| 1:40–1:55 | Open `/demo/maya`. | "Maya's mother describes something dangerous. The deterministic safety rules stop everything at once and show the emergency numbers. No language model is involved." |
| 1:55–2:25 | `/demo/kabir` last step → **clinician view**; scroll to the disclaimer and one explanation path; click **Download Phenopacket (JSON)**. | "Only the clinician sees candidates, with a disclaimer and an explanation path through the ontology. When the pattern fits, it drafts a referral letter and a GA4GH Phenopacket version 2 file." |
| 2:25–2:45 | `/centre`: pick an open case; show the five look-alikes table (clinician, protocol); click **Which protocol is fastest?**. Say "synthetic" while the label is on screen. | "For a clinic, the same graph is shared memory: the five closest solved cases, who solved them, and with which protocol. This clinic data is synthetic and labelled so. It also finds bridge signs and shows what a knowledge update would change." |
| 2:45–2:55 | Show `eval/reports/2026-10-16-test-top10.png` (or the README evaluation table). | "On 5,336 real published cases with simulated parents, using a knowledge graph that excludes each case's own publications, we are modestly above the story-only baseline and level with the simple frequent-question baseline. We report that plainly. The aim is safe, earlier escalation, not a better guesser." |
| 2:55–3:00 | Landing page. | **Tagline: TODO (human).** Options: "Join the dots, safely." · "The right specialist, sooner." · "A family's memory, a doctor's head start." |

Checks before you publish: say "synthetic" for the clinic; do not read any condition name aloud from the clinician view as if it were a diagnosis;
state that the project was built with Claude Code and a human reviewed the safety rules, vignettes, stories and letters (see README §10).
