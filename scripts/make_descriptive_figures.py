"""Generate descriptive figures for the paper draft.

Outputs:
  - out/figures/dataset_overview.png: 4-panel dataset descriptives
  - out/figures/saints_score_ranked.png: top-N attackers ranked by naive score
    with Bayesian posterior means and 89% HDIs overlaid.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "out" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update(
    {
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "savefig.bbox": "tight",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
    }
)


def dataset_overview() -> Path:
    cases = pl.read_csv(ROOT / "out" / "cases.csv", infer_schema_length=10000)
    naive = pl.read_csv(ROOT / "out" / "scores" / "saints_naive.csv")

    fig, axes = plt.subplots(2, 2, figsize=(11, 8))

    # (a) Attacks per year
    by_year = (
        cases.group_by("event_year")
        .len()
        .sort("event_year")
    )
    ax = axes[0, 0]
    ax.bar(by_year["event_year"].to_list(), by_year["len"].to_list(), color="#3b6ea5")
    ax.set_xlabel("Event year")
    ax.set_ylabel("Number of attacks")
    ax.set_title("(a) Attacks per year")
    ax.grid(axis="y", alpha=0.3)

    # (b) Top countries
    top_c = (
        cases.group_by("country")
        .len()
        .sort("len", descending=True)
        .head(12)
        .reverse()
    )
    ax = axes[0, 1]
    ax.barh(top_c["country"].to_list(), top_c["len"].to_list(), color="#a4553b")
    ax.set_xlabel("Number of attacks")
    ax.set_title("(b) Top 12 countries by attack count")
    ax.grid(axis="x", alpha=0.3)

    # (c) Fatalities distribution (log-x)
    fat = cases["fatalities_total_incl_perp"].drop_nulls().to_numpy().astype(float)
    fat_pos = np.maximum(fat, 0.5)  # shift for log axis
    ax = axes[1, 0]
    bins = np.logspace(np.log10(0.5), np.log10(max(fat_pos.max(), 2)), 25)
    ax.hist(fat_pos, bins=bins, color="#4b7f52", edgecolor="white")
    ax.set_xscale("log")
    ax.set_xlabel("Total fatalities (incl. perpetrator, log scale)")
    ax.set_ylabel("Number of attacks")
    ax.set_title(f"(c) Fatalities distribution (median = {int(np.median(fat))})")
    ax.grid(axis="y", alpha=0.3)

    # (d) Mention-count distribution on /pol/
    n = naive["n_total"].drop_nulls().to_numpy().astype(float)
    n_plot = np.maximum(n, 0.5)
    ax = axes[1, 1]
    bins = np.logspace(np.log10(0.5), np.log10(max(n_plot.max(), 2)), 25)
    ax.hist(n_plot, bins=bins, color="#6a4b8a", edgecolor="white")
    ax.set_xscale("log")
    ax.set_xlabel("Confirmed mentions on /pol/ (log scale)")
    ax.set_ylabel("Number of attackers")
    n_with = int((n >= 1).sum())
    ax.set_title(f"(d) Mentions per attacker (n={n_with} with ≥1 mention)")
    ax.grid(axis="y", alpha=0.3)

    fig.suptitle(
        f"Dataset overview: {cases.height} attacks, "
        f"{int(cases['event_year'].min())}–{int(cases['event_year'].max())}",
        fontsize=13,
    )
    fig.tight_layout()
    out = OUT / "dataset_overview.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def saints_score_ranked(top_n: int = 30) -> Path:
    naive = pl.read_csv(ROOT / "out" / "scores" / "saints_naive.csv")
    bayes = pl.read_csv(ROOT / "out" / "scores" / "saints_bayes.csv")

    df = naive.join(bayes, on="attacker_id", how="left").sort(
        "saints_naive", descending=True
    )
    top = df.head(top_n).reverse()  # reverse so highest appears at top

    ids = top["attacker_id"].to_list()
    naive_scores = top["saints_naive"].to_numpy()
    bayes_mean = top["saints_bayes_mean"].to_numpy()
    hdi_lo = top["saints_bayes_hdi_lo"].to_numpy()
    hdi_hi = top["saints_bayes_hdi_hi"].to_numpy()

    fig, ax = plt.subplots(figsize=(9, max(6, 0.28 * top_n)))
    y = np.arange(top_n)

    ax.barh(
        y,
        naive_scores,
        color="#3b6ea5",
        alpha=0.75,
        label="Naïve Saints Score",
    )
    ax.errorbar(
        bayes_mean,
        y,
        xerr=[bayes_mean - hdi_lo, hdi_hi - bayes_mean],
        fmt="o",
        color="#a4553b",
        ecolor="#a4553b",
        elinewidth=1.0,
        capsize=2,
        markersize=3,
        label="Bayesian posterior mean (89% HDI)",
    )

    ax.set_yticks(y)
    ax.set_yticklabels(ids, fontsize=8)
    ax.axvline(0, color="gray", linewidth=0.8, linestyle="--")
    ax.set_xlabel("Saints Score")
    ax.set_title(f"Top {top_n} attackers by naïve Saints Score")
    ax.legend(loc="lower right", fontsize=9)
    ax.grid(axis="x", alpha=0.3)

    fig.tight_layout()
    out = OUT / "saints_score_ranked.png"
    fig.savefig(out)
    plt.close(fig)
    return out


if __name__ == "__main__":
    p1 = dataset_overview()
    p2 = saints_score_ranked(top_n=30)
    print(f"Wrote {p1}")
    print(f"Wrote {p2}")
