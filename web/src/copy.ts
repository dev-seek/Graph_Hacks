// All fixed words from spec §6.4–6.5 live here, verbatim. The copy reviewer and the banned-word
// test read this one file. Do not reword the "mandatory" block (spec §6.5).

export const HERO = {
  h1: "Connect the dots no single appointment can see.",
  // Shortened from spec §6.4 by the copy reviewer (one 34-word sentence was over the 20-word rule).
  sub: "When your child's health worries don't add up, we help you gather the details that matter. We tell you when to see a doctor. You bring a clear summary, so the doctor can see the whole picture.",
  primary: "Start with your story",
  secondary: "See an example family (2 min)",
};

export const HOW_IT_WORKS = [
  "Tell us what you've noticed, in your own words.",
  "Answer a few short questions at a time.",
  "Know when to see a doctor — and bring a one-page summary.",
];

export const TRUST_STRIP =
  "Not a diagnosis · Built on open medical knowledge · Delete your information any time";

export const ROUND_INTRO =
  "A few questions to fill in the picture. Answer what you can — 'Not sure' is fine.";

export const SEE_DOCTOR =
  "It's a good time to see a doctor. Here's a one-page summary to bring, and questions you can ask.";

export const NO_ESCALATION =
  "Nothing you've told us needs a special appointment right now. Mention it at your next routine visit. Here's what to keep an eye on.";

// --- Mandatory texts (spec §6.5) -------------------------------------------------------------
export const PARENT_DISCLAIMER =
  "Constellation does not diagnose. It helps you gather information and decide when to see a doctor. Always follow your doctor's advice. In an emergency, call your local emergency number.";

export const URGENT =
  "This needs urgent medical help. Call your local emergency number now (112 in India and Europe, 911 in the US) or go to the nearest emergency department. Your answers are saved — come back when your child is safe.";

export const urgentSoon = (plainFinding: string) =>
  `Please see a doctor in the next day or two about this: ${plainFinding}. If it gets worse, call your local emergency number.`;

export const CLINICIAN_DISCLAIMER =
  "Decision support for clinician review. Candidate patterns come from public phenotype–disease knowledge (HPO, Orphanet) and the findings recorded here. They are not a diagnosis and may be incomplete.";

export const DEMO_BANNER = "Example family — all details are made up.";

export const AI_DISCLOSURE = [
  "Claude (an AI model) reads your words and turns them into plain-language findings, writes question wording and drafts letters. It never decides who needs to see a doctor.",
  "Scoring, ranking, the see-a-doctor decision and every safety rule are ordinary code reading a FalkorDB graph. No AI model is involved in them.",
  "This project was built with AI coding assistants under human review. The safety rules, 40 everyday-case vignettes, demo stories and doctor letters were drafted by Claude and then reviewed and edited by a person.",
];

// Words that must never reach a parent screen (spec §6.3). Used by tests.
export const PARENT_BANNED = [
  "probability",
  "likely",
  "chance",
  "risk score",
  "diagnosis",
  "you have",
  "rule out",
  "rare disease",
  "posterior",
];
