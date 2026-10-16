# pyright: basic
# ruff: noqa: E501
"""Render the evaluation report (markdown + PNG charts) from the aggregated JSON (spec §14)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from app.eval.paths import REPORTS  # noqa: E402

BLUE, ORANGE, GREY, TEAL = "#0072B2", "#D55E00", "#8C8C8C", "#009E73"
METHODS = ("B0 story only", "B1 random x4", "B2 frequent x4")


def pct(s: dict[str, float], k: str) -> str:
    return f"{100 * s[k]:.1f} [{100 * s[k + '_lo']:.1f}, {100 * s[k + '_hi']:.1f}]"


def method_rows(t: dict[str, Any]) -> list[tuple[str, dict[str, float]]]:
    return [
        (METHODS[0], t[METHODS[0]]),
        (METHODS[1], t[METHODS[1]]),
        (METHODS[2], t[METHODS[2]]),
        ("Ours, 4 rounds", t["Ours by round"]["4"]),
        ("Ours, after doctor visit", t["Ours after doctor"]),
    ]


def table(t: dict[str, Any]) -> list[str]:
    out = [
        "| Method | top-1 % [95% CI] | top-3 % | top-10 % | MRR | median rank |",
        "|---|---|---|---|---|---|",
    ]
    for name, s in method_rows(t):
        out.append(
            f"| {name} | {pct(s, 'top1')} | {pct(s, 'top3')} | {pct(s, 'top10')} | "
            f"{s['mrr']:.3f} | {s['median_rank']:.0f} |"
        )
    return out


def charts(rep: dict[str, Any], stem: Path) -> list[Path]:
    made: list[Path] = []
    # 1. top-10 by method, lpo (headline) vs standard
    fig, ax = plt.subplots(figsize=(8, 4.8))
    labels = [n for n, _ in method_rows(rep["lpo"]["all"])]
    y = range(len(labels))
    for off, kb, colour, name in (
        (-0.2, "lpo", BLUE, "leave-publication-out (headline)"),
        (0.2, "std", GREY, "standard kb (leaky)"),
    ):
        vals = [s["top10"] * 100 for _, s in method_rows(rep[kb]["all"])]
        lo = [100 * (s["top10"] - s["top10_lo"]) for _, s in method_rows(rep[kb]["all"])]
        hi = [100 * (s["top10_hi"] - s["top10"]) for _, s in method_rows(rep[kb]["all"])]
        ax.barh(
            [i + off for i in y],
            vals,
            height=0.36,
            color=colour,
            label=name,
            xerr=[lo, hi],
            ecolor="#333",
            capsize=2,
        )
    ax.set_yticks(list(y), labels)
    ax.invert_yaxis()
    ax.set_xlabel("Target in top 10 (% of cases, 95% CI)")
    ax.set_title("Top-10 hit rate on the frozen test split")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.16), ncol=2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = stem.with_name(stem.name + "-top10.png")
    fig.savefig(p, dpi=150)
    plt.close(fig)
    made.append(p)
    # 2. Ours by round (lpo)
    fig, ax = plt.subplots(figsize=(8, 4.2))
    rounds = sorted(rep["lpo"]["all"]["Ours by round"], key=int)
    for k, colour in (("top1", ORANGE), ("top3", TEAL), ("top10", BLUE)):
        v = [100 * rep["lpo"]["all"]["Ours by round"][r][k] for r in rounds]
        ax.plot(
            [int(r) for r in rounds], v, marker="o", color=colour, label=k.replace("top", "top-")
        )
    ax.set_xticks([int(r) for r in rounds])
    ax.set_xlabel("Home question rounds asked")
    ax.set_ylabel("Cases (%)")
    ax.set_title("Ours: target rank by round (leave-publication-out)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = stem.with_name(stem.name + "-rounds.png")
    fig.savefig(p, dpi=150)
    plt.close(fig)
    made.append(p)
    # 3. answer-model sensitivity
    fig, ax = plt.subplots(figsize=(6.5, 4))
    ks = sorted(rep["no_rate_sweep"])
    ax.bar(
        range(len(ks)),
        [100 * rep["no_rate_sweep"][k]["round4"]["top10"] for k in ks],
        color=BLUE,
        width=0.5,
    )
    ax.set_xticks(range(len(ks)), [f"{int(float(k) * 100)}% 'no'" for k in ks])
    ax.set_ylabel("Top-10 after 4 rounds (%)")
    ax.set_title("Sensitivity to how often an unknown sign is answered 'no'")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    p = stem.with_name(stem.name + "-answers.png")
    fig.savefig(p, dpi=150)
    plt.close(fig)
    made.append(p)
    return made


def render(rep: dict[str, Any], stem: Path) -> Path:
    L: list[str] = []
    a = L.append
    a(f"# Evaluation report ({rep['split']} split, {rep['date']})")
    a("")
    a(
        "**Honest framing.** Real published cases (Phenopacket Store 0.1.27) with *simulated* parent answers. Not a clinical validation. "
        "Published figures for other systems (GPT-4 19.2% top-1 / 32.5% top-10; Exomiser phenotype-only 35.5% top-1; DeepRare 57.18% Recall@1) "
        "are context only: different datasets and settings."
    )
    a("")
    a(
        f"- Split file SHA-256 (expected): `{rep['test_ids_sha256_expected']}`; split size {rep['split_size']}; cases evaluated **{rep['cases_evaluated']}** (fixed on the standard kb, ADR-0013)."
    )
    a(
        f"- Target still annotated in the leave-publication-out kb: {rep['lpo_target_still_annotated']} cases; the rest count as misses in the headline."
    )
    a(
        f"- Coverage (P1): {rep['coverage']['standard_pct']}% of all store cases resolve on the standard kb; {rep['coverage']['lpo_test_pct']}% of test cases resolve on lpo."
    )
    a(
        f"- kb `{rep['kb']}`; taus {rep['taus']}; `config/engine.yaml` SHA-256 `{rep.get('engine_yaml_sha256', '?')[:16]}…`."
    )
    a(f"- Query errors after retries (unresolved): {rep['errors'] or 'none'}.")
    a("")
    for kb, title in (
        ("lpo", "Headline: leave-publication-out kb, all cases in the list"),
        ("std", "Standard kb (leaky; context only)"),
    ):
        a(f"## {title}")
        a("")
        t = rep[kb]["all"]
        a(f"n = {t['n']} cases. Hit rule: exact mappings only.")
        a("")
        L.extend(table(t))
        a("")
        a(
            "Paired top-10 gain of Ours (4 rounds) over: "
            + "; ".join(
                f"{b} {100 * t[f'top10_gain_vs_{b}'][0]:+.1f} to {100 * t[f'top10_gain_vs_{b}'][1]:+.1f} pts"
                for b in ("B0", "B1", "B2")
            )
        )
        a("")
        a(
            f"Mean questions asked: {t['mean_questions_asked']:.1f}; median round latency {t['round_ms_median']:.0f} ms (p90 {t['round_ms_p90']:.0f} ms)."
        )
        a("")
    a("## Leave-publication-out, only cases whose target is still annotated")
    a("")
    L.extend(table(rep["lpo"]["annotated_only"]))
    a("")
    a("## Referral behaviour (fixed taus)")
    a("")
    a("| kb | referral sensitivity | see a doctor | watch | median rounds to see-doctor |")
    a("|---|---|---|---|---|")
    for kb in ("lpo", "std"):
        r = rep[kb]["referral"]
        a(
            f"| {kb} | {100 * r['referral_sensitivity']:.1f}% | {100 * r['see_doctor']:.1f}% | {100 * r['watch']:.1f}% | {r['median_rounds_to_see_doctor']} |"
        )
    a("")
    a("## Synthetic negatives (40 reviewed vignettes)")
    a("")
    a("| kb | false referral | false see-doctor | safety-rules-only floor |")
    a("|---|---|---|---|")
    for kb in ("lpo", "std"):
        n = rep[kb]["negatives"]
        a(
            f"| {kb} | {100 * n['false_referral']:.1f}% | {100 * n['false_see_doctor']:.1f}% | {100 * n['safety_floor_see_doctor']:.1f}% |"
        )
    a("")
    a("## Sensitivity to the simulated parent (lpo, Ours)")
    a("")
    a(
        "| unknown sign answered 'no' | top-1 % | top-10 % (4 rounds) | top-10 % after doctor | referral sensitivity |"
    )
    a("|---|---|---|---|---|")
    for k in sorted(rep["no_rate_sweep"]):
        s = rep["no_rate_sweep"][k]
        a(
            f"| {int(float(k) * 100)}% | {pct(s['round4'], 'top1')} | {pct(s['round4'], 'top10')} | {pct(s['after_doctor'], 'top10')} | {100 * s['referral']['referral_sensitivity']:.1f}% |"
        )
    a("")
    a("## Threshold sweep (report only; no re-tuning on the test split)")
    a("")
    for kb in ("lpo", "std"):
        sw = rep[kb]["tau_sweep"]
        a(
            f"- {kb}: {sw['feasible_points']} of {sw['points']} tau triples meet the pre-declared limits (false referral <= 10%, false see-doctor <= 30%); sensitivity range among them {sw['sensitivity_range_feasible']}; best by the pre-registered rule {sw['best_feasible_by_preregistered_rule']}."
        )
    a("")
    a("## Charts")
    a("")
    for p in charts(rep, stem):
        a(f"![{p.stem}]({p.name})")
    md = stem.with_suffix(".md")
    md.write_text("\n".join(L) + "\n")
    return md


def main(argv: list[str]) -> int:
    path = Path(argv[0]) if argv else sorted(REPORTS.glob("*.json"))[-1]
    rep = json.loads(path.read_text())
    print(f"wrote {render(rep, path.with_suffix(''))}")  # noqa: T201
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
