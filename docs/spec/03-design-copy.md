<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 6. Design system and words

### 6.1 Colour tokens (contrast computed against WCAG 2.2)
| Token | Hex | Use | Contrast notes |
|---|---|---|---|
| Ink | `#1C2333` | body text | 14.4:1 on Mist, 15.7:1 on Card |
| Night | `#24305E` | brand, headings, hero background, primary buttons | 11.6:1 on Mist; Card text on Night 12.7:1 |
| Starlight | `#F2B544` | stars, highlights, focus ring on Night, small accents | **never text on light backgrounds** (1.7:1). OK on Night (6.9:1); Ink on Starlight 8.6:1 |
| Sage | `#37705F` | "next step" actions, success, calm progress | 5.3:1 on Mist, 5.8:1 on Card |
| Mist | `#F7F5F0` | page background (warm paper, not hospital white) | — |
| Card | `#FFFFFF` | cards, inputs | — |
| Muted | `#6B6558` | secondary text, captions | 5.3:1 on Mist |
| Line | `#E3DED3` | decorative dividers only | not for input borders |
| Border | `#8A8475` | input and control borders | 3.4:1 on Mist (≥ 3:1 UI rule) |
| Urgent | `#B42318` | urgent banner, red-flag only | 6.0:1 on Mist; white on Urgent 6.6:1 |

Why: the night sky is the late-night search for answers; stars are findings; lines between them are the connections a single appointment misses; warm paper and sage keep it calm and human, not clinical or alarming. Red appears **only** for real urgency so it keeps its meaning. Light theme only in v1.

### 6.2 Type and layout
- Body: **Atkinson Hyperlegible** (designed for low-vision legibility), 18 px base on mobile, line-height 1.55. Headings: **Fraunces** (warm serif), weights 600/700. Both via `next/font` (Google Fonts, OFL).
- Max text width 65ch. Mobile first, 360 px minimum. Touch targets ≥ 44 px (exceeds WCAG 24 px minimum). Visible focus ring: 3 px Starlight on Night surfaces, 3 px Night on light surfaces.
- Icons: Lucide (ISC). No stock photos of children. Illustration: abstract star fields only.

### 6.3 Voice
- Reading age about 12. Sentences ≤ 20 words. Second person ("you", "your child").
- Warm, steady, honest. No exclamation marks, no "Great job!", no fear words ("dangerous", "serious disease", "alarming").
- Always say what we don't know: "This doesn't tell us what's causing it. It helps you and your doctor decide what to check."
- End every screen with the next step.
- Parent view bans: disease names, %, "likely", "probability", "chance", "risk score", "diagnosis", "you have", "rule out", "rare disease" as a label for *their* child (fine in general explanations on /about).
- Clinician view: precise, terse, HPO IDs shown, no hedging fluff, disclaimer present.

### 6.4 Key copy (use verbatim unless the copy reviewer improves it)
- Hero H1: "Connect the dots no single appointment can see."
- Hero sub: "When your child's health worries don't add up, Constellation helps you gather the details that matter, know when to see a doctor, and bring a clear summary so they can see the whole picture."
- Primary CTA: "Start with your story" · Secondary: "See an example family (2 min)"
- How it works: 1 "Tell us what you've noticed, in your own words." 2 "Answer a few short questions at a time." 3 "Know when to see a doctor — and bring a one-page summary."
- Trust strip: "Not a diagnosis · Built on open medical knowledge · Delete your information any time"
- Round intro: "A few questions to fill in the picture. Answer what you can — 'Not sure' is fine."
- See-doctor: "It's a good time to see a doctor. Here's a one-page summary to bring, and questions you can ask."
- No-escalation: "Nothing you've told us needs a special appointment right now. Mention it at your next routine visit. Here's what to keep an eye on."

### 6.5 Mandatory texts
- **Global disclaimer (parent):** "Constellation does not diagnose. It helps you gather information and decide when to see a doctor. Always follow your doctor's advice. In an emergency, call your local emergency number."
- **Urgent (emergency):** "This needs urgent medical help. Call your local emergency number now (112 in India and Europe, 911 in the US) or go to the nearest emergency department. Your answers are saved — come back when your child is safe."
- **Urgent soon:** "Please see a doctor in the next day or two about this: {plain finding}. If it gets worse, call your local emergency number."
- **Clinician:** "Decision support for clinician review. Candidate patterns come from public phenotype–disease knowledge (HPO, Orphanet) and the findings recorded here. They are not a diagnosis and may be incomplete."
- **Demo:** "Example family — all details are made up."
- **AI disclosure (/about):** which parts use AI models, which do not (scoring, gates, safety rules), and that the code was built with AI coding assistants under human review.
