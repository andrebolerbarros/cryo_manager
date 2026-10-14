"""SQL storage for cryopreserved material (SQLAlchemy Core: PostgreSQL or SQLite).

Tables (each fact lives in one place):

  labs          name, institute, running (a closed lab is hidden from dropdowns, never deleted)
  strains       name, lab it is associated with
  requests      internal id + Agendo ID (editable, unique), strain, requesting lab
  batches       one freezing session of one request; status planned / frozen / cancelled
  batch_animals the animals of a batch: sex, DOB, number (planned and used animals)
  straws        one physical straw: global straw number, material, embryos, location, thawed_at
                (never deleted, so there is a history and straw numbers are never reused)

A batch becomes 'frozen' once its straws are recorded. Sperm/embryo straw counts and the embryo
total of a batch are derived from its straws (batch_overview), not stored twice.

Which database is used is decided by a URL, looked up in this order:
  1. environment variable CRYO_DATABASE_URL (or DATABASE_URL)
  2. Streamlit secret `database_url`  (.streamlit/secrets.toml)
  3. a local SQLite file, cryo.db next to this module (development default)
e.g. postgresql+psycopg2://user:password@host:5432/cryo
"""
import json
import os
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import sqlalchemy as sa
from sqlalchemy import (Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer,
                        MetaData, String, Table, UniqueConstraint, case, func, insert, select, text,
                        update)
from sqlalchemy.exc import IntegrityError

DEFAULT_URL = f"sqlite:///{(Path(__file__).parent / 'cryo.db').as_posix()}"
MATERIALS = ("Sperm", "Embryo")
STATUSES = ("planned", "frozen", "cancelled")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


metadata = MetaData()

labs_t = Table(
    "labs", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, nullable=False),
    Column("institute", String, nullable=False, server_default=""),
    Column("running", Boolean, nullable=False, server_default=sa.true()),
    Index("uq_labs_name_lower", func.lower(text("name")), unique=True),
)

strains_t = Table(
    "strains", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("name", String, nullable=False),
    Column("lab_id", Integer, ForeignKey("labs.id")),
    Index("uq_strains_name_lower", func.lower(text("name")), unique=True),
)

requests_t = Table(
    "requests", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("agendo_id", String),               # assigned outside the database; unique, may be corrected
    Column("strain_id", Integer, ForeignKey("strains.id"), nullable=False),
    Column("lab_id", Integer, ForeignKey("labs.id"), nullable=False),
    Index("uq_requests_agendo_lower", func.lower(text("agendo_id")), unique=True),
)

batches_t = Table(
    "batches", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("request_id", Integer, ForeignKey("requests.id"), nullable=False),
    Column("status", String, nullable=False, server_default="planned"),
    Column("created_at", DateTime, nullable=False, default=_utcnow),
    Column("frozen_at", DateTime),
    CheckConstraint("status IN ('planned', 'frozen', 'cancelled')", name="ck_batch_status"),
)

animals_t = Table(
    "batch_animals", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("batch_id", Integer, ForeignKey("batches.id"), nullable=False),
    Column("sex", String, nullable=False),
    Column("dob", Date, nullable=False),
    Column("n", Integer, nullable=False),
    CheckConstraint("sex IN ('F', 'M')", name="ck_animal_sex"),
    CheckConstraint("n > 0", name="ck_animal_n"),
)

straws_t = Table(
    "straws", metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("batch_id", Integer, ForeignKey("batches.id"), nullable=False),
    Column("straw_no", Integer, nullable=False),           # global numbering
    Column("material", String, nullable=False),
    Column("n_embryos", Integer),                          # Embryo only
    Column("shelf", String, nullable=False),
    Column("position", String, nullable=False),
    Column("thawed_at", DateTime),                         # NULL = still in the freezer
    UniqueConstraint("straw_no", name="uq_straws_straw_no"),
    CheckConstraint("(material = 'Sperm' AND n_embryos IS NULL)"
                    " OR (material = 'Embryo' AND n_embryos >= 0)", name="ck_straw_material"),
)

SEED_LABS = [("Lab Silva", "Institute A"), ("Lab Costa", "Institute A"), ("Core Facility", "Institute B")]

SEED_REQUESTS = [
    # agendo_id, strain, lab, then the frozen straw blocks for that request (may be empty = open request)
    # block: material, n_straws, n_embryos (batch total, spread over the straws), shelf, position
    ("AG-1001", "GDF15 KO", "Lab Silva", [("Sperm", 10, None, "S1", "Rack A, Row 1"),
                                          ("Sperm", 5, None, "S1", "Rack A, Row 5"),
                                          ("Embryo", 6, 180, "S2", "Rack B, Row 3"),
                                          ("Embryo", 4, 120, "S2", "Rack B, Row 4")]),
    ("AG-1002", "FXR KO", "Lab Costa", [("Sperm", 8, None, "S1", "Rack A, Row 2")]),
    ("AG-1003", "Olfr56 KO", "Lab Silva", [("Embryo", 12, 360, "S2", "Rack C, Row 1"),
                                           ("Sperm", 5, None, "S1", "Rack A, Row 4")]),
    ("AG-1004", "CXCL5 KO", "Lab Costa", [("Sperm", 15, None, "S3", "Rack D, Row 2"),
                                          ("Embryo", 4, 100, "S3", "Rack D, Row 5")]),
    ("AG-1005", "B6J", "Core Facility", [("Embryo", 20, 600, "S4", "Rack E, Row 1"),
                                         ("Sperm", 20, None, "S4", "Rack E, Row 3")]),
    # open requests, nothing frozen yet
    ("AG-2001", "GDF15 KO", "Lab Silva", []),
    ("AG-2002", "FXR KO", "Lab Costa", []),
    ("AG-2003", "Olfr56 KO", "Lab Silva", []),
    ("AG-2004", "CXCL5 KO", "Lab Costa", []),
    ("AG-2005", "B6J", "Core Facility", []),
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
    """Create missing tables. A database in the previous layout (strain/lab/shelf on batches, plans
    table) is upgraded in place: its tables are kept as legacy_* and the data is copied across."""
    legacy = _has_legacy_layout(eng)
    if legacy:
        _rename_legacy(eng)
    metadata.create_all(eng)
    if legacy:
        with eng.begin() as con:
            _copy_legacy(con)


_engine: sa.Engine | None = None


def engine() -> sa.Engine:
    global _engine
    if _engine is None:
        eng = make_engine(database_url())
        create_schema(eng)
        _engine = eng
    return _engine


# --------------------------------------------------------------------------- legacy upgrade

def _has_legacy_layout(eng) -> bool:
    insp = sa.inspect(eng)
    return insp.has_table("batches") and "strain" in {c["name"] for c in insp.get_columns("batches")}


def _rename_legacy(eng) -> None:
    with eng.begin() as con:
        for ix in ("uq_labs_name_lower", "uq_requests_agendo_lower"):  # index names are database-wide
            con.execute(text(f"DROP INDEX IF EXISTS {ix}"))
        for t in ("plans", "straws", "requests", "labs", "batches"):
            if sa.inspect(con).has_table(t):
                con.execute(text(f"ALTER TABLE {t} RENAME TO legacy_{t}"))
    insp = sa.inspect(eng)
    with eng.begin() as con:  # very old files lack some columns
        for table, col in (("legacy_batches", "lab"), ("legacy_batches", "agendo_id"), ("legacy_plans", "lab")):
            if insp.has_table(table) and col not in {c["name"] for c in insp.get_columns(table)}:
                con.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} VARCHAR NOT NULL DEFAULT ''"))


def _dt(v):
    if v is None or isinstance(v, datetime):
        return v
    return datetime.fromisoformat(str(v))


def _copy_legacy(con) -> None:
    lab_ids: dict[str, int] = {}
    strain_ids: dict[str, int] = {}
    req_ids: dict[tuple, int] = {}

    def lab_id(name: str) -> int:
        k = name.strip().lower()
        if k not in lab_ids:
            lab_ids[k] = con.execute(insert(labs_t).values(name=name.strip())).inserted_primary_key[0]
        return lab_ids[k]

    def strain_id(name: str, lab: str) -> int:
        k = name.strip().lower()
        if k not in strain_ids:
            strain_ids[k] = con.execute(insert(strains_t).values(
                name=name.strip(), lab_id=lab_id(lab) if lab.strip() else None)).inserted_primary_key[0]
        return strain_ids[k]

    def request_id(agendo: str, strain: str, lab: str) -> int:
        agendo = (agendo or "").strip()
        lab = lab.strip() or "Unknown lab"
        k = (agendo.lower() or None, strain.strip().lower(), lab.lower())
        if k not in req_ids:
            req_ids[k] = con.execute(insert(requests_t).values(
                agendo_id=agendo or None, strain_id=strain_id(strain, lab), lab_id=lab_id(lab))
            ).inserted_primary_key[0]
        return req_ids[k]

    q = lambda sql: con.execute(text(sql)).mappings().all()
    for r in q("SELECT name FROM legacy_labs"):
        lab_id(r["name"])
    for r in q("SELECT agendo_id, strain_id, lab FROM legacy_requests"):
        request_id(r["agendo_id"], r["strain_id"], r["lab"])

    batch_map: dict[int, int] = {}
    for b in q("SELECT * FROM legacy_batches ORDER BY id"):
        req = request_id(b["agendo_id"], b["strain"], b["lab"])
        created = _dt(b["created_at"]) or _utcnow()
        batch_map[b["id"]] = con.execute(insert(batches_t).values(
            request_id=req, status="frozen", created_at=created, frozen_at=created)).inserted_primary_key[0]

    # Straw numbers were only unique per strain+material before; global numbering means renumbering.
    n = 0
    for s in q("SELECT s.id, s.batch_id, s.n_embryos, s.thawed_at, b.material, b.shelf, b.position"
               " FROM legacy_straws s JOIN legacy_batches b ON b.id = s.batch_id ORDER BY s.id"):
        n += 1
        con.execute(insert(straws_t).values(
            batch_id=batch_map[s["batch_id"]], straw_no=n, material=s["material"],
            n_embryos=s["n_embryos"] if s["material"] == "Embryo" else None,
            shelf=s["shelf"], position=s["position"], thawed_at=_dt(s["thawed_at"])))

    for p in q("SELECT * FROM legacy_plans ORDER BY id"):
        bid = con.execute(insert(batches_t).values(
            request_id=request_id(p["agendo_id"], p["strain_id"], p["lab"]), status="planned",
            created_at=_dt(p["created_at"]) or _utcnow())).inserted_primary_key[0]
        for a in json.loads(p["animals"]):
            con.execute(insert(animals_t).values(
                batch_id=bid, sex=a["sex"], dob=date.fromisoformat(a["dob"]), n=a["n"]))
    print(f"[db] upgraded legacy layout: {n} straws renumbered 1..{n} (global numbering); "
          "old tables kept as legacy_*")


# --------------------------------------------------------------------------- seed

def _spread(total: int | None, n: int) -> list[int | None]:
    """Spread an embryo total over n straws (integers that sum exactly to the total)."""
    if total is None:
        return [None] * n
    base, rem = divmod(total, n)
    return [base + (1 if i < rem else 0) for i in range(n)]


def seed_if_empty() -> None:
    with engine().begin() as con:
        if con.execute(select(func.count()).select_from(requests_t)).scalar():
            return
        labs = {n: con.execute(insert(labs_t).values(name=n, institute=i)).inserted_primary_key[0]
                for n, i in SEED_LABS}
        strains: dict[str, int] = {}
        next_no = 1
        for agendo, strain, lab, blocks in SEED_REQUESTS:
            if strain not in strains:
                strains[strain] = con.execute(insert(strains_t).values(
                    name=strain, lab_id=labs[lab])).inserted_primary_key[0]
            req = con.execute(insert(requests_t).values(
                agendo_id=agendo, strain_id=strains[strain], lab_id=labs[lab])).inserted_primary_key[0]
            if not blocks:
                continue
            now = _utcnow()
            batch = con.execute(insert(batches_t).values(
                request_id=req, status="frozen", frozen_at=now)).inserted_primary_key[0]
            for material, n, embryos, shelf, position in blocks:
                per = _spread(embryos if material == "Embryo" else None, n)
                con.execute(insert(straws_t), [
                    {"batch_id": batch, "straw_no": next_no + i, "material": material,
                     "n_embryos": per[i], "shelf": shelf, "position": position} for i in range(n)])
                next_no += n


# --------------------------------------------------------------------------- labs / strains / requests

def labs(include_closed: bool = False) -> list[str]:
    """Lab names for dropdowns; labs that are no longer running are left out unless asked for."""
    q = select(labs_t.c.name).order_by(func.lower(labs_t.c.name))
    if not include_closed:
        q = q.where(labs_t.c.running.is_(True))
    with engine().connect() as con:
        return [r[0] for r in con.execute(q)]


def labs_table() -> pd.DataFrame:
    with engine().connect() as con:
        return pd.read_sql_query(
            select(labs_t.c.id, labs_t.c.name, labs_t.c.institute, labs_t.c.running)
            .order_by(func.lower(labs_t.c.name)), con)


def add_lab(name: str, institute: str = "", running: bool = True) -> bool:
    """Returns False if a lab with this name (case-insensitive) already exists."""
    try:
        with engine().begin() as con:
            con.execute(insert(labs_t).values(name=name.strip(), institute=institute.strip(), running=running))
    except IntegrityError:
        return False
    return True


def update_labs(rows: list[dict]) -> None:
    """rows: [{'id', 'institute', 'running'}, ...] — name is not editable here."""
    with engine().begin() as con:
        for r in rows:
            con.execute(update(labs_t).where(labs_t.c.id == int(r["id"]))
                        .values(institute=(r["institute"] or "").strip(), running=bool(r["running"])))


def _lab_id(con, name: str) -> int:
    row = con.execute(select(labs_t.c.id).where(func.lower(labs_t.c.name) == name.strip().lower())).first()
    if row is None:
        raise ValueError(f"Unknown lab '{name}'.")
    return row[0]


def strains() -> list[str]:
    with engine().connect() as con:
        return [r[0] for r in con.execute(select(strains_t.c.name).order_by(func.lower(strains_t.c.name)))]


def strains_table() -> pd.DataFrame:
    q = (select(strains_t.c.id, strains_t.c.name, labs_t.c.name.label("lab"))
         .join(labs_t, labs_t.c.id == strains_t.c.lab_id, isouter=True)
         .order_by(func.lower(strains_t.c.name)))
    with engine().connect() as con:
        return pd.read_sql_query(q, con)


def add_strain(name: str, lab: str) -> bool:
    """Returns False if a strain with this name (case-insensitive) already exists."""
    try:
        with engine().begin() as con:
            con.execute(insert(strains_t).values(name=name.strip(), lab_id=_lab_id(con, lab) if lab else None))
    except IntegrityError:
        return False
    return True


def _strain_id(con, name: str, lab: str) -> int:
    row = con.execute(select(strains_t.c.id).where(func.lower(strains_t.c.name) == name.strip().lower())).first()
    if row:
        return row[0]
    return con.execute(insert(strains_t).values(
        name=name.strip(), lab_id=_lab_id(con, lab))).inserted_primary_key[0]


def requests() -> list[dict]:
    """Agendo requests with strain and lab names: id, agendo_id, strain, lab."""
    q = (select(requests_t.c.id, requests_t.c.agendo_id, strains_t.c.name.label("strain"),
                labs_t.c.name.label("lab"))
         .join(strains_t, strains_t.c.id == requests_t.c.strain_id)
         .join(labs_t, labs_t.c.id == requests_t.c.lab_id)
         .order_by(func.lower(func.coalesce(requests_t.c.agendo_id, "")), requests_t.c.id))
    with engine().connect() as con:
        return [dict(r._mapping) for r in con.execute(q)]


def add_request(agendo_id: str, strain: str, lab: str) -> bool:
    """Creates the strain too if it is new. Returns False if this Agendo ID already exists."""
    try:
        with engine().begin() as con:
            con.execute(insert(requests_t).values(
                agendo_id=agendo_id.strip() or None, strain_id=_strain_id(con, strain, lab),
                lab_id=_lab_id(con, lab)))
    except IntegrityError:
        return False
    return True


# --------------------------------------------------------------------------- plans and freezing

def add_plan(request_id: int, animals: list[dict]) -> int:
    """New planned batch for a request, with its animals [{'sex', 'dob' (iso), 'n'}]. Returns batch id."""
    with engine().begin() as con:
        bid = con.execute(insert(batches_t).values(
            request_id=request_id, status="planned")).inserted_primary_key[0]
        con.execute(insert(animals_t), [
            {"batch_id": bid, "sex": a["sex"], "dob": date.fromisoformat(a["dob"]), "n": a["n"]}
            for a in animals])
    return bid


def plans(status: str = "planned") -> list[dict]:
    """Batches in the given status, newest first: batch_id, agendo_id, strain, lab, animals (decoded)."""
    q = (select(batches_t.c.id.label("batch_id"), batches_t.c.created_at,
                func.coalesce(requests_t.c.agendo_id, "").label("agendo_id"),
                strains_t.c.name.label("strain"), labs_t.c.name.label("lab"))
         .join(requests_t, requests_t.c.id == batches_t.c.request_id)
         .join(strains_t, strains_t.c.id == requests_t.c.strain_id)
         .join(labs_t, labs_t.c.id == requests_t.c.lab_id)
         .where(batches_t.c.status == status).order_by(batches_t.c.id.desc()))
    with engine().connect() as con:
        out = [dict(r._mapping) for r in con.execute(q)]
        for b in out:
            rows = con.execute(select(animals_t.c.sex, animals_t.c.dob, animals_t.c.n)
                               .where(animals_t.c.batch_id == b["batch_id"]).order_by(animals_t.c.dob))
            b["animals"] = [{"sex": r.sex, "dob": r.dob.isoformat(), "n": r.n} for r in rows]
    return out


def cancel_plan(batch_id: int) -> None:
    with engine().begin() as con:
        res = con.execute(update(batches_t).where(batches_t.c.id == batch_id, batches_t.c.status == "planned")
                          .values(status="cancelled"))
        if res.rowcount != 1:
            raise ValueError("This plan is no longer open — reload the page.")


def next_straw_no() -> int:
    with engine().connect() as con:
        return (con.execute(select(func.max(straws_t.c.straw_no))).scalar() or 0) + 1


def freeze_batch(batch_id: int, straw_rows: list[dict]) -> int:
    """Record the straws of a planned batch and mark it frozen, all-or-nothing.

    straw_rows: [{'straw_no', 'material', 'n_embryos' (Embryo only), 'shelf', 'position'}, ...]
    Raises ValueError for a batch that is not open or straw numbers that are already used.
    """
    if not straw_rows:
        raise ValueError("Add at least one straw.")
    nums = [int(r["straw_no"]) for r in straw_rows]
    if len(set(nums)) != len(nums):
        raise ValueError("The same straw number appears more than once in this batch.")
    try:
        with engine().begin() as con:
            st = con.execute(select(batches_t.c.status).where(batches_t.c.id == batch_id)
                             .with_for_update()).scalar()
            if st != "planned":
                raise ValueError("This batch is no longer open for freezing — reload the page.")
            used = sorted(r[0] for r in con.execute(
                select(straws_t.c.straw_no).where(straws_t.c.straw_no.in_(nums))))
            if used:
                raise ValueError(f"Straw number(s) already in use (also thawed ones): {_ranges(used)}.")
            con.execute(insert(straws_t), [{
                "batch_id": batch_id, "straw_no": int(r["straw_no"]), "material": r["material"],
                "n_embryos": int(r["n_embryos"]) if r["material"] == "Embryo" else None,
                "shelf": r["shelf"], "position": r["position"]} for r in straw_rows])
            con.execute(update(batches_t).where(batches_t.c.id == batch_id)
                        .values(status="frozen", frozen_at=_utcnow()))
    except IntegrityError as e:  # concurrent session took a number between check and insert
        raise ValueError("A straw number was taken by someone else just now — reload the page.") from e
    return len(straw_rows)


def batch_overview() -> pd.DataFrame:
    """One row per frozen batch with counts derived from its straws (nothing stored twice)."""
    q = (select(batches_t.c.id.label("batch_id"), func.coalesce(requests_t.c.agendo_id, "").label("agendo_id"),
                strains_t.c.name.label("strain"), labs_t.c.name.label("lab"), batches_t.c.frozen_at,
                func.sum(case((straws_t.c.material == "Sperm", 1), else_=0)).label("sperm_straws"),
                func.sum(case((straws_t.c.material == "Embryo", 1), else_=0)).label("embryo_straws"),
                func.coalesce(func.sum(straws_t.c.n_embryos), 0).label("embryo_nr"),
                func.sum(case((straws_t.c.thawed_at.is_(None), 1), else_=0)).label("in_freezer"))
         .join(requests_t, requests_t.c.id == batches_t.c.request_id)
         .join(strains_t, strains_t.c.id == requests_t.c.strain_id)
         .join(labs_t, labs_t.c.id == requests_t.c.lab_id)
         .join(straws_t, straws_t.c.batch_id == batches_t.c.id)
         .where(batches_t.c.status == "frozen")
         .group_by(batches_t.c.id, requests_t.c.agendo_id, strains_t.c.name, labs_t.c.name, batches_t.c.frozen_at)
         .order_by(batches_t.c.id.desc()))
    with engine().connect() as con:
        return pd.read_sql_query(q, con)


# --------------------------------------------------------------------------- inventory

def live_straws(strain_like: str = "", lab_like: str = "", exact_lab: str | None = None) -> pd.DataFrame:
    """Every straw still in the freezer (one row each); case-insensitive substring filters,
    or exact_lab for an exact (case-insensitive) lab match."""
    q = (select(straws_t.c.id.label("straw_id"), straws_t.c.batch_id, straws_t.c.straw_no, straws_t.c.n_embryos,
                strains_t.c.name.label("strain"), straws_t.c.material, labs_t.c.name.label("lab"),
                func.coalesce(requests_t.c.agendo_id, "").label("agendo_id"),
                straws_t.c.shelf, straws_t.c.position)
         .join(batches_t, batches_t.c.id == straws_t.c.batch_id)
         .join(requests_t, requests_t.c.id == batches_t.c.request_id)
         .join(strains_t, strains_t.c.id == requests_t.c.strain_id)
         .join(labs_t, labs_t.c.id == requests_t.c.lab_id)
         .where(straws_t.c.thawed_at.is_(None),
                strains_t.c.name.icontains(strain_like.strip(), autoescape=True),
                labs_t.c.name.icontains(lab_like.strip(), autoescape=True)))
    if exact_lab is not None:
        q = q.where(func.lower(labs_t.c.name) == exact_lab.lower())
    q = q.order_by(func.lower(strains_t.c.name), straws_t.c.material, straws_t.c.shelf,
                   straws_t.c.position, straws_t.c.straw_no)
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
    """Collapse live straws to one row per batch, material and location: ID ranges, count, embryos."""
    rows = []
    for _, g in straws_df.groupby(["batch_id", "material", "shelf", "position"], sort=False):
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
            select(straws_t.c.id, straws_t.c.straw_no, straws_t.c.n_embryos, straws_t.c.thawed_at,
                   straws_t.c.material, strains_t.c.name.label("strain"))
            .join(batches_t, batches_t.c.id == straws_t.c.batch_id)
            .join(requests_t, requests_t.c.id == batches_t.c.request_id)
            .join(strains_t, strains_t.c.id == requests_t.c.strain_id)
            .where(straws_t.c.id.in_(ids)).with_for_update(of=straws_t)).all()
        if len(rows) != len(ids) or any(r.thawed_at is not None for r in rows):
            raise ValueError("Some selected straws are no longer in the freezer — reload the page.")
        res = con.execute(update(straws_t).where(straws_t.c.id.in_(ids), straws_t.c.thawed_at.is_(None))
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
    q = (select(straws_t.c.thawed_at, strains_t.c.name.label("strain"), straws_t.c.material,
                straws_t.c.straw_no, straws_t.c.n_embryos, labs_t.c.name.label("lab"))
         .join(batches_t, batches_t.c.id == straws_t.c.batch_id)
         .join(requests_t, requests_t.c.id == batches_t.c.request_id)
         .join(strains_t, strains_t.c.id == requests_t.c.strain_id)
         .join(labs_t, labs_t.c.id == requests_t.c.lab_id)
         .where(straws_t.c.thawed_at.is_not(None))
         .order_by(straws_t.c.thawed_at.desc(), straws_t.c.id.desc()).limit(limit))
    with engine().connect() as con:
        return pd.read_sql_query(q, con)
