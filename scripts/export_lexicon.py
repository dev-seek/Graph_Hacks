"""Export the disease-name lexicon from FalkorDB (registry query) and probe recorded parent text.

`make lexicon` writes data/derived/disease_lexicon.json; `--probe` also scans the parent-facing
strings of the recorded demos and prints collisions (AGENTS.md rule 1).
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.graph.client import connect, rows  # noqa: E402
from app.kb.info import load_kb_info  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "derived" / "disease_lexicon.json"
MIN_LEN = int(os.environ.get("LEXICON_MIN_LEN", "4"))


def build() -> list[str]:
    info = load_kb_info()
    if info is None:
        raise SystemExit("no knowledge base built: run `make kb`")
    g = connect().select_graph(info.release)
    names = {str(r["name"]).strip() for r in rows(g, "q_all_disease_names", {}) if r["name"]}
    # A disease named exactly like an HPO sign ("Cleft palate") is a sign when it appears in a
    # parent's words: those names are not forbidden (ADR-0012). Every other disease name is.
    signs = {str(r["name"]).strip().lower() for r in rows(g, "q_all_term_names", {}) if r["name"]}
    short = {n for n in names if len(n) < MIN_LEN}
    overlap = sorted(n for n in names if len(n) >= MIN_LEN and n.lower() in signs)
    (OUT.parent / "disease_lexicon_sign_overlap.json").write_text(json.dumps(overlap))
    print(f"dropped: {len(short)} shorter than {MIN_LEN}; {len(overlap)} equal to an HPO sign name")
    return sorted(n for n in names if len(n) >= MIN_LEN and n.lower() not in signs)


def parent_strings(doc: dict[str, Any]) -> list[str]:
    """Strings a parent can see in a recorded demo (never gate/clinician/phenopacket/queries)."""
    out: list[str] = []

    def walk(x: Any) -> None:
        if isinstance(x, str):
            out.append(x)
        elif isinstance(x, list):
            for i in cast("list[Any]", x):
                walk(i)
        elif isinstance(x, dict):
            for k, v in cast("dict[str, Any]", x).items():
                if k not in {"queries", "gate", "clinician", "phenopacket", "params", "cypher"}:
                    walk(v)

    for s in doc["steps"]:
        out.append(s["caption"])
        walk(s["payload"])
    return out


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    names = build()
    OUT.write_text(json.dumps(names))
    print(f"lexicon: {len(names)} disease names -> {OUT.relative_to(ROOT)}")
    if "--probe" not in sys.argv:
        return
    pats = [(n, re.compile(r"\b" + re.escape(n) + r"\b", re.I)) for n in names]
    hits: dict[str, set[str]] = {}
    for f in sorted((ROOT / "data" / "demo").glob("*.json")):
        if f.name == "query_embeddings.json":
            continue
        doc = json.loads(f.read_text())
        for s in parent_strings(doc):
            for n, p in pats:
                if p.search(s):
                    hits.setdefault(f.stem, set()).add(f"{n} <- {s[:60]!r}")
    for k, v in hits.items():
        print(k, len(v))
        for x in sorted(v)[:10]:
            print("  ", x)
    print("collisions:", sum(len(v) for v in hits.values()))


if __name__ == "__main__":
    main()
