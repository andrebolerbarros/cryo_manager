"""Copy an existing SQLite cryo.db into another SQL database (e.g. PostgreSQL), keeping all IDs.

    python migrate_sqlite_to_sql.py --target postgresql+psycopg2://user:pass@host:5432/cryo
    python migrate_sqlite_to_sql.py --source path/to/cryo.db --target <url> [--force]

The source file is never modified: it is copied to a temporary file first, and if it is in the
previous table layout it is upgraded there (see db.create_schema) before copying.
The target must be empty unless --force is given, which empties it first. Row counts are compared
at the end; a mismatch exits with an error.
"""
import argparse
import shutil
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy import insert, select, text

import db

ORDER = [db.labs_t, db.strains_t, db.requests_t, db.batches_t, db.animals_t, db.straws_t]  # parents first
DATETIME_COLS = {"created_at", "frozen_at", "thawed_at"}


def _to_dt(v):
    if v is None or isinstance(v, datetime):
        return v
    return datetime.fromisoformat(str(v))


def _to_date(v):
    if v is None or isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", default=str(Path(__file__).parent / "cryo.db"),
                    help="SQLite file to read (default: cryo.db next to db.py)")
    ap.add_argument("--target", required=True, help="SQLAlchemy URL of the destination database")
    ap.add_argument("--force", action="store_true", help="empty the target tables first")
    args = ap.parse_args()

    if not Path(args.source).is_file():
        print(f"ERROR: source file not found: {args.source}")
        return 1

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp) / "source.db"
        shutil.copyfile(args.source, work)
        src = db.make_engine(f"sqlite:///{work.as_posix()}")
        dst = db.make_engine(args.target)

        db.create_schema(src)   # upgrades the temporary copy if it is in the previous layout
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
                    if t is db.animals_t:
                        row["dob"] = _to_date(row["dob"])
                    rows.append(row)
                if rows:
                    d.execute(insert(t), rows)
                print(f"{t.name:14s} {len(rows):6d} rows copied")

            if dst.dialect.name == "postgresql":  # explicit IDs were inserted: move the sequences past them
                for t in ORDER:
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
        src.dispose()
        dst.dispose()
    if bad:
        print("ERROR: row count mismatch (table, source, target):", bad)
        return 1
    print("Migration complete, row counts match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
