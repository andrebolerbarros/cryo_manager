"""Helpers for 'Winter is coming': validate animal rows, merge by age in weeks, format."""
from datetime import date

import pandas as pd

SEXES = {"Female": "F", "Male": "M"}


def age_weeks(dob: str, today: date | None = None) -> int:
    return ((today or date.today()) - date.fromisoformat(dob)).days // 7


def merge_by_weeks(animals: list[dict], today: date | None = None) -> list[dict]:
    """Group animals of the same sex and the same whole number of weeks old (4.3w and 4.1w -> 4w).

    Returns rows sorted by age (youngest first), then sex:
    {'sex', 'weeks', 'n', 'dobs': [(iso_dob, n), ...]}
    """
    groups: dict[tuple[int, str], dict] = {}
    for a in animals:
        g = groups.setdefault((age_weeks(a["dob"], today), a["sex"]),
                              {"sex": a["sex"], "weeks": age_weeks(a["dob"], today), "n": 0, "dobs": {}})
        g["n"] += a["n"]
        g["dobs"][a["dob"]] = g["dobs"].get(a["dob"], 0) + a["n"]
    rows = sorted(groups.values(), key=lambda g: (g["weeks"], g["sex"]))
    for g in rows:
        g["dobs"] = sorted(g["dobs"].items())
    return rows


def format_sex_age(row: dict) -> str:
    return f"{row['n']} {'♀' if row['sex'] == 'F' else '♂'} × {row['weeks']}w"


def format_dobs(row: dict) -> str:
    """'14-09-2026' or, when several DOBs were merged, '14-09-2026 (3) · 16-09-2026 (2)'."""
    fmt = lambda iso: date.fromisoformat(iso).strftime("%d-%m-%Y")
    if len(row["dobs"]) == 1:
        return fmt(row["dobs"][0][0])
    return " · ".join(f"{fmt(d)} ({n})" for d, n in row["dobs"])


def format_animals(animals: list[dict], today: date | None = None) -> str:
    """One-line summary, e.g. '3 ♀ × 4w · 2 ♂ × 6w'."""
    return " · ".join(format_sex_age(r) for r in merge_by_weeks(animals, today))


def rows_to_animals(df: pd.DataFrame, today: date | None = None) -> tuple[list[dict], list[str]]:
    """Turn the edited Sex/DOB/Number table into animals; identical sex+DOB rows are merged."""
    today = today or date.today()
    groups: dict[tuple[str, str], int] = {}
    problems: list[str] = []
    for i, r in enumerate(df.itertuples(index=False), start=1):
        sex, dob, n = r.Sex, r.DOB, r.Number
        if pd.isna(sex) or pd.isna(dob) or pd.isna(n):
            problems.append(f"Row {i} is incomplete — fill sex, DOB and number (or delete the row).")
            continue
        dob = pd.Timestamp(dob).date()
        if dob > today:
            problems.append(f"Row {i}: date of birth {dob.strftime('%d-%m-%Y')} is in the future.")
        elif int(n) < 1:
            problems.append(f"Row {i}: number of animals must be at least 1.")
        else:
            key = (SEXES[sex], dob.isoformat())
            groups[key] = groups.get(key, 0) + int(n)
    if not groups and not problems:
        problems.append("Add at least one row (sex, DOB, number of animals).")
    animals = [{"sex": s, "dob": d, "n": n}
               for (s, d), n in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0]))]
    return animals, problems
