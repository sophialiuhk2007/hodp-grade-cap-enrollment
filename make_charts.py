"""Charts for the enrolment analysis. Static PNGs, light surface.
Palette: the validated default categorical slots (blue/orange/aqua) + diverging blue<->red.
"""
import sys
sys.path.insert(0, ".")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

SURFACE = "#fcfcfb"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
S1, S2, S3 = "#2a78d6", "#eb6834", "#1baf7a"     # categorical slots 1-3
POS, NEG = "#2a78d6", "#d03b3b"                   # diverging poles

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


import enrollment_lib as E
d = E.classify(E.load_all("."))
d["course"] = d.subject + " " + d.catalog.fillna("")
FALLS = ["F22", "F23", "F24", "F25", "F26"]
SPRINGS = ["S22", "S23", "S24", "S25", "S26"]
YEARS = [2022, 2023, 2024, 2025, 2026]


def share(flag_fn, terms):
    x = d[d.term.isin(terms)]
    m = np.asarray(flag_fn(x), dtype=bool)
    num = x[m].groupby("term", observed=True)["UGrad"].sum().reindex(terms).fillna(0)
    den = x.groupby("term", observed=True)["UGrad"].sum().reindex(terms)
    return (100 * num / den).values


# --------------------------------------------------------------- chart 1
fig, ax = plt.subplots(figsize=(8, 4.6))
cs_f = share(lambda x: x.dept == "Computer Science", FALLS)
cs_s = share(lambda x: x.dept == "Computer Science", SPRINGS)
ax.plot(YEARS, cs_f, color=S1, lw=2, marker="o", ms=8, zorder=3,
        markeredgecolor=SURFACE, markeredgewidth=2)
ax.plot(YEARS, cs_s, color=S2, lw=2, marker="o", ms=8, zorder=3,
        markeredgecolor=SURFACE, markeredgewidth=2)
ax.annotate("Fall", (YEARS[-1], cs_f[-1]), xytext=(34, 0), textcoords="offset points",
            color=S1, va="center", fontweight="bold")
ax.annotate("Spring", (YEARS[-1], cs_s[-1]), xytext=(34, 0), textcoords="offset points",
            color=S2, va="center", fontweight="bold")
for xx, yy, dy in [(YEARS[0], cs_f[0], -16), (YEARS[-1], cs_f[-1], -16),
                   (YEARS[0], cs_s[0], 11), (YEARS[-1], cs_s[-1], 11)]:
    ax.annotate(f"{yy:.1f}%", (xx, yy), xytext=(0, dy), textcoords="offset points",
                ha="center", color=INK2, fontsize=9)
ax.axvspan(2025.5, 2026.95, color="#f0efec", zorder=0)
ax.text(2025.56, max(cs_f.max(), cs_s.max()), "cap announced,\npartly enforced",
        color=MUTED, fontsize=8, va="top")
ax.set_xticks(YEARS)
ax.set_xlim(2021.8, 2026.95)
ax.set_ylabel("% of all Harvard College enrolments")
ax.set_title("Computer Science keeps shrinking — but the slide began in 2024-25",
             loc="left", fontweight="bold", pad=14)
_clean(ax)
fig.tight_layout()
fig.savefig("fig1_cs_share.png", dpi=170)
plt.close(fig)


# --------------------------------------------------------------- chart 2
def gradient(t0, t1):
    x = d[d.term.isin([t0, t1])]
    p = (x.groupby(["course", "term"], observed=True)["UGrad"].sum()
          .unstack("term").reindex(columns=[t0, t1]).fillna(0))
    p["base"] = x[x.term == t0].groupby("course", observed=True)["Total"].sum().reindex(p.index)
    p = p[(p[t0] > 0) & (p[t1] > 0) & p.base.notna()]
    p["b"] = pd.cut(p.base, [-1, 11, 24, 49, 99, 1e9],
                    labels=["1-11", "12-24", "25-49", "50-99", "100+"])
    g = p.groupby("b", observed=True)[[t0, t1]].sum()
    return (100 * (g[t1] / g[t0] - 1))


pairs = [("F22", "F23"), ("F23", "F24"), ("F24", "F25"), ("F25", "F26")]
G = pd.DataFrame({f"{a}->{b}": gradient(a, b) for a, b in pairs})
fig, ax = plt.subplots(figsize=(8, 4.6))
xs = np.arange(len(G.index))
for c in G.columns[:-1]:
    ax.plot(xs, G[c], color=AXIS, lw=2, marker="o", ms=7, zorder=2,
            markeredgecolor=SURFACE, markeredgewidth=2)
ax.plot(xs, G.iloc[:, -1], color=S1, lw=2.4, marker="o", ms=9, zorder=3,
        markeredgecolor=SURFACE, markeredgewidth=2)
ax.annotate("Fall 2025 → 2026", (xs[2], G.iloc[2, -1]), xytext=(12, -22),
            textcoords="offset points", color=S1, fontweight="bold")
ax.annotate("2022→23, 2023→24, 2024→25", (xs[1], G.iloc[1, :-1].max()),
            xytext=(10, 12), textcoords="offset points", color=MUTED)
ax.axhline(0, color=AXIS, lw=1)
ax.set_xticks(xs)
ax.set_xticklabels(G.index)
ax.set_xlabel("class size in the earlier year")
ax.set_ylabel("enrolment change, same courses (%)")
ax.set_title("Small classes grow faster every year — 2026 is not special",
             loc="left", fontweight="bold", pad=14)
_clean(ax)
fig.tight_layout()
fig.savefig("fig2_small_class_placebo.png", dpi=170)
plt.close(fig)


# --------------------------------------------------------------- chart 3
def dept_gap(t0, t1, minbase=200):
    x = d[d.term.isin([t0, t1])]
    p = (x.groupby(["course", "term"], observed=True)["UGrad"].sum()
          .unstack("term").reindex(columns=[t0, t1]).fillna(0))
    p = p.join(x[x.term == t0].drop_duplicates("course").set_index("course")[["dept"]])
    p = p[(p[t0] > 0) & (p[t1] > 0)].dropna(subset=["dept"])
    overall = 100 * (p[t1].sum() / p[t0].sum() - 1)
    g = p.groupby("dept", observed=True)[[t0, t1]].sum()
    g = g[g[t0] >= minbase]
    return (100 * (g[t1] / g[t0] - 1) - overall).sort_values()


gp = dept_gap("F25", "F26")
sel = pd.concat([gp.head(7), gp.tail(7)])
fig, ax = plt.subplots(figsize=(8.4, 6))
cols = [NEG if v < 0 else POS for v in sel.values]
ax.barh(range(len(sel)), sel.values, color=cols, height=0.68)
ax.set_yticks(range(len(sel)))
ax.set_yticklabels([s[:30] for s in sel.index], color=INK2, fontsize=9.5)
for i, v in enumerate(sel.values):
    ax.annotate(f"{v:+.0f}", (v, i), xytext=(6 if v > 0 else -6, 0),
                textcoords="offset points", va="center",
                ha="left" if v > 0 else "right", color=INK2, fontsize=9)
ax.axvline(0, color=AXIS, lw=1)
_lim = max(abs(sel.values)) * 1.22
ax.set_xlim(-_lim, _lim)
ax.set_xlabel("percentage points vs. the catalogue average")
ax.set_title("Fall 2026: which departments beat or missed the average\n"
             "same courses, both years, undergraduate enrolment",
             loc="left", fontweight="bold", pad=14)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.set_axisbelow(True)
ax.xaxis.grid(True, color=GRID, lw=0.8)
ax.tick_params(axis="y", length=0)
fig.tight_layout()
fig.savefig("fig3_dept_movers.png", dpi=170)
plt.close(fig)


# --------------------------------------------------------------- chart 4
courses = ["COMPSCI 50", "COMPSCI 61", "MATH 22A", "MATH 55A", "STAT 104", "PSY 1"]
p = (d[d.term.isin(FALLS)].groupby(["course", "term"], observed=True)["UGrad"].sum()
      .unstack("term").reindex(columns=FALLS).fillna(0))
fig, axes = plt.subplots(2, 3, figsize=(10, 5.4), sharex=True)
for ax, c in zip(axes.ravel(), courses):
    v = p.loc[c].values
    up = v[-1] >= v[-2]
    col = POS if up else NEG
    ax.plot(YEARS, v, color=col, lw=2.2, marker="o", ms=6,
            markeredgecolor=SURFACE, markeredgewidth=1.6)
    ax.annotate(f"{int(v[-1])}", (YEARS[-1], v[-1]), xytext=(0, 9),
                textcoords="offset points", ha="center", color=INK2, fontsize=9)
    ax.annotate(f"{int(v[0])}", (YEARS[0], v[0]), xytext=(0, 9),
                textcoords="offset points", ha="center", color=MUTED, fontsize=9)
    ax.set_title(c, loc="left", fontsize=10.5, fontweight="bold", color=INK)
    ax.set_ylim(0, max(v) * 1.35)
    ax.set_xticks(YEARS)
    ax.set_xticklabels([str(y)[2:] for y in YEARS])
    _clean(ax)
fig.suptitle("Gateway courses, Fall 2022-2026 (undergraduate enrolment)",
             x=0.012, ha="left", fontweight="bold", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig("fig4_gateway_courses.png", dpi=170)
plt.close(fig)

print("wrote fig1_cs_share.png fig2_small_class_placebo.png "
      "fig3_dept_movers.png fig4_gateway_courses.png")
