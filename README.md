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

Tables are created on first start and a toy dataset is loaded into an empty database. To start from
the toy data again, use a new database/SQLite file.

### Tables

| Table | One row is | Main columns |
|---|---|---|
| `labs` | a lab | name, institute, `running` (closed labs leave the dropdowns but are never deleted) |
| `strains` | a strain | name, associated lab |
| `requests` | an Agendo request | internal id, `agendo_id` (unique, can be corrected), strain, lab |
| `batches` | one freezing session of a request | request, status `planned` / `frozen` / `cancelled`, dates |
| `batch_animals` | animals of a batch | sex, DOB, number |
| `straws` | one physical straw | global straw number, material, embryos, shelf, position, `thawed_at` |

Sperm straws, embryo straws and the embryo total of a batch are derived from its straws, not stored
twice (see "Frozen batches" on the freezing page). Straw numbers are global and never reused,
including thawed ones.

### Upgrading and moving data

A database in the previous layout (strain, lab and location on `batches`, a `plans` table) is
upgraded automatically on first start: the old tables are kept as `legacy_*` and the data is copied
into the new tables. Straw numbers were only unique per strain and material before, so they are
**renumbered 1..N** to make them global; check that against the physical labels if the data is real.

**Moving an existing `cryo.db` to the server database** (keeps IDs and thaw history; the source file
is not modified; refuses a non-empty target unless `--force`; checks row counts at the end):

```bash
python migrate_sqlite_to_sql.py --source cryo.db --target postgresql+psycopg2://cryo_app:PASSWORD@db-host:5432/cryo
```

Notes: lab names, strain names and Agendo IDs are unique case-insensitively (functional index on
`lower(...)`); freezing and thawing lock the rows involved (`SELECT ... FOR UPDATE`) so two sessions
cannot take the same straw. Do not commit credentials: `secrets.toml` is git-ignored.

## Pages
- **Winter is coming**: requests (Agendo ID, strain, lab), then *Plan animals*: pick a request and enter
  Sex / DOB / Number rows. This creates a **planned batch**; planned batches show with age in whole
  weeks and can be cancelled.
- **Let's get freezing**: pick a planned batch, add blocks of straws (material, how many, first global
  straw ID, shelf, position, embryos per straw), correct single straws in the table (embryos are
  recorded per straw), and save: the batch becomes `frozen`. A batch can mix sperm and embryo straws
  and several locations.
- **Let's warm up!**: tick individual straws and press *warm it up!*; thawed straws leave the inventory
  (kept in the database with a timestamp, so straw IDs are never reused).
- **Search**: substring match on line name; totals shown per line.
- **Look at my kingdom!**: pick a lab; table of embryos, embryo straws and sperm straws per strain.
- **New gang joining!**: add and edit labs (institute, running) and strains (with their lab).
