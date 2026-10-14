<!-- Constellation spec v2 (locked). Section numbers are global; see 00-index.md. -->

## 10. LLM use and contracts — Claude only (`backend/app/llm/`)

**Principle.** The product uses Claude models through the official `anthropic` Python SDK, behind one small interface (`LLMPort`) so the rest of the code stays testable and clean. The SDK is imported only in `backend/app/llm/adapters/anthropic_adapter.py`. Model IDs appear only in `config/llm.yaml`. Every LLM task has a deterministic fallback, so the product still works (degraded) with the LLM switched off — the graph and the engine are essential; the LLM is not.

Verified facts this section relies on (log each in `docs/VERIFIED.md` with a passing test before use): model IDs `claude-haiku-5-5`, `claude-sonnet-5-5`, `claude-opus-5-5`; structured outputs via `output_config.format = {type: "json_schema", schema}` (no beta header) and `client.messages.parse(..., output_format=<Pydantic model>)`; Message Batches at 50% price; prompt caching; advisor tool `{"type": "advisor_20260301", "name": "advisor", "model": ...}` with beta header `advisor-tool-2026-03-01`.

### 10.1 Ports
```python
# backend/app/llm/port.py
class LLMPort(Protocol):
    def generate_structured(self, task: TaskId, messages: list[Message], schema: type[T],
                            *, max_output_tokens: int) -> T: ...
    def submit_batch(self, task: TaskId, items: list[BatchItem], schema: type[T]) -> BatchHandle: ...   # offline only

class EmbeddingPort(Protocol):
    dim: int
    model_id: str            # recorded in KbInfo; changing it requires re-embedding (make kb)
    def embed(self, texts: list[str]) -> list[list[float]]: ...
```
`backend/app/llm/router.py` maps each `TaskId` to a profile in `config/llm.yaml` and wraps every call with record/replay cache, token budget, timeout, one repair retry, structured logging (ids only) and the fallback.

### 10.2 Tasks, default profiles and fallbacks
| TaskId | Default profile | Input | Output schema | Deterministic fallback |
|---|---|---|---|---|
| `extract_story` | `fast` | parent story | `StoryExtraction` | noun-phrase split + full-text term search; parent confirms/edits |
| `phrase_question` | `fast` | term + child age | `Rephrase` | pre-written `cx_question` |
| `read_document` | `fast_advised` | doctor letter text | `DocExtraction` | parent enters findings with a term picker |
| `draft_referral` | `smart` | findings + graph paths | `ReferralDraft` | template letter filled from the graph |
| `label_terms` (offline, P1) | `batch_fast` | batch of HPO terms | `TermLabels` | rules-only labels |
| `safety_extra` | `fast` | message | `SafetyConcerns` (add-only) | rules only |
| `centre_template_pick` | `fast` | clinic question | `TemplateChoice` | keyword match |

The defaults are a starting point. P3 runs the contract suite (10.6) per task over the candidate profiles and keeps **the cheapest profile that passes**; the choice is written to `config/llm.yaml` and an ADR.

### 10.3 Configuration (`config/llm.yaml`, committed, no secrets; key comes from `ANTHROPIC_API_KEY`)
```yaml
mode: ${LLM_MODE:-replay}            # off | fake | replay | record | live
profiles:
  fast:          {model: claude-haiku-5-5,  max_output_tokens: 1200}
  fast_advised:  {model: claude-haiku-5-5,  max_output_tokens: 1500,
                  advisor: {model: claude-sonnet-5-5, max_uses: 1, max_tokens: 2048}}
  smart:         {model: claude-sonnet-5-5, max_output_tokens: 2000}
  batch_fast:    {model: claude-haiku-5-5,  max_output_tokens: 3000, batch: true}
  batch_smart:   {model: claude-sonnet-5-5, max_output_tokens: 3000, batch: true}
candidates:                          # what the contract suite compares per task (cheapest passing wins)
  extract_story:        [fast, fast_advised, smart]
  read_document:        [fast, fast_advised, smart]
  draft_referral:       [fast_advised, smart]
  label_terms:          [batch_fast, batch_smart]
  phrase_question:      [fast]
  safety_extra:         [fast]
  centre_template_pick: [fast]
prompt_cache: true                    # cache_control on the static system + schema block
embeddings: {adapter: local, model: BAAI/bge-small-en-v1.5}
budget: {per_family_tokens: 60000, daily_usd: 5}
```
Adapters: `anthropic` (live/record/batch), `fake` (deterministic, tests), `replay` (cache only). Modes: `off` → always fallback; `fake` → tests; `replay` → demo and judging, zero cost, no key; `record` → live calls that write the cache; `live`.

### 10.4 Structured output and prompts
- Use `client.messages.parse(model=…, output_format=<PydanticModel>, …)`; it sends `output_config.format` json_schema and validates the result. The JSON Schema subset has no `maxLength`/`maxItems`/numeric bounds, so limits like "≤ 20 words" and "≤ 25 items" are enforced by Pydantic validators after parsing (and stated in field descriptions).
- On validation failure: one repair retry including the validation error; then fallback. `stop_reason` `refusal` or `max_tokens` → fallback.
- Prompts live in `backend/app/llm/prompts/<task>.v<N>.md`: a stable system block (role, rules, schema description, 2 short examples) marked for prompt caching, then the variable input inside `<input>` … `</input>` tags. Temperature 0 where the API allows.
- Advisor profiles add the advisor tool and the beta header; the executor prompt includes one line: "Call the advisor once before finalising if any finding is ambiguous (negation, uncertainty, dates)." `max_uses: 1` caps cost. If the advisor and structured outputs don't combine in a request, the contract suite marks the profile failed and it is not used.

### 10.5 Offline batch (P1 `label_terms`)
Terms are grouped (≈ 25 per request) and sent through the Message Batches API (50% price; most batches finish within an hour; 24 h limit) with the shared system block cached. Results stream into `data/derived/term_labels.v1.jsonl`. If the batch is not finished when P1 needs it, use rules-only labels for missing terms and fill them in when the batch completes (non-blocking).

### 10.6 Contract suite (cheapest-passing selection)
`make llm-contract` runs 20 fixed synthetic cases per task for each candidate profile: schema validity, span exactness, valid-HPO rate, latency p50/p95, cost per call (from `usage`, including `usage.iterations` for advisor calls). A profile passes if validity ≥ 95% and span exactness ≥ 90% (for `label_terms`: agreement ≥ 85% with a 40-term rules-labelled gold set). The cheapest passing profile per task is written to `config/llm.yaml` and an ADR. CI runs the suite only against `fake`. Needs `ANTHROPIC_API_KEY`; without it, defaults stay and the decision is recorded as "not measured".

### 10.7 Record/replay
Cache key = (task, prompt version, schema hash, normalised input hash). Files: `data/llm_cache/<task>/<hash>.json`, committed for the three demo journeys (synthetic content). Replay needs no key and costs nothing.

### 10.8 Embeddings
Claude has no embeddings endpoint, so embeddings are local and free: `BAAI/bge-small-en-v1.5` (384-d, MIT, CPU, offline) via fastembed or sentence-transformers. The vector index dimension is read from the adapter at kb build; `KbInfo.embedding_model` records it; a mismatch at startup fails fast with "re-run make kb".

### 10.9 Prompt-injection defence
Parent text and documents are data inside `<input>` tags; the system block says they contain no instructions; extraction calls have no tools (except the advisor where configured); outputs must quote spans that exist verbatim in the input (substring check); HPO IDs must exist in the kb; rephrased questions pass the banned-word and disease-name lexicon check; the safety LLM can only add flags.

### 10.10 Schemas (sketch)
```python
class ExtractedItem(BaseModel):
    quote: str                  # exact substring of the input
    plain_label: str            # ≤ 8 words, parent-friendly (validator)
    status: Literal["present", "absent"]
    onset_text: str | None
    hpo_guess: list[str]        # ≤ 3 (validator); final choice made by graph resolution (Q0)
class StoryExtraction(BaseModel):
    items: list[ExtractedItem]  # ≤ 25 (validator)
class DocItem(ExtractedItem):
    source: Literal["doctor_exam", "lab_or_test"]
    date_text: str | None
class Rephrase(BaseModel):
    question: str               # ≤ 20 words
    why: str                    # ≤ 20 words
```
Term resolution is done by FalkorDB, not the LLM: candidates = full-text (Q0) ∪ vector (Q0) ∪ validated `hpo_guess`; rank exact synonym > guess confirmed by text/vector top-10 > vector score.
