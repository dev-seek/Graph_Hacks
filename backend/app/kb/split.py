"""Dev/test split of the Phenopacket Store cases by source publication (spec §14).

One-shot: the test list is frozen from P1. A case belongs to the dev split with probability 0.30,
decided by a hash of (seed, PMID), so every case of a publication lands on the same side and the
assignment does not depend on file order or on the kb. Eligibility (resolves to a kb disease,
>= 5 present features) is applied later, at evaluation time, so the lists never change with the kb.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from app.kb.parsers.phenopackets import EvalCase, parse_phenopackets

SEED = 20260901
DEV_FRACTION = 0.30
ROOT = Path(__file__).resolve().parents[3]
SPLITS = ROOT / "eval" / "splits"


def is_dev(pmid_or_case: str, seed: int = SEED, dev_fraction: float = DEV_FRACTION) -> bool:
    digest = hashlib.sha256(f"{seed}:{pmid_or_case}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64 < dev_fraction


def assign(cases: list[EvalCase], seed: int = SEED) -> tuple[list[str], list[str], list[str]]:
    """-> (dev case ids, test case ids, test PMIDs). A case with no PMID is its own unit."""
    dev: list[str] = []
    test: list[str] = []
    test_pmids: set[str] = set()
    for c in sorted(cases, key=lambda c: c.case_id):
        if is_dev(c.pmid or c.case_id, seed):
            dev.append(c.case_id)
        else:
            test.append(c.case_id)
            if c.pmid:
                test_pmids.add(c.pmid)
    return dev, test, sorted(test_pmids)


def write_split(zip_path: Path, out_dir: Path = SPLITS, seed: int = SEED) -> dict[str, object]:
    test_file = out_dir / "test_ids.txt"
    if test_file.exists():
        raise FileExistsError(f"{test_file} exists: the test split is frozen and never rewritten")
    cases = parse_phenopackets(zip_path)
    ids = [c.case_id for c in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("phenopacket case ids are not unique")
    dev, test, test_pmids = assign(cases, seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "dev_ids.txt").write_text("\n".join(dev) + "\n", encoding="utf-8")
    test_file.write_text("\n".join(test) + "\n", encoding="utf-8")
    (out_dir / "test_pmids.txt").write_text("\n".join(test_pmids) + "\n", encoding="utf-8")
    sha = hashlib.sha256(test_file.read_bytes()).hexdigest()
    summary: dict[str, object] = {
        "seed": seed,
        "cases": len(cases),
        "dev": len(dev),
        "test": len(test),
        "test_pmids": len(test_pmids),
        "test_ids_sha256": sha,
    }
    (out_dir / "split_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary


if __name__ == "__main__":
    # Prints counts and the checksum only: per-case test output is never shown (AGENTS.md rule 9).
    print(json.dumps(write_split(ROOT / "data" / "raw" / "all_phenopackets.zip"), indent=2))
    sys.exit(0)
