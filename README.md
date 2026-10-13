# Mouse Cryo Manager

Streamlit dashboard for tracking cryopreserved mouse sperm and embryo straws.

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

- Data lives in `cryo.db` (SQLite, git-ignored). A 5-line toy dataset is loaded on first run;
  delete `cryo.db` to reset.
- **Let's get freezing**: one row = one contiguous block of straw IDs in one shelf position.
- **Let's warm up!**: tick individual straws and press *warm it up!*; thawed straws leave the inventory
  (kept in the DB with a timestamp, so straw IDs are never reused).
- **Search**: substring match on line name; totals shown per line.
- **Look at my kingdom!**: per-lab table of embryos, embryo straws and sperm straws per strain.
- **New gang joining!**: add labs; they feed the Lab dropdown.
