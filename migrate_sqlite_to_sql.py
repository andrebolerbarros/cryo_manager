"""Copy an existing SQLite cryo.db into another SQL database (e.g. PostgreSQL), keeping all IDs.

    python migrate_sqlite_to_sql.py --target postgresql+psycopg2://user:pass@host:5432/cryo
    python migrate_sqlite_to_sql.py --source path/to/cryo.db --target <url> [--force]

The target must be empty (no batches/straws/requests/plans/labs) unless --force is given, which
truncates it first. Row counts are compared at the end; a mismatch exits with an error.
"""
import argparse
import sys
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import insert, select, text

import db

ORDER = [db.labs_t, db.requests_t, db.batches, db.straws, db.plans_t]  # parents before children
DATETIME_COLS = {"created_at", "thawed_at"}


def _to_dt(v):
    if v is None or isinstance(v, datetime):
        return v
    return datetime.fromisoformat(str(v))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(db.DEFAULT_URL.removeprefix("sqlite:///")),
                    help="SQLite file to read (default: cryo.db next to db.py)")
    ap.add_argument("--target", required=True, help="SQLAlchemy URL of the destination database")
    ap.add_argument("--force", action="store_true", help="empty the target tables first")
    args = ap.parse_args()

    src = db.make_engine(f"sqlite:///{args.source}")
    dst = db.make_engine(args.target)
    if src.url == dst.url:
        print("ERROR: source and target are the same database.")
        return 1

    # source: make sure legacy files are on the current schema before reading
    db.create_schema(src)
    db.create_schema(dst)

    with dst.begin() as con:
        existing = {t.name: con.execute(select(sa.func.count()).select_from(t)).scalar() for t in ORDER}
        if any(existing.values()):
            if not args.force:
                print(f"ERROR: target is not empty ({existing}). Use --force to overwrite.")
                return 1
            for t in reversed(ORDER):
                con.execute(t.delete())

    with src.connect() as s, dst.begin() as d:
        for t in ORDER:
            rows = []
            for r in s.execute(select(t)).mappings():
                row = dict(r)
                for c in DATETIME_COLS & set(row):
                    row[c] = _to_dt(row[c])
                rows.append(row)
            if rows:
                d.execute(insert(t), rows)
            print(f"{t.name:10s} {len(rows):6d} rows copied")

        if dst.dialect.name == "postgresql":  # explicit IDs were inserted: move the sequences past them
            for t in (db.batches, db.straws, db.plans_t):
                d.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{t.name}', 'id'),"
                    f" COALESCE((SELECT MAX(id) FROM {t.name}), 1),"
                    f" (SELECT MAX(id) FROM {t.name}) IS NOT NULL)"))

    bad = []
    with src.connect() as s, dst.connect() as d:
        for t in ORDER:
            n_s = s.execute(select(sa.func.count()).select_from(t)).scalar()
            n_d = d.execute(select(sa.func.count()).select_from(t)).scalar()
            if n_s != n_d:
                bad.append((t.name, n_s, n_d))
    if bad:
        print("ERROR: row count mismatch (table, source, target):", bad)
        return 1
    print("Migration complete, row counts match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
