"""
Pre-med course enrollment: Fall 2026 vs prior falls, Spring 2026 vs prior springs.

Course basket is taken from FAS Career Services' premedical requirements page:
careerservices.fas.harvard.edu/resources/premedical-information-for-harvard-
students-timelines-courses-and-resources/

The page's list mixes two very different kinds of course, so they are kept apart:

  CORE  courses that exist mainly to serve the pre-med / life-science
        requirement (intro chem, orgo, the PhysSci physics sequence, intro bio,
        biochem). Pre-meds are a large share of the seats, so a change here is
        informative about pre-med behaviour.

  SHARED  requirements the whole College takes anyway (Expos, Math Ma/1a,
        Stat, Psych 1, Sociology). Pre-meds are a small minority of these
        seats, so they are reported separately and NOT used for the headline.

Matching is on exact (subject, catalog) strings so that e.g. CHEM 17 is not
confused with CHEM 171, and PHYSICS 15C (not a pre-med option) is excluded.
"""
import numpy as np
import pandas as pd
import enrollment_lib as el

FALLS   = ["F22", "F23", "F24", "F25", "F26"]
SPRINGS = ["S22", "S23", "S24", "S25", "S26"]

# --- basket -----------------------------------------------------------------
# (subject, catalog) exactly as the registrar reports it, grouped by the
# requirement area the Career Services page files it under.
CORE = {
    "Intro chemistry": [
        ("LPS", "A"), ("LIFESCI", "1A"), ("LIFESCI", "50A"),
        ("PHYSCI", "11"), ("PHYSCI", "10"), ("CHEM", "103"),
        ("CHEM", "40"), ("CHEM", "60"), ("CHEM", "160"), ("ENG-SCI", "181"),
    ],
    "Organic chemistry": [
        ("CHEM", "17"), ("CHEM", "27"), ("CHEM", "20"), ("CHEM", "30"),
    ],
    "Biology": [
        ("LIFESCI", "1B"), ("LIFESCI", "2"), ("LIFESCI", "50B"),
        ("MCB", "60"), ("MCB", "68"), ("OEB", "10"), ("OEB", "58"),
        ("SCRB", "50"), ("HEB", "10"), ("HEB", "50"), ("HEB", "55"),
        ("ENG-SCI", "53"),
    ],
    "Biochemistry": [
        ("MCB", "63"), ("MCB", "65"), ("MCB", "130"),
        ("CHEM", "170"), ("CHEM", "171"), ("BCMP", "234"),
    ],
    "Physics": [
        ("PHYSCI", "2"), ("PHYSCI", "3"), ("PHYSCI", "12A"), ("PHYSCI", "12B"),
        ("APPHY", "50A"), ("APPHY", "50B"),
        ("PHYSICS", "15A"), ("PHYSICS", "15B"), ("PHYSICS", "16"),
        ("PHYSICS", "19"), ("PHYSICS", "153"),
    ],
}

SHARED = {
    "Math": [
        ("MATH", "MA"), ("MATH", "MB"), ("MATH", "LS"),
        ("MATH", "1A"), ("MATH", "1B"), ("MATH", "18A"), ("MATH", "18B"),
        ("MATH", "19A"), ("MATH", "21A"), ("MATH", "21B"),
        ("APMTH", "21A"), ("APMTH", "21B"), ("APMTH", "22A"), ("APMTH", "22B"),
    ],
    "Statistics": [
        ("STAT", "100"), ("STAT", "102"), ("STAT", "104"), ("STAT", "110"),
        ("STAT", "111"), ("STAT", "139"), ("MATH", "19B"), ("PSY", "1900"),
        ("GOV", "50"), ("SOCIOL", "1156"), ("APMTH", "101"), ("ENG-SCI", "150"),
    ],
    "Writing (Expos)":  [("EXPOS", "10"), ("EXPOS", "20")],
    "Psych / sociology": [("PSY", "1"), ("SOCIOL", "1000")],
}

BANDS = {**{k: ("CORE", v) for k, v in CORE.items()},
         **{k: ("SHARED", v) for k, v in SHARED.items()}}


def tag(d):
    """Label each section with its requirement area and tier."""
    lookup = {}
    for band, (tier, pairs) in BANDS.items():
        for p in pairs:
            lookup.setdefault(p, (tier, band))
    key = list(zip(d["subject"], d["catalog"].fillna("").str.upper()))
    d = d.copy()
    d["tier"] = [lookup.get(k, (None, None))[0] for k in key]
    d["band"] = [lookup.get(k, (None, None))[1] for k in key]
    d["course"] = d["subject"] + " " + d["catalog"].fillna("")
    return d


def basket(d, terms, tier, value="UGrad"):
    """Enrolment in the basket, and the College total, for each term."""
    rows = []
    for t in terms:
        x = d[d.term == t]
        rows.append({
            "term": t,
            "label": el.TERM_FILES[t][1],
            "run_date": x["run_date"].iloc[0].date(),
            "basket": int(x.loc[x.tier == tier, value].sum()),
            "college": int(x[value].sum()),
            "n_courses": x.loc[x.tier == tier, "course"].nunique(),
        })
    out = pd.DataFrame(rows).set_index("term")
    out["share_pct"] = 100 * out["basket"] / out["college"]
    out["basket_yoy_pct"] = 100 * out["basket"].pct_change()
    out["college_yoy_pct"] = 100 * out["college"].pct_change()
    # difference-in-differences: basket growth net of College-wide growth
    out["excess_pp"] = out["basket_yoy_pct"] - out["college_yoy_pct"]
    return out


def per_course(d, terms, tier, value="UGrad"):
    x = d[(d.tier == tier) & (d.term.isin(terms))]
    tbl = (x.groupby(["band", "course", "term"])[value].sum()
             .unstack("term").reindex(columns=terms))
    return tbl


def main():
    d = tag(el.load_all())
    fmt = lambda f: f.round(2).to_string()

    for season, terms in [("FALL", FALLS), ("SPRING", SPRINGS)]:
        prev, cur = terms[-2], terms[-1]
        print("=" * 78)
        print(f"{season}: {el.TERM_FILES[cur][1]} vs {el.TERM_FILES[prev][1]}")
        print("=" * 78)
        for tier in ["CORE", "SHARED"]:
            b = basket(d, terms, tier)
            print(f"\n--- {tier} pre-med basket (undergraduate enrolments) ---")
            print(fmt(b[["label", "run_date", "n_courses", "basket", "college",
                         "share_pct", "basket_yoy_pct", "college_yoy_pct", "excess_pp"]]))
            chg = b.loc[cur, "basket"] - b.loc[prev, "basket"]
            print(f"\n  {prev}->{cur}: {chg:+d} seats "
                  f"({b.loc[cur,'basket_yoy_pct']:+.1f}%), "
                  f"share {b.loc[prev,'share_pct']:.2f}% -> {b.loc[cur,'share_pct']:.2f}% "
                  f"({b.loc[cur,'share_pct']-b.loc[prev,'share_pct']:+.2f} pp)")
            hist = b["basket_yoy_pct"].dropna()[:-1]
            print(f"  prior {season.lower()}-to-{season.lower()} changes: "
                  f"{', '.join(f'{v:+.1f}%' for v in hist)}  "
                  f"(mean {hist.mean():+.1f}%, sd {hist.std(ddof=1):.1f})")

        print(f"\n--- CORE, by requirement area ({prev} -> {cur}) ---")
        pc = per_course(d, terms, "CORE")
        band = pc.groupby("band").sum()
        band["chg"] = band[cur] - band[prev]
        band["pct"] = 100 * band["chg"] / band[prev].replace(0, np.nan)
        print(fmt(band))

        print(f"\n--- CORE, course level ({prev} -> {cur}); '.' = not offered ---")
        pcs = pc[[prev, cur]].copy()
        pcs["chg"] = pcs[cur].fillna(0) - pcs[prev].fillna(0)
        pcs = pcs.sort_values("chg")
        print(pcs.fillna(".").to_string())

        print(f"\n--- SHARED, by requirement area ({prev} -> {cur}) ---")
        ps = per_course(d, terms, "SHARED").groupby("band").sum()
        ps["chg"] = ps[cur] - ps[prev]
        ps["pct"] = 100 * ps["chg"] / ps[prev].replace(0, np.nan)
        print(fmt(ps))
        print()


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# Composition control
# ---------------------------------------------------------------------------
def decompose(d, prev, cur, tier="CORE", value="UGrad"):
    """Split the year-on-year change into three parts.

    The basket is a list of courses, not a fixed set of seats: the registrar
    adds and retires courses between years (Fall 2026 retired LIFESCI 2 and
    opened HEB 10/50/55). Lumping those in with the rest makes a supply change
    look like a demand change, so they are reported separately:

      same    courses offered in BOTH terms  -> the demand signal
      added   offered in `cur` only          -> new supply
      dropped offered in `prev` only         -> retired supply
    """
    x = d[(d.tier == tier) & (d.term.isin([prev, cur]))]
    p = x.groupby(["course", "term"])[value].sum().unstack("term")
    p = p.reindex(columns=[prev, cur])
    both = p[prev].notna() & p[cur].notna()
    only_cur = p[prev].isna() & p[cur].notna()
    only_prev = p[prev].notna() & p[cur].isna()
    return {
        "same_prev": p.loc[both, prev].sum(),
        "same_cur": p.loc[both, cur].sum(),
        "same_chg": p.loc[both, cur].sum() - p.loc[both, prev].sum(),
        "n_same": int(both.sum()),
        "added": p.loc[only_cur, cur].sum(),
        "added_courses": list(p.index[only_cur]),
        "dropped": p.loc[only_prev, prev].sum(),
        "dropped_courses": list(p.index[only_prev]),
    }


def composition_report(d):
    for season, terms in [("FALL", FALLS), ("SPRING", SPRINGS)]:
        prev, cur = terms[-2], terms[-1]
        print("=" * 78)
        print(f"{season} CORE basket, composition-controlled: {prev} -> {cur}")
        print("=" * 78)
        r = decompose(d, prev, cur)
        net = r["same_chg"] + r["added"] - r["dropped"]
        print(f"  courses offered in both terms ({r['n_same']}): "
              f"{r['same_prev']:.0f} -> {r['same_cur']:.0f} seats "
              f"({r['same_chg']:+.0f}, {100*r['same_chg']/r['same_prev']:+.1f}%)  <-- demand signal")
        print(f"  newly offered in {cur}: {r['added']:+.0f} seats  {r['added_courses']}")
        print(f"  retired after {prev}:   {-r['dropped']:+.0f} seats  {r['dropped_courses']}")
        print(f"  net change:            {net:+.0f} seats")
        print()


if __name__ == "__main__":
    composition_report(tag(el.load_all()))
