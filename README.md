# Mouse Cryo Manager

Streamlit dashboard for tracking cryopreserved mouse sperm and embryo straws.

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

- Data lives in `cryo.db` (SQLite, git-ignored). A 5-line toy dataset is loaded on first run;
  delete `cryo.db` to reset.
- **Submit**: one row = one contiguous block of straw IDs in one shelf position.
- **Search**: substring match on line name; totals shown per line.
