"""SQLite storage for cryopreserved material.

batches = the original freezing submissions (immutable).
straws  = one row per physical straw; thawing sets thawed_at (never deleted, so there is a history
          and straw IDs can't be reused by accident).
"""
import json
import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "cryo.db"
MATERIALS = ("Sperm", "Embryo")

SCHEMA = """
CREATE TABLE IF NOT EXISTS batches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    strain      TEXT    NOT NULL,
    material    TEXT    NOT NULL CHECK (material IN ('Sperm', 'Embryo')),
    n_straws    INTEGER NOT NULL CHECK (n_straws > 0),
    start_id    INTEGER NOT NULL,
    end_id      INTEGER NOT NULL,
    n_embryos   INTEGER,              -- batch total; only meaningful for Embryo
    lab         TEXT    NOT NULL DEFAULT '',
    agendo_id   TEXT    NOT NULL DEFAULT '',
    shelf       TEXT    NOT NULL,
    position    TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_id - start_id + 1 = n_straws)
);

CREATE TABLE IF NOT EXISTS labs (
    name TEXT PRIMARY KEY COLLATE NOCASE
);

CREATE TABLE IF NOT EXISTS straws (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id   INTEGER NOT NULL REFERENCES batches(id),
    straw_no   INTEGER NOT NULL,
    n_embryos  INTEGER,               -- embryos in this straw (Embryo only)
    thawed_at  TEXT,                  -- NULL = still in the freezer
    UNIQUE (batch_id, straw_no)
);

CREATE TABLE IF NOT EXISTS plans (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    agendo_id  TEXT NOT NULL,
    strain_id  TEXT NOT NULL,
    comment    TEXT NOT NULL,
    animals    TEXT NOT NULL,         -- JSON: [{"sex": "F", "dob": "2026-01-15", "n": 3}, ...]
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

SEED = [
    # strain, material, n_straws, start, end, n_embryos, shelf, position, lab, agendo_id
    ("GDF15 KO", "Sperm", 10, 1, 10, None, "S1", "Rack A, Row 1", "Lab Silva", "AG-1001"),
    ("GDF15 KO", "Sperm", 5, 11, 15, None, "S1", "Rack A, Row 5", "Lab Silva", "AG-1001"),
    ("GDF15 KO", "Embryo", 6, 1, 6, 180, "S2", "Rack B, Row 3", "Lab Silva", "AG-1001"),
    ("GDF15 KO", "Embryo", 4, 7, 10, 120, "S2", "Rack B, Row 4", "Lab Silva", "AG-1001"),
    ("FXR KO", "Sperm", 8, 1, 8, None, "S1", "Rack A, Row 2", "Lab Costa", "AG-1002"),
    ("Olfr56 KO", "Embryo", 12, 1, 12, 360, "S2", "Rack C, Row 1", "Lab Silva", "AG-1003"),
    ("Olfr56 KO", "Sperm", 5, 1, 5, None, "S1", "Rack A, Row 4", "Lab Silva", "AG-1003"),
    ("CXCL5 KO", "Sperm", 15, 1, 15, None, "S3", "Rack D, Row 2", "Lab Costa", "AG-1004"),
    ("CXCL5 KO", "Embryo", 4, 1, 4, 100, "S3", "Rack D, Row 5", "Lab Costa", "AG-1004"),
    ("B6J", "Embryo", 20, 1, 20, 600, "S4", "Rack E, Row 1", "Core Facility", "AG-1005"),
    ("B6J", "Sperm", 20, 21, 40, None, "S4", "Rack E, Row 3", "Core Facility", "AG-1005"),
]


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    cols = {r[1] for r in con.execute("PRAGMA table_info(batches)")}
    for c in ("lab", "agendo_id"):  # migrate DBs created before these columns existed
        if c not in cols:
            con.execute(f"ALTER TABLE batches ADD COLUMN {c} TEXT NOT NULL DEFAULT ''")
    _sync_labs(con)
    _populate_straws(con)
    con.commit()  # leave no implicit transaction open (thaw_straws starts its own)
    return con


def _sync_labs(con: sqlite3.Connection) -> None:
    """Every lab already used by a batch must exist in the labs list."""
    con.execute("INSERT OR IGNORE INTO labs (name) SELECT DISTINCT lab FROM batches WHERE lab <> ''")


def _insert_straws(con, batch_id, material, start_id, n_straws, n_embryos) -> None:
    """Spread the batch's embryo total over its straws (integers that sum exactly to the total)."""
    if material == "Embryo" and n_embryos is not None:
        base, rem = divmod(n_embryos, n_straws)
        per = [base + (1 if i < rem else 0) for i in range(n_straws)]
    else:
        per = [None] * n_straws
    con.executemany(
        "INSERT INTO straws (batch_id, straw_no, n_embryos) VALUES (?,?,?)",
        [(batch_id, start_id + i, per[i]) for i in range(n_straws)])


def _populate_straws(con: sqlite3.Connection) -> None:
    """Create straw rows for batches saved before the straws table existed."""
    rows = con.execute(
        "SELECT id, material, start_id, n_straws, n_embryos FROM batches b"
        " WHERE NOT EXISTS (SELECT 1 FROM straws s WHERE s.batch_id = b.id)").fetchall()
    for r in rows:
        _insert_straws(con, r["id"], r["material"], r["start_id"], r["n_straws"], r["n_embryos"])


def _insert_batch(con, strain, material, n_straws, start_id, end_id, n_embryos,
                  shelf, position, lab, agendo_id) -> None:
    n_embryos = n_embryos if material == "Embryo" else None
    cur = con.execute(
        "INSERT INTO batches (strain, material, n_straws, start_id, end_id, n_embryos,"
        " shelf, position, lab, agendo_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (strain, material, n_straws, start_id, end_id, n_embryos, shelf, position, lab, agendo_id))
    _insert_straws(con, cur.lastrowid, material, start_id, n_straws, n_embryos)


def seed_if_empty() -> None:
    with connect() as con:
        if con.execute("SELECT COUNT(*) FROM batches").fetchone()[0] == 0:
            for row in SEED:
                _insert_batch(con, *row)
            _sync_labs(con)


def strains() -> list[str]:
    with connect() as con:
        rows = con.execute("SELECT DISTINCT strain FROM batches ORDER BY strain COLLATE NOCASE")
        return [r[0] for r in rows]


def labs() -> list[str]:
    with connect() as con:
        return [r[0] for r in con.execute("SELECT name FROM labs ORDER BY name COLLATE NOCASE")]


def add_lab(name: str) -> bool:
    """Returns False if a lab with this name (case-insensitive) already exists."""
    with connect() as con:
        cur = con.execute("INSERT OR IGNORE INTO labs (name) VALUES (?)", (name.strip(),))
        return cur.rowcount == 1


def overlap(strain: str, material: str, start: int, end: int) -> pd.DataFrame:
    """Earlier batches of the same strain+material whose straw-ID range intersects [start, end].
    Includes straws that were already thawed, so IDs are never reused."""
    with connect() as con:
        return pd.read_sql_query(
            "SELECT * FROM batches WHERE strain = ? COLLATE NOCASE AND material = ?"
            " AND start_id <= ? AND end_id >= ?",
            con, params=(strain, material, end, start))


def add_batch(strain, material, n_straws, start_id, end_id, n_embryos, shelf, position,
              lab, agendo_id) -> None:
    with connect() as con:
        _insert_batch(con, strain, material, n_straws, start_id, end_id, n_embryos,
                      shelf, position, lab, agendo_id)


def live_straws(strain_like: str = "", lab_like: str = "", exact_lab: str | None = None) -> pd.DataFrame:
    """Every straw still in the freezer (one row each); case-insensitive substring filters,
    or exact_lab for an exact (case-insensitive) lab match."""
    with connect() as con:
        return pd.read_sql_query(
            "SELECT s.id AS straw_id, s.batch_id, s.straw_no, s.n_embryos, b.strain, b.material,"
            " b.lab, b.agendo_id, b.shelf, b.position"
            " FROM straws s JOIN batches b ON b.id = s.batch_id"
            " WHERE s.thawed_at IS NULL AND b.strain LIKE ? AND b.lab LIKE ?"
            + (" AND b.lab = ? COLLATE NOCASE" if exact_lab is not None else "") +
            " ORDER BY b.strain COLLATE NOCASE, b.material, b.shelf, b.position, b.id, s.straw_no",
            con, params=(f"%{strain_like.strip()}%", f"%{lab_like.strip()}%",
                         *([exact_lab] if exact_lab is not None else [])))


def _ranges(nums) -> str:
    """[1,2,3,7,9,10] -> '1–3, 7, 9–10'"""
    nums, out = sorted(nums), []
    i = 0
    while i < len(nums):
        j = i
        while j + 1 < len(nums) and nums[j + 1] == nums[j] + 1:
            j += 1
        out.append(str(nums[i]) if i == j else f"{nums[i]}–{nums[j]}")
        i = j + 1
    return ", ".join(out)


def summarize_batches(straws: pd.DataFrame) -> pd.DataFrame:
    """Collapse live straws to one row per batch: ID ranges, straw count, embryo total."""
    rows = []
    for _, g in straws.groupby("batch_id", sort=False):
        f = g.iloc[0]
        rows.append({
            "strain": f.strain, "material": f.material, "lab": f.lab, "agendo_id": f.agendo_id,
            "shelf": f.shelf, "position": f.position, "ids": _ranges(g.straw_no.tolist()),
            "n_straws": len(g),
            "n_embryos": int(g.n_embryos.sum()) if f.material == "Embryo" else None,
        })
    return pd.DataFrame(rows, columns=["strain", "material", "lab", "agendo_id", "shelf",
                                       "position", "ids", "n_straws", "n_embryos"])


def thaw_straws(straw_ids: list[int]) -> list[dict]:
    """Mark the given straws as thawed, all-or-nothing. Fails if any is already gone."""
    ids = sorted({int(i) for i in straw_ids})
    marks = ",".join("?" * len(ids))
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        rows = con.execute(
            "SELECT s.id, s.straw_no, s.n_embryos, s.thawed_at, b.strain, b.material"
            f" FROM straws s JOIN batches b ON b.id = s.batch_id WHERE s.id IN ({marks})",
            ids).fetchall()
        if len(rows) != len(ids) or any(r["thawed_at"] is not None for r in rows):
            raise ValueError("Some selected straws are no longer in the freezer — reload the page.")
        con.execute(f"UPDATE straws SET thawed_at = CURRENT_TIMESTAMP WHERE id IN ({marks})", ids)
    out: dict[tuple, dict] = {}
    for r in rows:
        d = out.setdefault((r["strain"], r["material"]),
                           {"strain": r["strain"], "material": r["material"], "nums": [], "embryos": 0})
        d["nums"].append(r["straw_no"])
        d["embryos"] += r["n_embryos"] or 0
    return [{"strain": d["strain"], "material": d["material"], "straws": len(d["nums"]),
             "ids": _ranges(d["nums"]), "embryos": d["embryos"] if d["material"] == "Embryo" else None}
            for d in out.values()]


def recent_thaws(limit: int = 20) -> pd.DataFrame:
    with connect() as con:
        return pd.read_sql_query(
            "SELECT s.thawed_at, b.strain, b.material, s.straw_no, s.n_embryos, b.lab"
            " FROM straws s JOIN batches b ON b.id = s.batch_id WHERE s.thawed_at IS NOT NULL"
            " ORDER BY s.thawed_at DESC, s.id DESC LIMIT ?", con, params=(limit,))


def add_plan(agendo_id: str, strain_id: str, comment: str, animals: list[dict]) -> None:
    with connect() as con:
        con.execute("INSERT INTO plans (agendo_id, strain_id, comment, animals) VALUES (?,?,?,?)",
                    (agendo_id, strain_id, comment, json.dumps(animals)))


def plans() -> list[dict]:
    """Newest first; 'animals' is already decoded."""
    with connect() as con:
        rows = con.execute("SELECT * FROM plans ORDER BY id DESC").fetchall()
    return [{**dict(r), "animals": json.loads(r["animals"])} for r in rows]
