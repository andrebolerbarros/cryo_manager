import pandas as pd
import streamlit as st

import db
import plans

st.title("🐺 Winter is coming")

for msg in st.session_state.pop("flash_winter", []):
    st.success(msg)

# ---------------------------------------------------------------- open requests
st.subheader("Open Requests")
requests = db.requests()
if requests:
    st.dataframe(
        [{"Agendo ID": r["agendo_id"], "Strain": r["strain_id"], "Lab": r["lab"]} for r in requests],
        hide_index=True, use_container_width=True,
    )
else:
    st.caption("No open requests yet.")

with st.expander("Add a new request"):
    n1, n2, n3 = st.columns(3)
    new_agendo = n1.text_input("Agendo ID", key="nr_agendo").strip()
    new_strain = n2.text_input("Strain ID", key="nr_strain").strip()
    known_labs = db.labs()
    new_lab = n3.selectbox("Lab", known_labs, key="nr_lab") if known_labs else ""
    if st.button("Add request"):
        if not (new_agendo and new_strain and new_lab):
            st.error("Agendo ID, strain and lab are all required (labs are added on 'New gang joining!').")
        elif db.add_request(new_agendo, new_strain, new_lab):
            st.session_state["flash_winter"] = [f"Added request {new_agendo} ({new_strain}, {new_lab})."]
            st.rerun()
        else:
            st.error(f"Request '{new_agendo}' already exists (case-insensitive).")

# ---------------------------------------------------------------- planning form
st.subheader("Plan animals")
if not requests:
    st.info("Add a request above first.")
    st.stop()

v = st.session_state.setdefault("winter_v", 0)  # bump to clear the form after a successful save
by_id = {r["agendo_id"]: r for r in requests}

c1, c2, c3 = st.columns(3)
agendo_id = c1.selectbox("Agendo ID", list(by_id), key=f"w_agendo_{v}")
req = by_id[agendo_id]
# keys include the Agendo ID so the greyed-out fields refresh when the selection changes
c2.text_input("Strain ID", value=req["strain_id"], disabled=True, key=f"w_strain_{v}_{agendo_id}")
c3.text_input("Lab", value=req["lab"], disabled=True, key=f"w_lab_{v}_{agendo_id}")

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
    animals, errors = plans.rows_to_animals(rows)
    if errors:
        for e in errors:
            st.error(e)
    else:
        db.add_plan(req["agendo_id"], req["strain_id"], req["lab"], animals)
        st.session_state["flash_winter"] = [
            f"Planned {req['strain_id']} ({req['lab']}, {req['agendo_id']}): "
            f"{plans.format_animals(animals)}"]
        st.session_state["winter_v"] = v + 1
        st.rerun()

# ---------------------------------------------------------------- planned entries (one table)
st.subheader("Planned entries")
saved = db.plans()
if not saved:
    st.caption("Nothing planned yet.")
else:
    st.caption("Age = whole weeks since birth, calculated against today; entries with the same Agendo ID, "
               "strain and lab are combined, and animals of the same sex and number of weeks are merged.")
    groups: dict[tuple, dict] = {}
    for r in saved:  # newest first
        key = tuple(r[k].strip().casefold() for k in ("agendo_id", "strain_id", "lab"))
        g = groups.setdefault(key, {**r, "animals": []})
        g["animals"] += r["animals"]
    table = []
    for g in groups.values():
        for row in plans.merge_by_weeks(g["animals"]):
            table.append({
                "Strain ID": g["strain_id"], "Lab": g["lab"] or "—", "Agendo request ID": g["agendo_id"],
                "Sex × age": plans.format_sex_age(row), "DOB": plans.format_dobs(row),
            })
    st.dataframe(table, hide_index=True, use_container_width=True)
