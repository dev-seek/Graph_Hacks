"""Contract suite (spec §10.6): fixed synthetic cases per task, per candidate profile.

`python -m app.llm.contract fake` checks the plumbing in CI. With `ANTHROPIC_API_KEY` set,
`python -m app.llm.contract live` measures every candidate profile and writes the cheapest passing
one per task to `config/llm.yaml` (`chosen:`). Without a key nothing is written: "not measured".
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field

import yaml
from pydantic import BaseModel, ValidationError

from app.llm.adapters.anthropic_adapter import AnthropicAdapter
from app.llm.adapters.fake import FakeAdapter
from app.llm.lexicon import is_clean
from app.llm.port import LLMPort, Message, TaskId
from app.llm.router import wrap_input
from app.llm.schemas import (
    TASK_SCHEMAS,
    DocExtraction,
    Rephrase,
    SafetyConcerns,
    StoryExtraction,
)
from app.llm.settings import DEFAULT_PATH, LLMSettings, load_settings

MIN_VALIDITY = 0.95
MIN_SPAN_EXACT = 0.90
STORIES = [
    "He was floppy as a baby and he does not walk yet. He has had many chest infections.",
    "She has had seizures since she was one. Her head looks small. She is not talking.",
    "He tires quickly. No fever and no rash. His right eye turns inwards when tired.",
    "She was born early and was slow to feed. She does not sit without help at ten months.",
    "He has a heart murmur and a very short stature. He has never had a seizure.",
]
LETTERS = [
    "Examination: low muscle tone and a heart murmur. MRI brain normal.",
    "Findings: microcephaly. EEG shows no epileptiform activity. Eyes: strabismus.",
]
QUESTIONS = [
    {
        "question": "Does he tire quickly when he plays?",
        "why": "Tiring easily helps the doctor.",
        "age_months": 30,
    },
    {
        "question": "Has she had many chest infections?",
        "why": "Frequent infections are worth noting.",
        "age_months": 24,
    },
]
CASES_PER_TASK = 20


@dataclass
class Case:
    input_text: str


def build_cases(task: str) -> list[Case]:
    if task == "extract_story":
        base = [Case(s) for s in STORIES]
    elif task == "read_document":
        base = [Case(s) for s in LETTERS]
    elif task == "phrase_question":
        base = [Case(json.dumps(q)) for q in QUESTIONS]
    elif task == "safety_extra":
        base = [Case(s) for s in STORIES[:3]]
    else:
        base = [Case(STORIES[0])]
    return [base[i % len(base)] for i in range(CASES_PER_TASK)]


def spans_exact(out: BaseModel, text: str) -> tuple[int, int]:
    items = getattr(out, "items", None)
    if items is None:
        return (0, 0)
    ok = sum(1 for i in items if i.quote in text)
    return (ok, len(items))


@dataclass
class ProfileResult:
    task: str
    profile: str
    n: int = 0
    valid: int = 0
    span_ok: int = 0
    span_total: int = 0
    lexicon_ok: int = 0
    latencies: list[float] = field(default_factory=list[float])
    cost_usd: float = 0.0

    @property
    def validity(self) -> float:
        return self.valid / self.n if self.n else 0.0

    @property
    def span_exact(self) -> float:
        return self.span_ok / self.span_total if self.span_total else 1.0

    @property
    def passes(self) -> bool:
        lex = self.lexicon_ok == self.valid
        return self.validity >= MIN_VALIDITY and self.span_exact >= MIN_SPAN_EXACT and lex

    def row(self) -> str:
        p50 = statistics.median(self.latencies) if self.latencies else 0.0
        return (
            f"{self.task:22} {self.profile:13} valid {self.validity:5.0%}"
            f" span {self.span_exact:5.0%}"
            f" p50 {p50 * 1000:6.0f} ms cost/call ${self.cost_usd / max(self.n, 1):.5f}"
            f" {'PASS' if self.passes else 'FAIL'}"
        )


def run_profile(
    adapter: LLMPort,
    task: TaskId,
    profile: str,
    settings: LLMSettings,
    cost_of: Callable[[], float] | None = None,
) -> ProfileResult:
    schema = TASK_SCHEMAS[task]
    res = ProfileResult(task, profile)
    max_out = settings.profiles[profile].max_output_tokens
    for case in build_cases(task):
        res.n += 1
        t0 = time.perf_counter()
        try:
            out = adapter.generate_structured(
                task,
                [Message("user", wrap_input(case.input_text))],
                schema,
                max_output_tokens=max_out,
            )
        except (ValidationError, ValueError, RuntimeError):
            continue
        res.latencies.append(time.perf_counter() - t0)
        res.valid += 1
        ok, total = spans_exact(out, case.input_text)
        res.span_ok += ok
        res.span_total += total
        if isinstance(out, Rephrase):
            res.lexicon_ok += int(is_clean(out.question + " " + out.why))
        else:
            res.lexicon_ok += 1
        if cost_of:
            res.cost_usd += cost_of()
    return res


def usage_cost(adapter: AnthropicAdapter, model: str) -> float:
    pin, pout = adapter.settings.prices_usd_per_mtok.get(model, (0.0, 0.0))
    u = adapter.last_usage
    return (u.get("input", 0) * pin + u.get("output", 0) * pout) / 1_000_000


def cheapest_passing(results: list[ProfileResult]) -> dict[str, str]:
    best: dict[str, ProfileResult] = {}
    for r in results:
        if not r.passes:
            continue
        cur = best.get(r.task)
        if cur is None or r.cost_usd < cur.cost_usd:
            best[r.task] = r
    return {t: r.profile for t, r in best.items()}


def write_chosen(chosen: dict[str, str]) -> None:
    data = yaml.safe_load(DEFAULT_PATH.read_text(encoding="utf-8"))
    data["chosen"] = chosen
    DEFAULT_PATH.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def main(mode: str) -> int:
    settings = load_settings()
    results: list[ProfileResult] = []
    tasks: list[TaskId] = ["extract_story", "read_document", "phrase_question", "safety_extra"]
    if mode == "fake":
        fake = FakeAdapter()
        for task in tasks:
            profile = settings.profile_name_for(task)
            results.append(run_profile(fake, task, profile, settings))
        for r in results:
            print(r.row())  # noqa: T201
        print("contract (fake): plumbing only; NOT a measurement of any Claude profile")  # noqa: T201
        return 0 if all(r.passes for r in results) else 1
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY unset: not measured; config/llm.yaml unchanged")  # noqa: T201
        return 0
    live = AnthropicAdapter(settings)
    for task in tasks:
        for profile in settings.candidates.get(task, []):
            s = settings.model_copy(update={"chosen": {task: profile}})
            live.settings = s
            model = settings.profiles[profile].model
            r = run_profile(live, task, profile, s, lambda m=model: usage_cost(live, m))
            results.append(r)
            print(r.row())  # noqa: T201
    chosen = cheapest_passing(results)
    write_chosen(chosen)
    print(f"chosen: {chosen}")  # noqa: T201
    return 0


_ = (DocExtraction, SafetyConcerns, StoryExtraction)  # schemas exercised through TASK_SCHEMAS

if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "fake"))
