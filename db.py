"""SQL storage for cryopreserved material (SQLAlchemy Core: PostgreSQL or SQLite).

batches = the original freezing submissions (immutable).
straws  = one row per physical straw; thawing sets thawed_at (never deleted, so there is a history
          and straw IDs can't be reused by accident).

Which database is used is decided by a URL, looked up in this order:
  1. environment variable CRYO_DATABASE_URL (or DATABASE_URL)
  2. Streamlit secret `database_url`  (.streamlit/secrets.toml)
  3. a local SQLite file, cryo.db next to this module (development default)
e.g. postgresql+psycopg2://user:password@host:5432/cryo
"""
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import (CheckConstraint, Column, DateTime, ForeignKey, Index, Integer, MetaData,
                        String, Table, Text, UniqueConstraint, func, insert, select, text, update)
from sqlalchemy.exc import IntegrityError

DEFAULT_URL = f"sqlite:///{(Path(__file__).parent / 'cryo.db').as_posix()}"
MATERIALS = ("Sperm", "Embryo")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


metadata = MetaData()

batches = Table(
    "batches", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("strain", String, nullable=False),
    Column("material", String, nullable=False),
    Column("n_straws", Integer, nullable=False),
    Column("start_id", Integer, nullable=False),
    Column("end_id", Integer, nullable=False),
    Column("n_embryos", Integer),              # batch total; only meaningful for Embryo
    Column("lab", String, nullable=False, server_default=""),
    Column("agendo_id", String, nullable=False, server_default=""),
    Column("shelf", String, nullable=False),
    Column("position", String, nullable=False),
    Column("created_at", DateTime, nullable=False, default=_utcnow),
    CheckConstraint("material IN ('Sperm', 'Embryo')", name="ck_batches_material"),
    CheckConstraint("n_straws > 0", name="ck_batches_n_straws"),
    CheckConstraint("end_id - start_id + 1 = n_straws", name="ck_batches_range"),
)

labs_t = Table(
    "labs", metadata,
    Column("name", String, primary_key=True),
    Index("uq_labs_name_lower", func.lower(text("name")), unique=True),
)

straws = Table(
    "straws", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("batch_id", Integer, ForeignKey("batches.id"), nullable=False),
    Column("straw_no", Integer, nullable=False),
    Column("n_embryos", Integer),              # embryos in this straw (Embryo only)
    Column("thawed_at", DateTime),             # NULL = still in the freezer
    UniqueConstraint("batch_id", "straw_no", name="uq_straws_batch_straw"),
)

requests_t = Table(
    "requests", metadata,
    Column("agendo_id", String, primary_key=True),
    Column("strain_id", String, nullable=False),
    Column("lab", String, nullable=False),
    Index("uq_requests_agendo_lower", func.lower(text("agendo_id")), unique=True),
)

plans_t = Table(
    "plans", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("agendo_id", String, nullable=False),
    Column("strain_id", String, nullable=False),
    Column("lab", String, nullable=False, server_default=""),
    Column("comment", Text, nullable=False, server_default=""),
    Column("animals", Text, nullable=False),   # JSON: [{"sex": "F", "dob": "2026-01-15", "n": 3}, ...]
    Column("created_at", DateTime, nullable=False, default=_utcnow),
)

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

REQUESTS_SEED = [
    # agendo_id, strain_id, lab
    ("AG-2001", "GDF15 KO", "Lab Silva"),
    ("AG-2002", "FXR KO", "Lab Costa"),
    ("AG-2003", "Olfr56 KO", "Lab Silva"),
    ("AG-2004", "CXCL5 KO", "Lab Costa"),
    ("AG-2005", "B6J", "Core Facility"),
]


# --------------------------------------------------------------------------- engine

def database_url() -> str:
    url = os.environ.get("CRYO_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not url:
        try:
            import streamlit as st
            url = st.secrets.get("database_url")
        except Exception:  # no secrets file / not running under streamlit
            url = None
    url = url or DEFAULT_URL
    if url.startswith("postgres://"):  # SQLAlchemy needs the dialect name
        url = "postgresql+psycopg2://" + url[len("postgres://"):]
    elif url.startswith("postgresql://"):
        url = "postgresql+psycopg2://" + url[len("postgresql://"):]
    return url


def make_engine(url: str) -> sa.Engine:
    return sa.create_engine(url, pool_pre_ping=True, future=True)


def create_schema(eng: sa.Engine) -> None:
    """Create missing tables, and add columns that databases created by older versions lack."""
    metadata.create_all(eng)
    insp = sa.inspect(eng)
    with eng.begin() as con:
        for table, col in (("batches", "lab"), ("batches", "agendo_id"), ("plans", "lab")):
            if col not in {c["name"] for c in insp.get_columns(table)}:
                con.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} VARCHAR NOT NULL DEFAULT ''"))
        _sync_labs(con)
        _populate_straws(con)


_engine: sa.Engine | None = None


def engine() -> sa.Engine:
    global _engine
    if _engine is None:
        eng = make_engine(database_url())
        create_schema(eng)
        _engine = eng
    return _engine


# --------------------------------------------------------------------------- helpers

def _sync_labs(con) -> None:
    """Every lab already used by a batch or request must exist in the labs list (case-insensitive)."""
    con.execute(text(
        "INSERT INTO labs (name)"
        " SELECT MIN(u.lab) FROM (SELECT lab FROM batches UNION SELECT lab FROM requests) u"
        " WHERE u.lab <> '' AND NOT EXISTS (SELECT 1 FROM labs l WHERE lower(l.name) = lower(u.lab))"
        " GROUP BY lower(u.lab)"))


def _insert_straws(con, batch_id, material, start_id, n_straws, n_embryos) -> None:
    """Spread the batch's embryo total over its straws (integers that sum exactly to the total)."""
    if material == "Embryo" and n_embryos is not None:
        base, rem = divmod(n_embryos, n_straws)
        per = [base + (1 if i < rem else 0) for i in range(n_straws)]
    else:
        per = [None] * n_straws
    con.execute(insert(straws), [
        {"batch_id": batch_id, "straw_no": start_id + i, "n_embryos": per[i]} for i in range(n_straws)])


def _populate_straws(con) -> None:
    """Create straw rows for batches saved before the straws table existed."""
    has_straws = select(straws.c.id).where(straws.c.batch_id == batches.c.id).exists()
    rows = con.execute(select(batches.c.id, batches.c.material, batches.c.start_id,
                              batches.c.n_straws, batches.c.n_embryos).where(~has_straws)).all()
    for r in rows:
        _insert_straws(con, r.id, r.material, r.start_id, r.n_straws, r.n_embryos)


def _insert_batch(con, strain, material, n_straws, start_id, end_id, n_embryos,
                  shelf, position, lab, agendo_id) -> None:
    n_embryos = n_embryos if material == "Embryo" else None
    res = con.execute(insert(batches).values(
        strain=strain, material=material, n_straws=n_straws, start_id=start_id, end_id=end_id,
        n_embryos=n_embryos, shelf=shelf, position=position, lab=lab, agendo_id=agendo_id))
    _insert_straws(con, res.inserted_primary_key[0], material, start_id, n_straws, n_embryos)


# --------------------------------------------------------------------------- API (used by views)

def seed_if_empty() -> None:
    with engine().begin() as con:
        if con.execute(select(func.count()).select_from(batches)).scalar() == 0:
            for row in SEED:
                _insert_batch(con, *row)
            _sync_labs(con)
        # toy open requests, only into a database that has neither requests nor plans yet
        if (con.execute(select(func.count()).select_from(requests_t)).scalar() == 0
                and con.execute(select(func.count()).select_from(plans_t)).scalar() == 0):
            con.execute(insert(requests_t), [
                {"agendo_id": a, "strain_id": s, "lab": lab} for a, s, lab in REQUESTS_SEED])
            _sync_labs(con)


def requests() -> list[dict]:
    """Open Agendo requests, each tied to one strain and one lab."""
    with engine().connect() as con:
        rows = con.execute(select(requests_t).order_by(func.lower(requests_t.c.agendo_id)))
        return [dict(r._mapping) for r in rows]


def add_request(agendo_id: str, strain_id: str, lab: str) -> bool:
    """Returns False if this Agendo ID (case-insensitive) already exists."""
    try:
        with engine().begin() as con:
            con.execute(insert(requests_t).values(
                agendo_id=agendo_id.strip(), strain_id=strain_id.strip(), lab=lab))
    except IntegrityError:
        return False
    with engine().begin() as con:
        _sync_labs(con)
    return True


def strains() -> list[str]:
    with engine().connect() as con:
        rows = con.execute(select(batches.c.strain).distinct().order_by(func.lower(batches.c.strain)))
        return [r[0] for r in rows]


def labs() -> list[str]:
    with engine().connect() as con:
        return [r[0] for r in con.execute(select(labs_t.c.name).order_by(func.lower(labs_t.c.name)))]


def add_lab(name: str) -> bool:
    """Returns False if a lab with this name (case-insensitive) already exists."""
    try:
        with engine().begin() as con:
            con.execute(insert(labs_t).values(name=name.strip()))
    except IntegrityError:
        return False
    return True


def overlap(strain: str, material: str, start: int, end: int) -> pd.DataFrame:
    """Earlier batches of the same strain+material whose straw-ID range intersects [start, end].
    Includes straws that were already thawed, so IDs are never reused."""
    q = select(batches).where(
        func.lower(batches.c.strain) == strain.strip().lower(),
        batches.c.material == material,
        batches.c.start_id <= end, batches.c.end_id >= start)
    with engine().connect() as con:
        return pd.read_sql_query(q, con)


def add_batch(strain, material, n_straws, start_id, end_id, n_embryos, shelf, position,
              lab, agendo_id) -> None:
    with engine().begin() as con:
        _insert_batch(con, strain, material, n_straws, start_id, end_id, n_embryos,
                      shelf, position, lab, agendo_id)


def live_straws(strain_like: str = "", lab_like: str = "", exact_lab: str | None = None) -> pd.DataFrame:
    """Every straw still in the freezer (one row each); case-insensitive substring filters,
    or exact_lab for an exact (case-insensitive) lab match."""
    q = (select(straws.c.id.label("straw_id"), straws.c.batch_id, straws.c.straw_no, straws.c.n_embryos,
                batches.c.strain, batches.c.material, batches.c.lab, batches.c.agendo_id,
                batches.c.shelf, batches.c.position)
         .join(batches, batches.c.id == straws.c.batch_id)
         .where(straws.c.thawed_at.is_(None),
                batches.c.strain.icontains(strain_like.strip(), autoescape=True),
                batches.c.lab.icontains(lab_like.strip(), autoescape=True)))
    if exact_lab is not None:
        q = q.where(func.lower(batches.c.lab) == exact_lab.lower())
    q = q.order_by(func.lower(batches.c.strain), batches.c.material, batches.c.shelf,
                   batches.c.position, batches.c.id, straws.c.straw_no)
    with engine().connect() as con:
        return pd.read_sql_query(q, con)


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


def summarize_batches(straws_df: pd.DataFrame) -> pd.DataFrame:
    """Collapse live straws to one row per batch: ID ranges, straw count, embryo total."""
    rows = []
    for _, g in straws_df.groupby("batch_id", sort=False):
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
    with engine().begin() as con:
        # lock the rows (FOR UPDATE on PostgreSQL) so two sessions can't thaw the same straw
        rows = con.execute(
            select(straws.c.id, straws.c.straw_no, straws.c.n_embryos, straws.c.thawed_at,
                   batches.c.strain, batches.c.material)
            .join(batches, batches.c.id == straws.c.batch_id)
            .where(straws.c.id.in_(ids)).with_for_update(of=straws)).all()
        if len(rows) != len(ids) or any(r.thawed_at is not None for r in rows):
            raise ValueError("Some selected straws are no longer in the freezer — reload the page.")
        res = con.execute(update(straws).where(straws.c.id.in_(ids), straws.c.thawed_at.is_(None))
                          .values(thawed_at=_utcnow()))
        if res.rowcount != len(ids):
            raise ValueError("Some selected straws are no longer in the freezer — reload the page.")
    out: dict[tuple, dict] = {}
    for r in rows:
        d = out.setdefault((r.strain, r.material),
                           {"strain": r.strain, "material": r.material, "nums": [], "embryos": 0})
        d["nums"].append(r.straw_no)
        d["embryos"] += r.n_embryos or 0
    return [{"strain": d["strain"], "material": d["material"], "straws": len(d["nums"]),
             "ids": _ranges(d["nums"]), "embryos": d["embryos"] if d["material"] == "Embryo" else None}
            for d in out.values()]


def recent_thaws(limit: int = 20) -> pd.DataFrame:
    q = (select(straws.c.thawed_at, batches.c.strain, batches.c.material, straws.c.straw_no,
                straws.c.n_embryos, batches.c.lab)
         .join(batches, batches.c.id == straws.c.batch_id)
         .where(straws.c.thawed_at.is_not(None))
         .order_by(straws.c.thawed_at.desc(), straws.c.id.desc()).limit(limit))
    with engine().connect() as con:
        return pd.read_sql_query(q, con)


def add_plan(agendo_id: str, strain_id: str, lab: str, animals: list[dict]) -> None:
    with engine().begin() as con:
        con.execute(insert(plans_t).values(  # comment column kept for old rows
            agendo_id=agendo_id, strain_id=strain_id, lab=lab, comment="", animals=json.dumps(animals)))


def plans() -> list[dict]:
    """Newest first; 'animals' is already decoded."""
    with engine().connect() as con:
        rows = con.execute(select(plans_t).order_by(plans_t.c.id.desc())).all()
    return [{**dict(r._mapping), "animals": json.loads(r.animals)} for r in rows]
