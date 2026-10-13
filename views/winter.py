import pandas as pd
import streamlit as st

import db
import plans

st.title("🐺 Winter is coming")

for msg in st.session_state.pop("flash_winter", []):
    st.success(msg)

v = st.session_state.setdefault("winter_v", 0)  # bump to clear the form after a successful save

c1, c2 = st.columns(2)
agendo_id = c1.text_input("Agendo ID", key=f"w_agendo_{v}").strip()
strain_id = c2.text_input("Strain ID", key=f"w_strain_{v}").strip()

st.markdown("**Animals** — one row per sex × DOB (“+” top right adds a row)")
empty = pd.DataFrame({
    "Sex": pd.Series(dtype="object"),
    "DOB": pd.Series(dtype="datetime64[ns]"),
    "Number": pd.Series(dtype="int64"),
})
rows = st.data_editor(
    empty, key=f"w_rows_{v}", num_rows="dynamic", hide_index=True, use_container_width=True,
    column_config={
        "Sex": st.column_config.SelectboxColumn("Sex", options=list(plans.SEXES), required=True),
        "DOB": st.column_config.DateColumn("DOB", format="DD-MM-YYYY", required=True),
        "Number": st.column_config.NumberColumn("Number", min_value=1, step=1, default=1, required=True),
    },
)

if st.button("Let's get planning!", type="primary"):
    errors = []
    if not agendo_id:
        errors.append("Agendo ID is required.")
    if not strain_id:
        errors.append("Strain ID is required.")
    animals, problems = plans.rows_to_animals(rows)
    errors += problems
    if errors:
        for e in errors:
            st.error(e)
    else:
        db.add_plan(agendo_id, strain_id, animals)
        st.session_state["flash_winter"] = [
            f"Planned {strain_id} ({agendo_id}): {plans.format_animals(animals)}"]
        st.session_state["winter_v"] = v + 1
        st.rerun()

st.subheader("Planned entries")
saved = db.plans()
if not saved:
    st.caption("Nothing planned yet.")
else:
    st.caption("Age in weeks is calculated against today's date.")
    st.dataframe(
        [{"Strain ID": r["strain_id"], "Agendo ID": r["agendo_id"],
          "Animals (sex × DOB, age)": plans.format_animals(r["animals"])} for r in saved],
        hide_index=True, use_container_width=True,
    )
