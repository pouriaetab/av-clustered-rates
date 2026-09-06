"""
Figure 1 for the paper: actual coverage of a nominal 95% confidence interval
for the fleet event rate, as a function of the design effect, with and without
the effective-sample-size correction.

Reads its numbers from sim_clustered_av_rates.py so the figure and the tables
cannot drift apart.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from sim_clustered_av_rates import coverage_study, deff_true

# Okabe-Ito blue / vermillion: validated CVD-safe pair, distinct in grayscale,
# and reinforced with distinct markers so identity is never colour-alone.
C_NAIVE = "#D55E00"
C_CORR = "#0072B2"
INK = "#1a1a1a"
MUTED = "#6b6b6b"
GRID = "#dcdcdc"

THETA = 1e-4
MILES = 5_000_000
N_REP = 20_000

# p values chosen to sweep DEFF from 1 to 7
P_GRID = [1.0, 0.85, 0.75, 0.6, 0.5, 0.42, 0.35, 0.3, 0.25]


def main():
    deffs, cov_naive, cov_corr = [], [], []
    for p in P_GRID:
        r = coverage_study(THETA, p, MILES, n_rep=N_REP)
        deffs.append(r["DEFF_true"])
        cov_naive.append(r["coverage_naive"] * 100)
        cov_corr.append(r["coverage_corrected"] * 100)
        print(f"DEFF {r['DEFF_true']:.2f}  naive {r['coverage_naive']:.1%}  "
              f"corrected {r['coverage_corrected']:.1%}")

    plt.rcParams.update({
        "font.family": "serif",
        "font.size": 9,
        "axes.edgecolor": MUTED,
        "axes.labelcolor": INK,
        "text.color": INK,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
    })

    fig, ax = plt.subplots(figsize=(5.4, 3.4))

    # Nominal level: a recessive reference, not a data series.
    ax.axhline(95, color=MUTED, linewidth=1.0, linestyle=(0, (1, 2.5)), zorder=1)
    ax.annotate("nominal 95%", xy=(2.2, 95), xytext=(2.2, 96.4),
                ha="center", va="bottom", fontsize=8, color=MUTED)

    ax.plot(deffs, cov_corr, color=C_CORR, linewidth=2, marker="s",
            markersize=5, markeredgecolor="white", markeredgewidth=1.0,
            zorder=3, label="Corrected (effective sample size)")
    ax.plot(deffs, cov_naive, color=C_NAIVE, linewidth=2, marker="o",
            markersize=5, markeredgecolor="white", markeredgewidth=1.0,
            zorder=3, label="Naive (Poisson, independence assumed)")

    # Direct labels: identity without relying on colour alone.
    ax.annotate("Corrected", xy=(deffs[-1], cov_corr[-1]),
                xytext=(-4, 9), textcoords="offset points",
                ha="right", fontsize=8.5, color=C_CORR, weight="bold")
    ax.annotate("Naive", xy=(deffs[-1], cov_naive[-1]),
                xytext=(-4, -14), textcoords="offset points",
                ha="right", fontsize=8.5, color=C_NAIVE, weight="bold")

    ax.set_xlabel("Design effect  DEFF $= E[K^2]/E[K]$")
    ax.set_ylabel("Actual coverage of a nominal 95% CI (%)")
    ax.set_ylim(45, 100)
    ax.set_xlim(0.8, 7.2)
    ax.set_yticks([50, 60, 70, 80, 90, 95, 100])
    ax.grid(axis="y", color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)

    leg = ax.legend(loc="lower left", frameon=False, fontsize=8,
                    handlelength=2.4, borderpad=0.2)
    for t in leg.get_texts():
        t.set_color(INK)

    fig.tight_layout()
    fig.savefig("coverage_vs_deff.pdf", bbox_inches="tight")
    fig.savefig("coverage_vs_deff.png", dpi=200, bbox_inches="tight")
    print("\nwrote coverage_vs_deff.pdf and coverage_vs_deff.png")


if __name__ == "__main__":
    main()
