"""SQLite storage for cryopreserved batches. One row = one contiguous block of straws."""
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
    n_embryos   INTEGER,              -- only meaningful for Embryo
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

CREATE TABLE IF NOT EXISTS thaw_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    strain     TEXT    NOT NULL,
    material   TEXT    NOT NULL,
    n_straws   INTEGER NOT NULL,
    first_id   INTEGER NOT NULL,
    last_id    INTEGER NOT NULL,
    n_embryos  INTEGER,
    lab        TEXT    NOT NULL DEFAULT '',
    agendo_id  TEXT    NOT NULL DEFAULT '',
    shelf      TEXT    NOT NULL,
    position   TEXT    NOT NULL,
    thawed_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
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
    con.commit()  # leave no implicit transaction open (thaw_many starts its own)
    return con


def _sync_labs(con: sqlite3.Connection) -> None:
    """Every lab already used by a batch must exist in the labs list."""
    con.execute("INSERT OR IGNORE INTO labs (name) SELECT DISTINCT lab FROM batches WHERE lab <> ''")


def seed_if_empty() -> None:
    with connect() as con:
        if con.execute("SELECT COUNT(*) FROM batches").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO batches (strain, material, n_straws, start_id, end_id,"
                " n_embryos, shelf, position, lab, agendo_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
                SEED,
            )
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
    """Existing batches of the same strain+material whose straw-ID range intersects [start, end]."""
    with connect() as con:
        return pd.read_sql_query(
            "SELECT * FROM batches WHERE strain = ? COLLATE NOCASE AND material = ?"
            " AND start_id <= ? AND end_id >= ?",
            con, params=(strain, material, end, start),
        )


def add_batch(strain, material, n_straws, start_id, end_id, n_embryos, shelf, position,
              lab, agendo_id) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO batches (strain, material, n_straws, start_id, end_id,"
            " n_embryos, shelf, position, lab, agendo_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (strain, material, n_straws, start_id, end_id,
             n_embryos if material == "Embryo" else None, shelf, position, lab, agendo_id),
        )


def search(query: str) -> pd.DataFrame:
    """Case-insensitive substring match on strain name."""
    with connect() as con:
        return pd.read_sql_query(
            "SELECT * FROM batches WHERE strain LIKE ? ORDER BY strain COLLATE NOCASE, material, start_id",
            con, params=(f"%{query.strip()}%",),
        )


def thaw_many(selection: dict[int, int]) -> list[dict]:
    """Thaw k straws from each batch id in `selection` ({batch_id: k}), all-or-nothing.

    Straws are taken from the low end of the ID range, so the remainder stays contiguous.
    Embryos are removed pro rata (assumes the same number of embryos per straw);
    thawing a whole batch removes all of its embryos. Every thaw is written to thaw_log.
    """
    done = []
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        for batch_id, k in selection.items():
            r = con.execute("SELECT * FROM batches WHERE id = ?", (batch_id,)).fetchone()
            if r is None:
                raise ValueError("A selected batch no longer exists — reload the page.")
            if not 1 <= k <= r["n_straws"]:
                raise ValueError(
                    f"{r['strain']} {r['material'].lower()}: asked for {k} straw(s) but only "
                    f"{r['n_straws']} left — reload the page.")
            emb = None
            if r["n_embryos"] is not None:
                emb = r["n_embryos"] if k == r["n_straws"] else r["n_embryos"] * k // r["n_straws"]
            first, last = r["start_id"], r["start_id"] + k - 1
            con.execute(
                "INSERT INTO thaw_log (strain, material, n_straws, first_id, last_id, n_embryos,"
                " lab, agendo_id, shelf, position) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (r["strain"], r["material"], k, first, last, emb,
                 r["lab"], r["agendo_id"], r["shelf"], r["position"]))
            if k == r["n_straws"]:
                con.execute("DELETE FROM batches WHERE id = ?", (batch_id,))
            else:
                con.execute(
                    "UPDATE batches SET start_id = ?, n_straws = n_straws - ?, n_embryos = ? WHERE id = ?",
                    (last + 1, k, None if emb is None else r["n_embryos"] - emb, batch_id))
            done.append({"strain": r["strain"], "material": r["material"],
                         "straws": k, "ids": (first, last), "embryos": emb})
    return done


def recent_thaws(limit: int = 15) -> pd.DataFrame:
    with connect() as con:
        return pd.read_sql_query(
            "SELECT thawed_at, strain, material, n_straws, first_id, last_id, n_embryos, lab"
            " FROM thaw_log ORDER BY id DESC LIMIT ?", con, params=(limit,))
