from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"
SPLITS = ROOT / "eval" / "splits"
REPORTS = ROOT / "eval" / "reports"
