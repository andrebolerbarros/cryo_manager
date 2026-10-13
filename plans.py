"""Helpers for 'Winter is coming': validate animal rows and format sex × DOB (age in weeks)."""
from datetime import date

import pandas as pd

SEXES = {"Female": "F", "Male": "M"}


def age_weeks(dob: str, today: date | None = None) -> int:
    return ((today or date.today()) - date.fromisoformat(dob)).days // 7


def format_animals(animals: list[dict], today: date | None = None) -> str:
    """'3 ♀ × 14-09-2026 (4w) · 2 ♂ × 02-09-2026 (6w)' — age is computed against `today`."""
    parts = []
    for a in animals:
        d = date.fromisoformat(a["dob"])
        parts.append(f"{a['n']} {'♀' if a['sex'] == 'F' else '♂'} × {d.strftime('%d-%m-%Y')} "
                     f"({age_weeks(a['dob'], today)}w)")
    return " · ".join(parts)


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
