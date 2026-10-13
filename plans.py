"""Parse the free-text comment of a 'Winter is coming' entry into (sex, DOB, count) groups.

Accepted, one group per line or separated by ';':
    3 females DOB 2026-01-15
    2 males, D.O.B. 12/02/2026
    3F 2M DOB: 15 Jan 2026          (one date shared by both sexes on the line)
Dates: YYYY-MM-DD, DD/MM/YYYY (also . or - as separator), or '15 Jan 2026'. Day comes first.
Lines with no number of females/males and no date are treated as plain notes and ignored.
"""
import re
from datetime import date, datetime

DATE_RE = re.compile(
    r"(?<![\d/.\-])(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}|\d{1,2}\s+[A-Za-z]{3,9}\.?\s+\d{4})(?![\d/\-])")
LABEL_RE = re.compile(r"(?i)\b(?:d\.\s?o\.\s?b\.?|dob|date of birth|born)(?![a-z])")
COUNT_FIRST = re.compile(r"(?i)(?<!\d)(\d+)\s*(females?|males?|f|m|♀|♂)(?![a-z])")
SEX_FIRST = re.compile(r"(?i)(?<![a-z])(females?|males?|f|m|♀|♂)\s*[:=x]?\s*(\d+)(?!\d)")


def _sex(token: str) -> str:
    return "F" if token.lower().startswith("f") or token == "♀" else "M"


def _counts(text: str) -> list[tuple[str, int]]:
    hits = [(_sex(m.group(2)), int(m.group(1))) for m in COUNT_FIRST.finditer(text)]
    if not hits:
        hits = [(_sex(m.group(1)), int(m.group(2))) for m in SEX_FIRST.finditer(text)]
    return hits


def _parse_date(token: str) -> date | None:
    token = re.sub(r"\s+", " ", token.replace(".", " ") if re.search(r"[A-Za-z]", token) else token).strip()
    if re.fullmatch(r"\d{1,2}[/.\-]\d{1,2}[/.\-]\d{4}", token):
        token = re.sub(r"[.\-]", "/", token)
        fmts = ["%d/%m/%Y"]
    elif re.fullmatch(r"\d{4}-\d{1,2}-\d{1,2}", token):
        fmts = ["%Y-%m-%d"]
    else:
        fmts = ["%d %b %Y", "%d %B %Y"]
    for f in fmts:
        try:
            return datetime.strptime(token, f).date()
        except ValueError:
            pass
    return None


def parse_comment(text: str, today: date | None = None) -> tuple[list[dict], list[str]]:
    """Returns (animals, problems). animals = [{'sex': 'F'|'M', 'dob': 'YYYY-MM-DD', 'n': int}]."""
    today = today or date.today()
    pieces: list[str] = []
    for seg in (s.strip() for s in re.split(r"[\n;]+", text) if s.strip()):
        if len(DATE_RE.findall(seg)) > 1:  # e.g. '3 F DOB x, 2 M DOB y' on one line
            pieces += [p.strip() for p in seg.split(",") if p.strip()]
        else:
            pieces.append(seg)

    groups: dict[tuple[str, str], int] = {}
    problems: list[str] = []
    for piece in pieces:
        dates = DATE_RE.findall(piece)
        counts = _counts(LABEL_RE.sub(" ", DATE_RE.sub(" ", piece)))
        if not counts:
            if dates:
                problems.append(f"Found a date but no number of females/males in: “{piece}”")
            continue  # plain note
        if not dates:
            problems.append(f"No date of birth found for: “{piece}”")
        elif len(dates) > 1:
            problems.append(f"More than one date in: “{piece}” — put each date on its own line")
        else:
            dob = _parse_date(dates[0])
            if dob is None:
                problems.append(f"Could not read the date “{dates[0]}” in: “{piece}”")
            elif dob > today:
                problems.append(f"Date of birth {dob.isoformat()} is in the future in: “{piece}”")
            else:
                for sex, n in counts:
                    groups[(sex, dob.isoformat())] = groups.get((sex, dob.isoformat()), 0) + n
    if not groups and not problems:
        problems.append("No animals found — write e.g. “3 females DOB 2026-01-15” and "
                        "“2 males DOB 2026-02-12” on separate lines.")
    animals = [{"sex": s, "dob": d, "n": n} for (s, d), n in sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0]))]
    return animals, problems


def format_animals(animals: list[dict]) -> str:
    return " · ".join(f"{a['n']} {'♀' if a['sex'] == 'F' else '♂'} × {a['dob']}" for a in animals)
