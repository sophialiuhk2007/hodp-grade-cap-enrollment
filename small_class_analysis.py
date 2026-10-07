"""
Small-class re-analysis for the 20% + 4 A-cap study.

The first pass (notebook §5.2) tested the small-class hypothesis one way only:
matched-course *growth* by size bucket. That test had two defects.

  1. It measured growth, not exposure. "Do small courses grow faster?" is a
     different question from "what share of students sit in a small class?".
     Only the second one says whether the cap bites.
  2. Its size variable was the course total, summed over sections. MATH 21A
     has 17 sections of 17-39 students; the old code called it a 399-person
     course and put it in the "100+" bucket. No student sits in a room of 399.

This module works at the *class* level (one registrar class number = one room,
one grade sheet) and adds the test the rule's own arithmetic suggests: under
allowed(n) = floor(0.20n + 4), a class of 5 or fewer is completely unconstrained,
because 0.20(5) + 4 = 5. The cliff from n=5 to n=6 is the sharpest in the rule.
"""
import re
import numpy as np
import pandas as pd

import enrollment_lib as E

# ---------------------------------------------------------------------------
# The rule, as adopted
# ---------------------------------------------------------------------------
# FAS faculty ballot, 458-201, announced 20 May 2026; in force from Fall 2027.
# Motion item 3: instructors "may award A grades to at most 20 percent of the
# final undergraduate letter-graded course enrolment plus 4, with other letter
# grades, including A-, not subject to a limit."
#
# Two features of that sentence drive everything below.
#   * The base is UNDERGRADUATE enrolment. Graduate students in the room are
#     neither counted nor capped, so `n` is the UGrad column, not Total.
#   * It caps flat A only. A- is unlimited, so the benchmark is Harvard's
#     flat-A rate (60.2% in 2024-25), never the ~85% A-range figure.
#
# The March 2026 revision put pass/fail students back into the base, which our
# UGrad column already includes.
CAP_PCT = 0.20
CAP_FLAT = 4

# Harvard's own published grade statistics, for benchmarking.
# FAS Office of Institutional Research, via Dean Claybaugh's October 2025 report.
FLAT_A_RATE = {"2005": 0.240, "2015": 0.403, "2022-23": 0.585,
               "2024-25": 0.602, "Fall 2025": 0.534}

# Flat-A share by class size, 2024-25, from the Crimson's analysis of the OUE
# grading dashboard (22,000+ course rows, 2014-15 to 2024-25), 28 May 2026.
# The only class-size breakdown of Harvard grades that exists publicly.
A_RATE_BY_SIZE = [(12, 0.79), (30, 0.71), (50, 0.68), (150, 0.64), (10**9, 0.52)]


def observed_A_rate(n):
    """Flat-A rate actually awarded in a class of n, per the Crimson bands."""
    n = np.asarray(n, dtype=float)
    out = np.full(n.shape, A_RATE_BY_SIZE[-1][1], dtype=float)
    for hi, r in reversed(A_RATE_BY_SIZE[:-1]):
        out = np.where(n <= hi, r, out)
    return out


def allowed_A(n, pct=CAP_PCT, flat=CAP_FLAT, rounding="floor"):
    """Number of A grades the rule permits in a class of n students.

    Capped at n: the rule cannot permit more A's than there are students, which
    is exactly why it stops constraining anything at n <= 5.
    """
    n = np.asarray(n, dtype=float)
    raw = pct * n + flat
    val = np.floor(raw) if rounding == "floor" else np.round(raw)
    return np.minimum(val, n)


def allowed_rate(n, **kw):
    """Share of a class of n that may receive an A. 100% for n <= 5."""
    n = np.asarray(n, dtype=float)
    return np.where(n > 0, allowed_A(n, **kw) / np.maximum(n, 1), np.nan)


def binding_n(pct=CAP_PCT, flat=CAP_FLAT):
    """Largest class size at which the cap permits everyone an A."""
    n = 1
    while allowed_A(n, pct, flat) >= n:
        n += 1
    return n - 1


# ---------------------------------------------------------------------------
# The universe: rooms undergraduates actually sit in
# ---------------------------------------------------------------------------
# Rows at n = 1-6 are dominated by graduate supervision -- "Doctoral
# Dissertation", "Reading and Research", "Graduate Research". In Fall 2026,
# 1,157 of the 1,482 rows with Total <= 6 enrol zero undergraduates. Counting
# those as "small classes" would measure the size of the PhD programme, not
# undergraduate course choice.
#
# Supervision arrangements are also not classes in the sense the cap cares
# about: a senior writing a thesis with an adviser is not a room where a
# grade distribution exists. They are excluded, and `SUPERVISION_RE` is kept
# deliberately tight so that real small seminars survive it.
SUPERVISION_RE = re.compile(
    r"(reading\s*(and|&)\s*research"
    r"|supervised\s+read"
    r"|^research$|graduate\s+research|research-related"
    r"|dissertation"
    r"|direction\s+of|directed\s+(writing|study|research)"
    r"|independent\s+(study|research|work)"
    r"|experiential\s+study"
    r"|general\s+examination"
    r"|thesis\s+research)",
    re.I,
)


def classroom(d, min_ugrad=1, base="UGrad"):
    """Restrict to graded classrooms containing undergraduates.

    `n` is the cap base: undergraduate enrolment, because the rule counts only
    undergraduates. `Total` is kept as `n_room` for the "how big does the class
    feel" questions, which is a different quantity in courses with heavy
    graduate enrolment.
    """
    x = d[d["UGrad"] >= min_ugrad].copy()
    x = x[x["Total"] > 0]

    name = x["course_name"].fillna("")
    x["is_supervision"] = (
        name.str.contains(SUPERVISION_RE, regex=True)
        | x["catalog_num"].eq(91)                 # 91r, the supervised-reading number
    )
    x = x[~x["is_supervision"]].copy()

    x["n"] = x[base]
    x["n_room"] = x["Total"]
    x["allowed"] = allowed_A(x["n"])
    x["allowed_rate"] = allowed_rate(x["n"])
    x["uncapped"] = x["n"] <= binding_n()
    return x


# ---------------------------------------------------------------------------
# 1. Exposure: what share of undergraduates sit in a small class
# ---------------------------------------------------------------------------
def exposure(x, terms, thresholds=(6, 12, 20, 25, 50)):
    """Share of classes vs share of undergraduate SEATS below each size.

    The two columns answer different questions and usually disagree sharply:
    most classes are small, most students are not in them.
    """
    rows = {}
    for t in terms:
        s = x[x["term"] == t]
        seats = s["UGrad"].sum()
        rec = {"classes": len(s), "ugrad_seats": int(seats),
               "median_class_size": s["n"].median(),
               "seat_wtd_class_size": np.average(s["n"], weights=s["UGrad"])}
        for th in thresholds:
            m = s["n"] < th
            rec[f"% classes <{th}"] = 100 * m.mean()
            rec[f"% seats <{th}"] = 100 * s.loc[m, "UGrad"].sum() / seats
        rows[t] = rec
    return pd.DataFrame(rows).T


# ---------------------------------------------------------------------------
# 2 & 3. The size distribution and bunching at the non-binding threshold
# ---------------------------------------------------------------------------
def size_hist(x, terms, top=16, weight=None):
    """Counts of classes (or undergraduate seats) at each exact class size."""
    out = {}
    for t in terms:
        s = x[x["term"] == t]
        if weight is None:
            c = s["n"].value_counts()
            denom = len(s)
        else:
            c = s.groupby("n")[weight].sum()
            denom = s[weight].sum()
        out[t] = (100 * c / denom).reindex(range(1, top + 1)).fillna(0)
    return pd.DataFrame(out)


def bunching(x, terms, lo=1, hi=12):
    """Share of classes at each size 1..hi, per term, plus the n<=5 mass.

    If instructors were shrinking classes to escape the cap, the mass at
    n <= 5 should rise in the terms where the rule was live, and the step
    between n=5 and n=6 should deepen.
    """
    tbl = size_hist(x, terms, top=hi)
    add = {}
    for t in terms:
        s = x[x["term"] == t]
        add[t] = {
            "% classes n<=5": 100 * (s["n"] <= 5).mean(),
            "% classes n in 6-10": 100 * s["n"].between(6, 10).mean(),
            "ratio n=5 / n=6": (s["n"].eq(5).sum() / max(s["n"].eq(6).sum(), 1)),
            "% ugrad seats n<=5": 100 * s.loc[s["n"] <= 5, "UGrad"].sum() / s["UGrad"].sum(),
        }
    return tbl, pd.DataFrame(add)


# ---------------------------------------------------------------------------
# 4. The cap that the size distribution actually implies
# ---------------------------------------------------------------------------
def effective_cap(x, terms, weight="UGrad"):
    """The real ceiling on A's once the +4 meets the actual class-size mix.

    `allowed %` is the College-wide ceiling: total A's permitted across all
    classes, over total seats. It is the number that "a 20% cap" should be
    compared against.
    """
    rows = {}
    for t in terms:
        s = x[x["term"] == t]
        w = s[weight]
        # A's permitted, pro-rated to the undergraduate share of each class so
        # that the ceiling is expressed per undergraduate seat.
        permitted = (s["allowed_rate"] * w).sum()
        rows[t] = {
            "classes": len(s),
            "ugrad_seats": int(w.sum()),
            "allowed %": 100 * permitted / w.sum(),
            "class-avg allowed %": 100 * s["allowed_rate"].mean(),
            "% seats uncapped (n<=5)": 100 * w[s["uncapped"]].sum() / w.sum(),
            "% seats allowed >=50%": 100 * w[s["allowed_rate"] >= 0.50].sum() / w.sum(),
            "% seats allowed >=40%": 100 * w[s["allowed_rate"] >= 0.40].sum() / w.sum(),
            "% seats allowed >=30%": 100 * w[s["allowed_rate"] >= 0.30].sum() / w.sum(),
            "% seats allowed <25%": 100 * w[s["allowed_rate"] < 0.25].sum() / w.sum(),
        }
    return pd.DataFrame(rows).T


def cap_curve(sizes=(1, 3, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 75, 100, 200, 400, 700)):
    """The rule as a lookup table: what the +4 is worth at each class size."""
    s = np.array(sizes, dtype=float)
    return pd.DataFrame({
        "class size": s.astype(int),
        "A's allowed": allowed_A(s).astype(int),
        "allowed % of class": (100 * allowed_rate(s)).round(1),
    }).set_index("class size")


def bite(x, terms, actual_A_rate):
    """How much of the current A pile the cap removes, by class size.

    Assumes every class currently awards A's at the College-wide rate. That is
    a deliberate simplification -- we have no per-class grade data -- so this
    is a scenario, not a measurement. Its purpose is to show WHERE the cap
    lands, which does not depend much on the assumed rate.
    """
    rows = {}
    for t in terms:
        s = x[x["term"] == t].copy()
        s["cur_A"] = actual_A_rate * s["UGrad"]
        s["cap_A"] = s["allowed_rate"] * s["UGrad"]
        s["lost"] = np.maximum(s["cur_A"] - s["cap_A"], 0)
        band = pd.cut(s["n"], [0, 5, 11, 24, 49, 99, 10**9],
                      labels=["1-5", "6-11", "12-24", "25-49", "50-99", "100+"])
        g = s.groupby(band, observed=True).agg(
            seats=("UGrad", "sum"), cur_A=("cur_A", "sum"), lost=("lost", "sum"))
        g["% of seats"] = 100 * g.seats / g.seats.sum()
        g["A's lost %"] = 100 * g.lost / g.cur_A
        g["share of all lost A's %"] = 100 * g.lost / s["lost"].sum()
        rows[t] = g
    return rows


def projected_bite(x, term, calibrate_to=None):
    """What the cap does, using the A-rates Harvard classes actually award.

    Instead of assuming one A-rate everywhere, each class is assigned the
    flat-A rate the Crimson measured for its size band. That matters because
    the observed rates run the *opposite* way to the cap: small classes award
    the most A's (79% at n<=12) and face the loosest ceiling.
    """
    s = x[x["term"] == term].copy()
    s["cur_rate"] = observed_A_rate(s["n"])

    # The Crimson's band rates are course-level averages. Weighting them by
    # enrolment implies a College flat-A rate of ~67%, against the 60.2% the
    # FAS Office of Institutional Research reports for 2024-25 -- the gap is
    # the small-class rates being applied to too many seats. Scaling all bands
    # by a constant reconciles the level while preserving the gradient, which
    # is the part that matters here.
    if calibrate_to is not None:
        implied = (s["cur_rate"] * s["n"]).sum() / s["n"].sum()
        s["cur_rate"] = np.minimum(s["cur_rate"] * calibrate_to / implied, 1.0)

    s["new_rate"] = np.minimum(s["cur_rate"], s["allowed_rate"])
    s["cur_A"] = s["cur_rate"] * s["n"]
    s["new_A"] = s["new_rate"] * s["n"]

    band = pd.cut(s["n"], [0, 5, 12, 30, 50, 150, 10**9],
                  labels=["1-5", "6-12", "13-30", "31-50", "51-150", "150+"])
    g = s.groupby(band, observed=True).agg(
        classes=("n", "size"), seats=("n", "sum"),
        cur_A=("cur_A", "sum"), new_A=("new_A", "sum"))
    g["% of seats"] = 100 * g.seats / g.seats.sum()
    g["A rate now %"] = 100 * g.cur_A / g.seats
    g["A rate capped %"] = 100 * g.new_A / g.seats
    g["A's removed"] = (g.cur_A - g.new_A).round(0)
    g["share of all cuts %"] = 100 * (g.cur_A - g.new_A) / (s.cur_A.sum() - s.new_A.sum())

    totals = {"college A rate now %": 100 * s.cur_A.sum() / s.n.sum(),
              "college A rate capped %": 100 * s.new_A.sum() / s.n.sum(),
              "A's removed %": 100 * (1 - s.new_A.sum() / s.cur_A.sum()),
              "% of classes already compliant":
                  100 * (s.cur_rate <= s.allowed_rate).mean(),
              "% of seats already compliant":
                  100 * s.loc[s.cur_rate <= s.allowed_rate, "n"].sum() / s.n.sum()}
    return g.round(1), pd.Series(totals).round(1)


def load(root="."):
    return classroom(E.classify(E.load_all(root)))
