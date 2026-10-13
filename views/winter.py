import pandas as pd
import streamlit as st

import db
import plans

st.title("🐺 Winter is coming")

for msg in st.session_state.pop("flash_winter", []):
    st.success(msg)

v = st.session_state.setdefault("winter_v", 0)  # bump to clear the form after a successful save

c1, c2, c3 = st.columns(3)
agendo_id = c1.text_input("Agendo ID", key=f"w_agendo_{v}").strip()
strain_id = c2.text_input("Strain ID", key=f"w_strain_{v}").strip()
all_labs = db.labs()
if all_labs:
    lab = c3.selectbox("Lab", all_labs, key=f"w_lab_{v}")
else:
    lab = ""
    c3.warning("No labs yet — add one on 'New gang joining!'.")

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
    if not lab:
        errors.append("Lab is required (add it on 'New gang joining!').")
    animals, problems = plans.rows_to_animals(rows)
    errors += problems
    if errors:
        for e in errors:
            st.error(e)
    else:
        db.add_plan(agendo_id, strain_id, lab, animals)
        st.session_state["flash_winter"] = [
            f"Planned {strain_id} ({lab}, {agendo_id}): {plans.format_animals(animals)}"]
        st.session_state["winter_v"] = v + 1
        st.rerun()

st.subheader("Planned entries")
saved = db.plans()
if not saved:
    st.caption("Nothing planned yet.")
else:
    st.caption("Age = whole weeks since birth, calculated against today; animals of the same sex "
               "and the same number of weeks are merged.")
    # entries with the same Agendo request ID + strain + lab share one section and one table
    sections: dict[tuple, dict] = {}
    for r in saved:  # newest first, so a section shows the newest entry's spelling
        key = tuple(r[k].strip().casefold() for k in ("agendo_id", "strain_id", "lab"))
        sec = sections.setdefault(key, {**r, "animals": []})
        sec["animals"] += r["animals"]
    for r in sections.values():
        st.markdown(f"### {r['strain_id']}\n"
                    f"- **Lab:** {r['lab'] or '—'}\n"
                    f"- **Agendo request ID:** {r['agendo_id']}")
        st.dataframe(
            [{"Sex × age": plans.format_sex_age(g), "DOB": plans.format_dobs(g)}
             for g in plans.merge_by_weeks(r["animals"])],
            hide_index=True, use_container_width=True,
        )
