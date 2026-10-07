"""
Shared loader + taxonomy for the Harvard FAS course-enrollment analysis.
Kept in one place so the notebook stays readable.
"""
import re
import numpy as np
import pandas as pd
from pathlib import Path

COUNT_COLS = ["UGrad", "Grad", "NonDegree", "XReg", "VUS", "Employee", "Withdraw", "Total"]

# term key -> (filename, pretty label, season, academic year of the fall)
TERM_FILES = {
    "S22": ("archive/S22.csv", "Spring 2022", "Spring", 2022),
    "F22": ("archive/F22.csv", "Fall 2022",   "Fall",   2022),
    "S23": ("archive/S23.csv", "Spring 2023", "Spring", 2023),
    "F23": ("archive/F23.csv", "Fall 2023",   "Fall",   2023),
    "S24": ("archive/S24.csv", "Spring 2024", "Spring", 2024),
    "F24": ("archive/F24.csv", "Fall 2024",   "Fall",   2024),
    "S25": ("Class Enrollment Summary by Term_Spring 25.csv", "Spring 2025", "Spring", 2025),
    "F25": ("Class Enrollment Summary by Term_Fall 25.csv",   "Fall 2025",   "Fall",   2025),
    "S26": ("Class Enrollment Summary by Term_Spring 26.csv", "Spring 2026", "Spring", 2026),
    "F26": ("Class Enrollment Summary_Fall 26.csv",           "Fall 2026",   "Fall",   2026),
}


# ----------------------------------------------------------------------------
# Loading
# ----------------------------------------------------------------------------
HEADER_STARTS = ("Class Number,", "Course ID,")

# Subject codes the registrar renamed mid-window. Left unmapped they would show
# up as a course "disappearing" in one year and a new one "appearing" in the next.
SUBJECT_ALIASES = {
    "FRSEMR": "FYSEMR",      # First-Year Seminar Program, renamed in 2023
    "HSEMR-EL": "FYSEMR",
    "HSEMR-LE": "FYSEMR",
    "AAAS": "AFRAMER",       # African & African American Studies
    # Fall 2026 split Engineering Sciences: ENG-SCI 152/155/157 became
    # ECE 152/155/157 with identical numbers. Map back so the series is continuous.
    "ECE": "ENG-SCI",
}

# Department labels the registrar re-spelled mid-window. Without these, a rename
# reads as a department losing all its students and a new one appearing.
DEPT_ALIASES = {
    "Human Evolutionary Biology": "Human Biology, Behavior,& Evol",
    "Freshman Seminars": "First Year Seminar Program",
    # Fall 2026 broke "Medical Sciences" into its constituent HILS programs.
    # These are graduate programs with ~0 undergraduates; folding them back keeps
    # the department series comparable.
    "Biological and Biomedical Scie": "Medical Sciences",
    "Biomedical Informatics": "Medical Sciences",
    "Immunology": "Medical Sciences",
    "Speech and Hearing Bioscience": "Medical Sciences",
    "Virology": "Medical Sciences",
    "Electrical and Computer Engine": "Engineering Sciences",
}


def _find_header(path):
    """Report files have a variable-length preamble, and the ID column was renamed
    from 'Course ID' to 'Class Number' in the 2024 reports. Find the real header."""
    with open(path, encoding="latin-1") as fh:
        for i, line in enumerate(fh):
            if line.startswith(HEADER_STARTS):
                return i
    raise ValueError(f"no header row found in {path}")


def _run_date(path):
    with open(path, encoding="latin-1") as fh:
        for line in fh:
            m = re.search(r"Time run:\s*([\d/]+)", line)
            if m:
                return pd.to_datetime(m.group(1))
            if line.startswith(HEADER_STARTS):
                break
    return pd.NaT


def load_term(key, root="."):
    """Load one term's report into a tidy, typed frame."""
    fname, label, season, year = TERM_FILES[key]
    path = Path(root) / fname
    hdr = _find_header(path)
    df = pd.read_csv(path, skiprows=hdr, encoding="latin-1", dtype=str)
    df = df.rename(columns={"Course ID": "Class Number"})

    # The report appends a filter/footer block after the data; data rows are the
    # ones with a numeric Class Number, so truncate at the last of those.
    is_num = pd.to_numeric(df["Class Number"], errors="coerce").notna()
    df = df.loc[: is_num[::-1].idxmax()].copy()
    df = df[is_num.loc[df.index]]

    for c in COUNT_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)

    df = df.rename(columns={
        "Course Title": "course_code",
        "Course Name": "course_name",
        "Course Department": "dept",
        "Instructor Full Name": "instructor",
        "Course Section Code": "section",
    })
    keep = ["Class Number", "course_code", "course_name", "section", "dept",
            "instructor"] + COUNT_COLS
    df = df[[c for c in keep if c in df.columns]]

    df["term"] = key
    df["term_label"] = label
    df["season"] = season
    df["year"] = year
    df["run_date"] = _run_date(path)

    df["course_code"] = df["course_code"].str.strip()
    df["subject"] = df["course_code"].str.extract(r"^(\S+)")[0].replace(SUBJECT_ALIASES)
    df["catalog"] = df["course_code"].str.split(n=1).str[-1].str.strip()
    df["catalog_num"] = pd.to_numeric(
        df["catalog"].str.extract(r"(\d+)")[0], errors="coerce")
    df["instructor"] = df["instructor"].fillna("(none listed)").str.strip()
    df["dept"] = df["dept"].fillna("(unknown)").str.strip().replace(DEPT_ALIASES)
    return df


def load_all(root=".", keys=None):
    keys = keys or list(TERM_FILES)
    return pd.concat([load_term(k, root) for k in keys], ignore_index=True)


# ----------------------------------------------------------------------------
# Taxonomy
# ----------------------------------------------------------------------------
# Departments already reported to be enforcing a 20%+4 style A cap, plus the
# wider rings the user asked to be tested separately.
CS_ONLY = ["Computer Science"]
SEAS = ["Computer Science", "Applied Computation", "Engineering Sciences",
        "Applied Mathematics", "Electrical and Computer Engine",
        "Biomedical Engineering", "Environmental Sci & Engineer",
        "Applied Physics", "Quantum Science & Engineering",
        "Arch, Landscape & Urban Plan"]
QUANT_CORE = ["Computer Science", "Mathematics", "Statistics", "Physics",
              "Economics", "Chemistry & Chemical Biology"]

DEPT_GROUPS = {"CS only": CS_ONLY, "SEAS": SEAS, "Quant core": QUANT_CORE}

# Tutorial / seminar-by-design subject codes and catalog ranges.
SEMINAR_SUBJECTS = {"FYSEMR"}                 # First-Year Seminar Program
TUTORIAL_NUMS = {97, 98, 99}                  # sophomore/junior/senior tutorials
SEMINAR_MAX = 50                              # user's definition: seminar = < 50 students

# Pre-med requirement courses, from FAS Career Services' premedical page.
# Matched on (subject, catalog-number) so section suffixes (A/B) are handled.
PREMED_COURSES = {
    "Chemistry (intro)":   [("LIFESCI", 1), ("LIFESCI", 50), ("PHYSCI", 11), ("CHEM", 103), ("PHYSCI", 10)],
    "Organic chemistry":   [("CHEM", 17), ("CHEM", 27), ("CHEM", 20), ("CHEM", 30)],
    "Biology":             [("LIFESCI", 2), ("MCB", 60), ("MCB", 68), ("OEB", 10), ("OEB", 58),
                            ("SCRB", 50), ("HEB", 10), ("HEB", 50), ("HEB", 55), ("ENG-SCI", 53)],
    "Biochemistry":        [("MCB", 63), ("MCB", 65), ("MCB", 130), ("BCMP", 234)],
    "Physics":             [("PHYSCI", 2), ("PHYSCI", 3), ("PHYSCI", 12), ("PHYSICS", 15),
                            ("PHYSICS", 16), ("PHYSICS", 19), ("PHYSICS", 153), ("APPHY", 50)],
    "Math":                [("MATH", 1), ("MATH", 18), ("MATH", 19), ("MATH", 21), ("APMTH", 21)],
    "Statistics":          [("STAT", 104), ("STAT", 110), ("PSY", 1900), ("GOV", 50),
                            ("MATH", 19), ("SOCIOL", 1156), ("APMTH", 101), ("ENG-SCI", 150)],
}

# Harvard's "iconic" large courses the user named.
ICONIC = {
    "MATH 55":   ("MATH", 55),
    "STAT 110":  ("STAT", 110),
    "HUM 10":    ("HUMAN", 10),
    "CHEM 10":   ("CHEM", 10),
    "EC 10":     ("ECON", 10),
    "CS 50":     ("COMPSCI", 50),
    "GOV 50":    ("GOV", 50),
}


def classify(df):
    """Add the analysis flags. Operates on a copy."""
    d = df.copy()

    d["is_gened"] = d["subject"].eq("GENED")
    d["is_expos"] = d["subject"].eq("EXPOS")
    d["is_fyseminar"] = d["subject"].isin(SEMINAR_SUBJECTS)
    d["is_tutorial"] = d["catalog_num"].isin(TUTORIAL_NUMS)

    # User's definition: a seminar is a small class (<50), plus first-year
    # seminars and tutorials regardless of size.
    d["is_seminar"] = (d["Total"] < SEMINAR_MAX) | d["is_fyseminar"] | d["is_tutorial"]

    # Level bands. Harvard FAS numbering is NOT simply "200+ = graduate": the
    # renumbering put a large block of undergraduate courses in the 1000s
    # (all of Gen Ed, Ec 1010s, CS 1200s, Psych 1000s ...). Checking who actually
    # sits in each band in Fall 2026:
    #     <100        0.9% graduate      100-199     9.8% graduate
    #     200-299    72.9% graduate      300-999    89.7% graduate
    #     1000-1999   2.9% graduate      2000+      80.3% graduate
    # so the graduate block is 200-999 plus 2000+, and 1000-1999 is undergraduate.
    n = d["catalog_num"]
    d["is_gradlevel"] = ((n >= 200) & (n < 1000)) | (n >= 2000)
    d["level"] = np.select(
        [n < 100, ((n >= 100) & (n < 200)) | ((n >= 1000) & (n < 2000)), d["is_gradlevel"]],
        ["Intro (<100)", "Upper undergrad", "Graduate"], default="Unnumbered")

    for name, members in DEPT_GROUPS.items():
        d[f"grp_{name}"] = d["dept"].isin(members)

    # Pre-med flags
    premed_map = {}
    for band, pairs in PREMED_COURSES.items():
        for subj, num in pairs:
            premed_map.setdefault((subj, num), []).append(band)
    key = list(zip(d["subject"], d["catalog_num"]))
    d["premed_band"] = [",".join(premed_map.get(k, [])) or None for k in key]
    d["is_premed"] = d["premed_band"].notna()

    iconic_map = {v: k for k, v in ICONIC.items()}
    d["iconic"] = [iconic_map.get(k) for k in key]

    return d


# ----------------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------------
def share_table(d, flag, value="UGrad"):
    """Share of a term's total `value` enrollment that sits in rows where flag is True."""
    g = d.groupby("term", observed=True).apply(
        lambda x: pd.Series({
            "in_group": x.loc[x[flag], value].sum(),
            "total": x[value].sum(),
        }), include_groups=False)
    g["share_pct"] = 100 * g["in_group"] / g["total"]
    return g


def yoy(tbl, a, b, col="share_pct"):
    """Percentage-point change from term a to term b."""
    return tbl.loc[b, col] - tbl.loc[a, col]


def course_key(d):
    """Course-level key that collapses multiple sections of the same course."""
    return d["subject"] + " " + d["catalog"].fillna("")


def course_totals(d, value="UGrad"):
    x = d.copy()
    x["course"] = course_key(x)
    return (x.groupby(["term", "course"], observed=True)[value].sum()
             .unstack("term").fillna(0))
