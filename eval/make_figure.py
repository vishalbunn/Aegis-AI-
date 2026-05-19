"""
Generate the headline results figure for the README/LinkedIn/SOP.

Reads the most recent eval/results_*.json and produces a clean two-panel
PNG showing the comparative metrics between parallel and sequential debate.

Usage:
    python -m eval.make_figure                  # auto-find latest results JSON
    python -m eval.make_figure --json eval/results_20260512_222429.json
    python -m eval.make_figure --out docs/headline.png
"""
import json
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np


# Editorial colors matching the project's design language
COLORS = {
    "ink":     "#0a0a0f",
    "paper":   "#f5f0e8",
    "gold":    "#c9a84c",
    "pro":     "#1a6b3c",
    "con":     "#8b1a1a",
    "muted":   "#888888",
    "rule":    "#dad5cc",
}


def latest_results_json(eval_dir: Path) -> Path:
    files = sorted(eval_dir.glob("results_*.json"))
    if not files:
        raise FileNotFoundError(f"No results_*.json in {eval_dir}")
    return files[-1]


def make_figure(json_path: Path, out_path: Path, title_suffix: str = ""):
    data = json.loads(json_path.read_text(encoding="utf-8"))
    par = data["parallel_aggregate"]
    seq = data["sequential_aggregate"]

    # Set the global style
    plt.rcParams.update({
        "font.family":     "DejaVu Sans Mono",
        "font.size":       10,
        "axes.edgecolor":  COLORS["ink"],
        "axes.labelcolor": COLORS["ink"],
        "axes.titlecolor": COLORS["ink"],
        "xtick.color":     COLORS["ink"],
        "ytick.color":     COLORS["ink"],
        "axes.spines.top":   False,
        "axes.spines.right": False,
        "savefig.facecolor": COLORS["paper"],
        "axes.facecolor":    COLORS["paper"],
        "figure.facecolor":  COLORS["paper"],
    })

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

    # ─── LEFT PANEL — the four key metrics ──────────────────────────
    metrics = [
        ("Argument\nDiversity",  par.get("avg_diversity", 0),     seq.get("avg_diversity", 0)),
        ("Pro Stance\nDrift R1→Rn", par.get("avg_pro_drift", 0),  seq.get("avg_pro_drift", 0)),
        ("Con Stance\nDrift R1→Rn", par.get("avg_con_drift", 0),  seq.get("avg_con_drift", 0)),
    ]

    labels = [m[0] for m in metrics]
    parallel_vals = [m[1] for m in metrics]
    sequential_vals = [m[2] for m in metrics]

    x = np.arange(len(labels))
    width = 0.36

    bars1 = ax1.bar(x - width/2, parallel_vals, width,
                    label="Parallel (v4 baseline)", color=COLORS["muted"], edgecolor=COLORS["ink"], linewidth=0.5)
    bars2 = ax1.bar(x + width/2, sequential_vals, width,
                    label="Sequential (v5)",        color=COLORS["gold"],  edgecolor=COLORS["ink"], linewidth=0.5)

    # Annotate bars with values
    for bars in (bars1, bars2):
        for bar in bars:
            h = bar.get_height()
            ax1.annotate(f"{h:.2f}",
                         xy=(bar.get_x() + bar.get_width() / 2, h),
                         xytext=(0, 3), textcoords="offset points",
                         ha="center", va="bottom", fontsize=9, color=COLORS["ink"])

    ax1.set_ylabel("TF-IDF distance (0 = identical, 1 = orthogonal)", fontsize=10)
    ax1.set_title("Argument Refinement", fontsize=12, fontweight="bold", pad=12, loc="left")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, fontsize=9)
    ax1.set_ylim(0, max(max(parallel_vals), max(sequential_vals)) * 1.25 + 0.1)
    ax1.legend(loc="upper left", frameon=False, fontsize=9)
    ax1.grid(axis="y", alpha=0.2, linestyle="--", color=COLORS["muted"])

    # ─── RIGHT PANEL — verdict alignment / trap resistance ──────────
    metrics2 = [
        ("Verdict\nAlignment",  par.get("verdict_alignment", 0), seq.get("verdict_alignment", 0)),
        ("Trap-case\nResistance", par.get("trap_resistance", 0), seq.get("trap_resistance", 0)),
    ]

    labels2 = [m[0] for m in metrics2]
    parallel_vals2 = [m[1] for m in metrics2]
    sequential_vals2 = [m[2] for m in metrics2]

    x2 = np.arange(len(labels2))

    bars3 = ax2.bar(x2 - width/2, parallel_vals2, width,
                    label="Parallel (v4 baseline)", color=COLORS["muted"], edgecolor=COLORS["ink"], linewidth=0.5)
    bars4 = ax2.bar(x2 + width/2, sequential_vals2, width,
                    label="Sequential (v5)",        color=COLORS["gold"],  edgecolor=COLORS["ink"], linewidth=0.5)

    for bars in (bars3, bars4):
        for bar in bars:
            h = bar.get_height()
            ax2.annotate(f"{h:.0f}%",
                         xy=(bar.get_x() + bar.get_width() / 2, h),
                         xytext=(0, 3), textcoords="offset points",
                         ha="center", va="bottom", fontsize=10, color=COLORS["ink"], fontweight="bold")

    ax2.set_ylabel("Alignment with reference (%)", fontsize=10)
    ax2.set_title("Decision Quality", fontsize=12, fontweight="bold", pad=12, loc="left")
    ax2.set_xticks(x2)
    ax2.set_xticklabels(labels2, fontsize=9)
    ax2.set_ylim(0, 105)
    ax2.legend(loc="upper left", frameon=False, fontsize=9)
    ax2.grid(axis="y", alpha=0.2, linestyle="--", color=COLORS["muted"])

    # Add a callout arrow on the trap-resistance bars (the headline finding)
    delta = seq.get("trap_resistance", 0) - par.get("trap_resistance", 0)
    if delta > 0:
        ax2.annotate(f"+{delta:.0f} pp",
                     xy=(1 + width/2, seq.get("trap_resistance", 0)),
                     xytext=(1 + width/2 + 0.3, seq.get("trap_resistance", 0) + 10),
                     fontsize=11, color=COLORS["con"], fontweight="bold",
                     arrowprops=dict(arrowstyle="->", color=COLORS["con"], lw=1.5))

    # ─── Suptitle ──────────────────────────────────────────────────
    n_par = par.get("n", 0)
    n_seq = seq.get("n", 0)
    fig.suptitle(
        f"Aegis AI v5 — Sequential vs Parallel Debate"
        f"  (n={n_par} parallel, n={n_seq} sequential){title_suffix}",
        fontsize=14, fontweight="bold", y=1.00, color=COLORS["ink"]
    )

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.savefig(out_path.with_suffix(".pdf"), bbox_inches="tight")  # also save vector PDF
    print(f"Wrote: {out_path}")
    print(f"Wrote: {out_path.with_suffix('.pdf')}")

    # Print headline numbers
    print("\nHeadline (text version):")
    print(f"  N:                {n_par} parallel / {n_seq} sequential")
    print(f"  Diversity:        {par.get('avg_diversity'):.4f} → {seq.get('avg_diversity'):.4f}")
    print(f"  Pro drift:        {par.get('avg_pro_drift'):.4f} → {seq.get('avg_pro_drift'):.4f}")
    print(f"  Con drift:        {par.get('avg_con_drift'):.4f} → {seq.get('avg_con_drift'):.4f}")
    print(f"  Verdict align:    {par.get('verdict_alignment')}% → {seq.get('verdict_alignment')}%")
    print(f"  Trap resistance:  {par.get('trap_resistance')}% → {seq.get('trap_resistance')}%   (Δ +{delta:.0f} pp)")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--json", type=str, default=None, help="Path to results JSON (default: latest in eval/)")
    p.add_argument("--out",  type=str, default="docs/headline.png", help="Output PNG path")
    p.add_argument("--suffix", type=str, default="", help="Optional title suffix")
    args = p.parse_args()

    eval_dir = Path(__file__).resolve().parent
    json_path = Path(args.json) if args.json else latest_results_json(eval_dir)
    out_path = Path(args.out)

    make_figure(json_path, out_path, args.suffix)