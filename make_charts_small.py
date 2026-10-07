"""Figures for the small-class re-analysis. Static PNGs, light surface.
Palette: the same validated categorical slots as make_charts.py, so the two
figure sets read as one system.
"""
import sys
sys.path.insert(0, ".")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import small_class_analysis as S

SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "savefig.facecolor": SURFACE, "font.size": 10,
    "text.color": INK, "axes.labelcolor": INK2,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": AXIS, "font.family": "DejaVu Sans",
})


def _clean(ax, ygrid=True):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(AXIS)
    ax.spines["bottom"].set_color(AXIS)
    if ygrid:
        ax.set_axisbelow(True)
        ax.yaxis.grid(True, color=GRID, lw=0.8)
        ax.xaxis.grid(False)


x = S.load(".")

# =============================================================== figure 5
# Two panels, one shared x-axis (class size). Never two y-scales on one panel:
# the measures are unrelated, so they get their own panel each.
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8.6, 6.4), sharex=True,
                               gridspec_kw={"height_ratios": [1.15, 1]})

n = np.arange(1, 801)
rate = 100 * S.allowed_rate(n)
ax1.step(n, rate, where="post", color=S1, lw=2, zorder=3)
ax1.axhline(20, color=MUTED, lw=1.2, ls=(0, (4, 3)), zorder=2)
ax1.text(760, 13, "the nominal 20% cap", ha="right", va="center",
         fontsize=9, color=MUTED)

for xn, lab, off, ha in [(5, "n=5: 100%\nall five may get an A", (-11, -24), "right"),
                         (12, "n=12: 50%", (10, 4), "left"),
                         (25, "n=25: 36%", (10, 4), "left"),
                         (100, "n=100: 24%", (10, 6), "left")]:
    r = 100 * S.allowed_rate(xn)
    ax1.plot([xn], [r], "o", ms=8, color=S1, mec=SURFACE, mew=2, zorder=4)
    ax1.annotate(lab, (xn, r), textcoords="offset points", xytext=off,
                 fontsize=9, color=INK2, va="center", ha=ha)

ax1.set_ylim(0, 108)
ax1.set_ylabel("share of undergraduates who\nmay receive an A (%)")
ax1.set_title("A “20% cap” is a 20% cap only in the largest lectures",
              fontsize=12.5, color=INK, loc="left", pad=10)
_clean(ax1)

s26 = x[x.term == "S26"]
order = np.sort(s26["n"].values)
seats = s26.sort_values("n")["UGrad"].values
cdf = 100 * np.cumsum(seats) / seats.sum()
ax2.step(order, cdf, where="post", color=S2, lw=2, zorder=3)

for xn in (5, 12, 25, 50, 100):
    v = 100 * s26.loc[s26["n"] <= xn, "UGrad"].sum() / s26["UGrad"].sum()
    ax2.plot([xn], [v], "o", ms=8, color=S2, mec=SURFACE, mew=2, zorder=4)
    ax2.annotate(f"{v:.0f}%", (xn, v), textcoords="offset points",
                 xytext=(7, -11), fontsize=9, color=INK2)

ax2.set_xscale("log")
ax2.set_xticks([1, 3, 5, 10, 25, 50, 100, 250, 700])
ax2.get_xaxis().set_major_formatter(matplotlib.ticker.ScalarFormatter())
ax2.set_xlim(1, 800)
ax2.set_ylim(0, 104)
ax2.set_xlabel("class size (undergraduates enrolled, log scale)")
ax2.set_ylabel("cumulative share of\nundergraduate seats (%)")
ax2.set_title("but almost no undergraduate sits in a class that small  "
              "— Spring 2026", fontsize=11, color=INK2, loc="left", pad=8)
_clean(ax2)

fig.tight_layout()
fig.savefig("fig5_cap_curve.png", dpi=170)
plt.close(fig)
print("wrote fig5_cap_curve.png")


# =============================================================== figure 6
# The bunching test. Aligned springs only (pulled day 57-63 of term); Fall 2026
# was pulled on day 14 and its size distribution is not comparable.
AL_PRE, TREAT = ["S22", "S24", "S25"], "S26"
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5),
                               gridspec_kw={"width_ratios": [1.5, 1]})

sizes = np.arange(1, 15)
pre = np.mean([[100 * (x[x.term == t]["n"] == k).mean() for k in sizes]
               for t in AL_PRE], axis=0)
post = np.array([100 * (x[x.term == TREAT]["n"] == k).mean() for k in sizes])

w = 0.4
ax1.bar(sizes - w / 2, pre, w - 0.06, color=MUTED, label="Springs 2022-25 (mean)",
        zorder=3)
ax1.bar(sizes + w / 2, post, w - 0.06, color=S2, label="Spring 2026", zorder=3)
ax1.set_ylim(0, 13.0)
ax1.axvspan(0.4, 5.5, color=S1, alpha=0.07, zorder=1)
ax1.text(3.0, 12.7, "cap permits every undergraduate an A",
         ha="center", va="top", fontsize=9, color=S1)
ax1.set_xticks(sizes)
ax1.set_xlim(0.4, 14.6)
ax1.set_xlabel("class size (undergraduates enrolled \u2014 the cap base)")
ax1.set_ylabel("share of all classes (%)")
ax1.set_title("No pile-up at the threshold", fontsize=12.5, color=INK,
              loc="left", pad=10)
ax1.legend(frameon=False, fontsize=9, loc="upper left",
           bbox_to_anchor=(0.02, 0.90))
_clean(ax1)

rng = np.random.default_rng(0)
terms = ["S22", "S24", "S25", "S26"]
vals, los, his = [], [], []
for t in terms:
    s = x[x.term == t]
    v = 100 * (s["n"] == 5).mean()
    bs = [100 * (s["n"].iloc[rng.choice(len(s), len(s), replace=True)] == 5).mean()
          for _ in range(2000)]
    vals.append(v)
    los.append(v - np.percentile(bs, 2.5))
    his.append(np.percentile(bs, 97.5) - v)

cols = [MUTED, MUTED, MUTED, S2]
ax2.errorbar(range(4), vals, yerr=[los, his], fmt="none", ecolor=AXIS,
             elinewidth=1.4, capsize=4, zorder=2)
for i, (v, c) in enumerate(zip(vals, cols)):
    ax2.plot([i], [v], "o", ms=9, color=c, mec=SURFACE, mew=2, zorder=4)
ax2.set_xticks(range(4))
ax2.set_xticklabels(["2022", "2024", "2025", "2026"])
ax2.set_xlim(-0.5, 3.5)
ax2.set_ylim(2.6, 6.2)
ax2.set_ylabel("classes with exactly 5 undergraduates (%)")
ax2.set_title("Mass at the threshold is flat: 4.26, 4.25, 4.32, 4.28",
              fontsize=11, color=INK2, loc="left", pad=10)
ax2.annotate(f"{vals[-1]:.2f}%", (3, vals[-1]), textcoords="offset points",
             xytext=(10, -3), fontsize=9.5, color=S2)
_clean(ax2)

fig.tight_layout()
fig.savefig("fig6_bunching.png", dpi=170)
plt.close(fig)
print("wrote fig6_bunching.png")
