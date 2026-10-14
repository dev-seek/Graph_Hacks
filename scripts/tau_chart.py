# pyright: basic
"""Trade-off chart for ADR-0006 from .build/logs/tune-taus.json (dev + negatives only)."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
data = json.loads((ROOT / ".build" / "logs" / "tune-taus.json").read_text())
pts = data["points"]
ok = [p for p in pts if p["false_referral"] <= 0.10]
fig, ax = plt.subplots(figsize=(6.5, 4.2), dpi=140)
ax.scatter(
    [100 * p["false_see_doctor"] for p in ok],
    [100 * p["sensitivity"] for p in ok],
    s=10,
    color="#8a9bb5",
    label="tau settings with false referral <= 10%",
)
c, d = data["chosen"], data["default"]
ax.scatter(
    100 * c["false_see_doctor"], 100 * c["sensitivity"], s=70, color="#d1495b", label="chosen"
)
ax.scatter(
    100 * d["false_see_doctor"],
    100 * d["sensitivity"],
    s=70,
    marker="s",
    color="#2b6777",
    label="spec defaults",
)
ax.axvline(30, color="#555", ls="--", lw=1)
ax.text(30.5, 1, "false see-doctor limit 30%", fontsize=7)
ax.set_xlabel("false see-doctor on 40 synthetic negatives (%)")
ax.set_ylabel("referral sensitivity on dev positives (%)")
ax.set_title("Gate thresholds: sensitivity vs false alarms (dev only)")
ax.legend(fontsize=7)
fig.tight_layout()
out = ROOT / "docs" / "adr" / "0006-tau-tradeoff.png"
fig.savefig(out)
print(f"wrote {out.relative_to(ROOT)}")
