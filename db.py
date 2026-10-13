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
    shelf       TEXT    NOT NULL,
    position    TEXT    NOT NULL,
    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (end_id - start_id + 1 = n_straws)
);
"""

SEED = [
    # strain, material, n_straws, start, end, n_embryos, shelf, position
    ("GDF15 KO", "Sperm", 10, 1, 10, None, "S1", "Rack A, Row 1"),
    ("GDF15 KO", "Embryo", 6, 1, 6, 180, "S2", "Rack B, Row 3"),
    ("FXR KO", "Sperm", 8, 1, 8, None, "S1", "Rack A, Row 2"),
    ("Olfr56 KO", "Embryo", 12, 1, 12, 360, "S2", "Rack C, Row 1"),
    ("Olfr56 KO", "Sperm", 5, 1, 5, None, "S1", "Rack A, Row 4"),
    ("CXCL5 KO", "Sperm", 15, 1, 15, None, "S3", "Rack D, Row 2"),
    ("CXCL5 KO", "Embryo", 4, 1, 4, 100, "S3", "Rack D, Row 5"),
    ("B6J", "Embryo", 20, 1, 20, 600, "S4", "Rack E, Row 1"),
    ("B6J", "Sperm", 20, 21, 40, None, "S4", "Rack E, Row 3"),
]


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def seed_if_empty() -> None:
    with connect() as con:
        if con.execute("SELECT COUNT(*) FROM batches").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO batches (strain, material, n_straws, start_id, end_id,"
                " n_embryos, shelf, position) VALUES (?,?,?,?,?,?,?,?)",
                SEED,
            )


def strains() -> list[str]:
    with connect() as con:
        rows = con.execute("SELECT DISTINCT strain FROM batches ORDER BY strain COLLATE NOCASE")
        return [r[0] for r in rows]


def overlap(strain: str, material: str, start: int, end: int) -> pd.DataFrame:
    """Existing batches of the same strain+material whose straw-ID range intersects [start, end]."""
    with connect() as con:
        return pd.read_sql_query(
            "SELECT * FROM batches WHERE strain = ? COLLATE NOCASE AND material = ?"
            " AND start_id <= ? AND end_id >= ?",
            con, params=(strain, material, end, start),
        )


def add_batch(strain, material, n_straws, start_id, end_id, n_embryos, shelf, position) -> None:
    with connect() as con:
        con.execute(
            "INSERT INTO batches (strain, material, n_straws, start_id, end_id,"
            " n_embryos, shelf, position) VALUES (?,?,?,?,?,?,?,?)",
            (strain, material, n_straws, start_id, end_id,
             n_embryos if material == "Embryo" else None, shelf, position),
        )


def search(query: str) -> pd.DataFrame:
    """Case-insensitive substring match on strain name."""
    with connect() as con:
        return pd.read_sql_query(
            "SELECT * FROM batches WHERE strain LIKE ? ORDER BY strain COLLATE NOCASE, material, start_id",
            con, params=(f"%{query.strip()}%",),
        )
