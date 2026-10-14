# Mouse Cryo Manager

Streamlit dashboard for tracking cryopreserved mouse sperm and embryo straws.

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Database

Storage goes through SQLAlchemy, so the same code runs on **PostgreSQL** (shared/server use) or
**SQLite** (local development). The database is chosen by a URL, looked up in this order:

1. environment variable `CRYO_DATABASE_URL` (or `DATABASE_URL`)
2. Streamlit secret `database_url` in `.streamlit/secrets.toml` (see `.streamlit/secrets.toml.example`)
3. fallback: local SQLite file `cryo.db` (git-ignored)

```bash
export CRYO_DATABASE_URL="postgresql+psycopg2://cryo_app:PASSWORD@db-host:5432/cryo"
streamlit run streamlit_app.py
```

Tables are created on first start and a toy dataset is loaded into an empty database (batches, straws,
labs, requests, plans). To start from the toy data again, empty the tables or use a new database/SQLite file.

**Moving an existing `cryo.db` to the server database** (keeps IDs and thaw history, refuses a
non-empty target unless `--force`, checks row counts at the end):

```bash
python migrate_sqlite_to_sql.py --source cryo.db --target postgresql+psycopg2://cryo_app:PASSWORD@db-host:5432/cryo
```

Notes: lab names and Agendo IDs are unique case-insensitively (functional index on `lower(...)`);
thawing locks the selected straws (`SELECT ... FOR UPDATE`) so two sessions cannot thaw the same straw.
Do not commit credentials: `secrets.toml` is git-ignored.

## Pages
- **Let's get freezing**: one row = one contiguous block of straw IDs in one shelf position.
- **Let's warm up!**: tick individual straws and press *warm it up!*; thawed straws leave the inventory
  (kept in the DB with a timestamp, so straw IDs are never reused).
- **Search**: substring match on line name; totals shown per line.
- **Winter is coming**: *Open Requests* (Agendo ID → strain + lab; a toy list is seeded) and a form where
  picking an Agendo ID fills strain and lab, then Sex / DOB / Number rows. All planned animals show in one
  table with age in whole weeks; entries for the same request are combined.
- **Look at my kingdom!**: pick a lab; table of embryos, embryo straws and sperm straws per strain.
- **New gang joining!**: add labs; they feed the Lab dropdown.
