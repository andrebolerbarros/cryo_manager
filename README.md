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
- **Winter is coming**: plan entries (Agendo ID, Strain ID, comment). The comment must give number of
  females/males + DOB per line, e.g. `3 females DOB 2026-01-15`; dates are read day-first.
- **Look at my kingdom!**: pick a lab; table of embryos, embryo straws and sperm straws per strain.
- **New gang joining!**: add labs; they feed the Lab dropdown.
