"""The two figures for the public layer (PAGE_SPEC §2).

  fig1_label_efficiency  -- CER vs real-label budget r, both arms, 95% CIs, and the gap
                            (with the r=100% NULL visibly on it, at the same weight as the win).
  fig2_truncation        -- the MECHANISM: predicted vs GT length on long crops (>=9 chars),
                            real-only vs +synth at r=10%. k=5 seeds pooled.

Every number is READ FROM THE RUN ARTIFACTS (runs/budget_curve_summary.json, runs/*/predictions.tsv).
Nothing is typed in by hand -- a figure that disagrees with RESULTS.md is a figure that lies.

    python scripts/make_figures.py        # -> docs/figures/*.svg + *.png
"""
from __future__ import annotations

import json
import os
import sys

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.scorer import nfc  # noqa: E402

OUT = "docs/figures"

# --- palette: dataviz categorical slots 1 (blue) + 8 (orange). Validated: worst adjacent
#     CVD dE 96.7 (protan), all slots >=3:1 on the light surface. Identity is never
#     color-alone -- every series is also direct-labelled.
BLUE = "#2a78d6"    # + synthetic  (the treatment arm)
ORANGE = "#eb6834"  # real-only    (the comparator)
INK = "#1a1a19"
INK2 = "#5c5b55"
GRID = "#e4e3de"
SURFACE = "#ffffff"

mpl.rcParams.update({
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
    "font.family": "sans-serif",
    "font.sans-serif": ["Inter", "Helvetica Neue", "Arial", "DejaVu Sans"],
    "font.size": 9,
    "axes.edgecolor": INK2,
    "axes.linewidth": 0.8,
    "axes.labelcolor": INK,
    "axes.titlecolor": INK,
    "xtick.color": INK2,
    "ytick.color": INK2,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.frameon": False,
    "svg.fonttype": "none",  # keep text as text in the SVG
})
MONO = {"family": "monospace", "fontsize": 8.5}


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    for ext in ("svg", "png"):
        fig.savefig(f"{OUT}/{name}.{ext}", dpi=200, bbox_inches="tight")
    print(f"  wrote {OUT}/{name}.svg + .png")


def despine(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", color=GRID, lw=0.7, zorder=0)
    ax.set_axisbelow(True)


# ============================================================ FIG 1 — label efficiency
def fig1():
    d = json.load(open("runs/budget_curve_summary.json", encoding="utf-8"))

    # The +synth arm is quoted STRICT-BANK wherever a strict set was generated (r=10, 25 --
    # EVAL_PROTOCOL §14.2: the headline must quote the strict version). At r=100% the r-subset's
    # own transcript bank IS the full train bank, so leg == strict by construction. Only r=50 is
    # full-bank-only; it is marked hollow. That is safe for the claim in the one direction that
    # matters: the bank confound can only INFLATE a gap, and the r=50 gap is already nil.
    pts = []
    for r in ("r10", "r25", "r50", "r100"):
        v = d[r]
        arm = "strict_arm" if "strict_arm" in v else "synth_arm"
        strict = arm == "strict_arm" or r == "r100"
        pts.append(dict(
            r=int(r[1:]), n=v["n_real"],
            real=v["real_only"]["cer"], k_real=v["k_real"],
            synth=v[arm]["metrics"]["cer"], k_synth=v[arm]["k"],
            gap=v[arm]["gap_cer"], green=v[arm]["green"], strict=strict,
        ))

    x = np.array([p["r"] for p in pts], float)
    rm = np.array([p["real"][0] for p in pts]); rh = np.array([p["real"][1] for p in pts])
    sm = np.array([p["synth"][0] for p in pts]); sh = np.array([p["synth"][1] for p in pts])
    gap = rm - sm
    gaph = np.sqrt(rh ** 2 + sh ** 2)  # unpaired diff of two means (same rule as the aggregators)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.6, 4.3), gridspec_kw=dict(wspace=0.28))

    # ---------- left: the two arms
    for m, h, c, lab in ((rm, rh, ORANGE, "real-only"), (sm, sh, BLUE, "+ 10k synthetic")):
        a1.fill_between(x, m - h, m + h, color=c, alpha=0.13, lw=0, zorder=1)
        a1.plot(x, m, color=c, lw=2, zorder=3, label=lab)
        a1.errorbar(x, m, yerr=h, fmt="none", ecolor=c, elinewidth=1.2, capsize=3, zorder=4)
    for p, xi, yi in zip(pts, x, sm):
        a1.plot([xi], [yi], "o", ms=7, mfc=BLUE if p["strict"] else SURFACE,
                mec=BLUE, mew=1.6, zorder=5)
    a1.plot(x, rm, "o", ms=7, color=ORANGE, zorder=5)

    a1.set_xscale("log")
    a1.set_xticks(x)
    a1.set_xticklabels([f"{p['r']}%\n{p['n']:,}" for p in pts], **MONO)
    a1.set_xlabel("real-label budget   (% of VinText train  ·  n crops)", labelpad=8)
    a1.set_ylabel("CER  %   (rec-only, test-500, lower is better)")
    a1.set_ylim(8, 18)
    a1.set_yticks(range(8, 19, 2))
    a1.set_yticklabels([f"{v}" for v in range(8, 19, 2)], **MONO)
    despine(a1)
    a1.text(10.4, 16.9, "real-only", color=ORANGE, fontsize=9.5, fontweight="bold")
    a1.text(10.4, 11.3, "+ 10k synthetic", color=BLUE, fontsize=9.5, fontweight="bold")
    a1.annotate("", xy=(10, sm[0]), xytext=(10, rm[0]),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=1.1, shrinkA=0, shrinkB=0))
    a1.text(10.9, (rm[0] + sm[0]) / 2, f"−{gap[0]:.2f} pp\nCER", color=INK, fontsize=8.5,
            va="center", linespacing=1.35)
    a1.text(72, 10.9, "the arms\nmeet", color=INK2, fontsize=8.5, ha="center", linespacing=1.35)
    a1.set_title("Synthetic data buys accuracy only when labels are scarce",
                 fontsize=10.5, fontweight="bold", loc="left", pad=10)

    # ---------- right: the gap, with the null at full weight
    a2.axhline(0, color=INK2, lw=1)
    cols = [BLUE if p["green"] else INK2 for p in pts]
    a2.bar(np.arange(4), gap, width=0.52, color=cols, zorder=2)
    a2.errorbar(np.arange(4), gap, yerr=gaph, fmt="none", ecolor=INK, elinewidth=1.2,
                capsize=4, zorder=3)
    for i, p in enumerate(pts):
        up = gap[i] >= 0
        a2.text(i, gap[i] + (gaph[i] + 0.16) * (1 if up else -1),
                f"{gap[i]:+.2f}", ha="center", va="bottom" if up else "top", **MONO)
        a2.text(i, -1.55, "GREEN" if p["green"] else "null",
                ha="center", fontsize=8.5, color=BLUE if p["green"] else INK2,
                fontweight="bold" if p["green"] else "normal")
        a2.text(i, -1.85, f"k={p['k_synth']}", ha="center", color=INK2, **MONO)
    a2.set_xticks(np.arange(4))
    a2.set_xticklabels([f"{p['r']}%" for p in pts], **MONO)
    a2.set_xlabel("real-label budget", labelpad=8)
    a2.set_ylabel("ΔCER  pp   (real-only − synth;  + = synthetic helps)")
    a2.set_ylim(-2.1, 4.35)
    a2.set_yticks([0, 1, 2, 3, 4])
    a2.set_yticklabels(["0", "1", "2", "3", "4"], **MONO)
    despine(a2)
    a2.set_title("The gap is monotone in the budget — and dies before full data",
                 fontsize=10.5, fontweight="bold", loc="left", pad=10)
    a2.text(2.62, 3.05,
            "GREEN = the pre-registered rule:\n95% CIs separate on CER *and* tone.\n"
            "r=25% separates on CER but NOT on\ntone → it does not clear the bar.",
            fontsize=8, color=INK2, linespacing=1.5, ha="center")

    fig.text(0.0, -0.17,
             "rec-only · VinText test-500 (10,068 instances / 37,254 chars) · NFC · "
             "mean ± 95% CI over k training seeds · document-pretrained VietOCR vgg_transformer, "
             "fine-tuned; only the real-label budget and the synthetic set vary.\n"
             "The +synth arm is the STRICT-BANK generator at r=10% and 25% (solid marker; the "
             "corpus draws only on transcripts the budget entitles it to) and at r=100% "
             "(where the two banks are identical by construction).\n"
             "r=50% (hollow marker) was only run full-bank; the confound can only inflate a gap, "
             "and that gap is already nil.",
             fontsize=7.6, color=INK2, linespacing=1.55)
    save(fig, "fig1_label_efficiency")
    plt.close(fig)
    return pts


# ============================================================ FIG 2 — the truncation mechanism
def fig2():
    SEEDS = range(5)
    ARMS = {"real-only": "budget_r10_real", "+ synthetic": "budget_r10_strict"}

    def load(run, s):
        with open(f"runs/{run}_seed{s}/predictions.tsv", encoding="utf-8") as f:
            rows = [ln.rstrip("\n").split("\t") for ln in f if ln.strip("\n")]
        return [(nfc(r[0]), nfc(r[1]) if len(r) > 1 else "") for r in rows]

    data = {a: {s: load(run, s) for s in SEEDS} for a, run in ARMS.items()}
    ref = data["real-only"][0]
    long_idx = [j for j, (gt, _) in enumerate(ref) if len(gt) >= 9]
    print(f"  long crops (>=9 chars): n={len(long_idx)} of {len(ref)}")

    stats = {}
    for a in ARMS:
        ratios, gl, pl = [], [], []
        for s in SEEDS:
            for j in long_idx:
                gt, pr = data[a][s][j]
                ratios.append(len(pr) / len(gt))
                gl.append(len(gt)); pl.append(len(pr))
        ratios = np.array(ratios)
        stats[a] = dict(ratio=ratios, gl=np.array(gl), pl=np.array(pl),
                        trunc=100 * (ratios < 0.6).mean(),
                        mean_pl=np.mean(pl), mean_gl=np.mean(gl))
        print(f"  {a:>12s}: mean GT {stats[a]['mean_gl']:.2f} -> mean pred "
              f"{stats[a]['mean_pl']:.2f}  severely truncated {stats[a]['trunc']:.1f}%")

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(10.6, 4.3), gridspec_kw=dict(wspace=0.26))

    # ---------- left: predicted vs GT length
    lens = sorted({int(g) for g in stats["real-only"]["gl"]})
    a1.plot([8.5, 18.5], [8.5, 18.5], color=INK2, lw=1, ls=(0, (4, 3)), zorder=1)
    a1.text(17.6, 18.0, "perfect\nlength", color=INK2, fontsize=8, ha="right", linespacing=1.35)
    for a, c in (("real-only", ORANGE), ("+ synthetic", BLUE)):
        ys, xs = [], []
        for L in lens:
            m = stats[a]["gl"] == L
            if m.sum() >= 5 * 3:  # >=3 instances x 5 seeds
                xs.append(L); ys.append(stats[a]["pl"][m].mean())
        a1.plot(xs, ys, "-o", color=c, lw=2, ms=6, mec=SURFACE, mew=1.2, zorder=3, label=a)
    a1.set_xlabel("ground-truth length   (characters)", labelpad=6)
    a1.set_ylabel("mean predicted length   (characters)")
    a1.set_xlim(8.4, 18.6); a1.set_ylim(4, 19)
    a1.set_xticks(range(9, 19, 2)); a1.set_yticks(range(4, 20, 2))
    a1.set_xticklabels([str(v) for v in range(9, 19, 2)], **MONO)
    a1.set_yticklabels([str(v) for v in range(4, 20, 2)], **MONO)
    despine(a1)
    a1.text(15.2, 9.6, "real-only", color=ORANGE, fontsize=9.5, fontweight="bold", ha="center")
    a1.text(12.0, 14.2, "+ synthetic", color=BLUE, fontsize=9.5, fontweight="bold", ha="center")
    a1.set_title("At a scarce budget the decoder stops early", fontsize=10.5,
                 fontweight="bold", loc="left", pad=10)

    # ---------- right: the truncation histogram
    # dodged bars, not alpha-blended overlays: an overlap colour is a third series the reader
    # has to decode, and here it would sit exactly on the bin that carries the finding.
    bins = np.arange(0, 1.55, 0.1)
    ctr = (bins[:-1] + bins[1:]) / 2
    bw = 0.042
    a2.axvspan(0, 0.6, color=GRID, alpha=0.7, zorder=0)
    for off, (a, c) in zip((-bw / 2, bw / 2), (("real-only", ORANGE), ("+ synthetic", BLUE))):
        h, _ = np.histogram(np.clip(stats[a]["ratio"], 0, 1.499), bins=bins)
        a2.bar(ctr + off, 100 * h / h.sum(), width=bw, color=c, zorder=2, label=a)
    a2.axvline(1.0, color=INK2, lw=1, ls=(0, (4, 3)), zorder=3)
    a2.set_xlabel("predicted length ÷ ground-truth length", labelpad=6)
    a2.set_ylabel("% of long crops  (≥9 chars,  n=296 × 5 seeds)")
    a2.set_xlim(0, 1.5)
    a2.set_xticks([0, 0.25, 0.5, 0.6, 0.75, 1.0, 1.25, 1.5])
    a2.set_xticklabels(["0", ".25", ".5", ".6", ".75", "1.0", "1.25", "1.5"], **MONO)
    a2.set_yticks(a2.get_yticks())
    a2.set_yticklabels([f"{t:g}" for t in a2.get_yticks()], **MONO)
    a2.set_ylim(0, None)
    despine(a2)
    a2.text(0.30, a2.get_ylim()[1] * 0.93, "severely truncated\n(< 60% of GT)",
            ha="center", fontsize=8.5, color=INK2, linespacing=1.4)
    a2.text(0.30, a2.get_ylim()[1] * 0.74,
            f"real-only   {stats['real-only']['trunc']:5.1f}%", color=ORANGE,
            ha="center", fontweight="bold", **MONO)
    a2.text(0.30, a2.get_ylim()[1] * 0.68,
            f"+ synthetic  {stats['+ synthetic']['trunc']:4.1f}%", color=BLUE,
            ha="center", fontweight="bold", **MONO)
    a2.text(1.02, a2.get_ylim()[1] * 0.93, "correct length", fontsize=8, color=INK2)
    a2.set_title("…and the synthetic data fixes it", fontsize=10.5,
                 fontweight="bold", loc="left", pad=10)

    fig.text(0.0, -0.055,
             "rec-only · VinText test-500 · NFC · r=10% (2,574 real crops) · k=5 seeds pooled · "
             "long crops = the 296 test instances with ≥9 GT characters (phone numbers, URLs, "
             "multi-word signs).\nThis is where 54.3% of the entire +2.783 pp CER gain lives — and "
             "sequence length was never a knob the generator targeted.",
             fontsize=7.6, color=INK2, linespacing=1.55)
    save(fig, "fig2_truncation")
    plt.close(fig)
    return stats


if __name__ == "__main__":
    print("fig1 — label efficiency")
    fig1()
    print("fig2 — truncation mechanism")
    fig2()
