import pandas as pd
import streamlit as st

import db
import plans

st.title("🐺 Winter is coming")

for msg in st.session_state.pop("flash_winter", []):
    st.success(msg)

# ---------------------------------------------------------------- requests
st.subheader("Requests")
requests = db.requests()
if requests:
    st.dataframe(
        [{"Agendo ID": r["agendo_id"] or "—", "Strain": r["strain"], "Lab": r["lab"]} for r in requests],
        hide_index=True, use_container_width=True,
    )
else:
    st.caption("No requests yet.")

with st.expander("Add a new request"):
    NEW = "➕ New strain…"
    known_strains = db.strains()
    strain_lab = dict(zip(db.strains_table().name, db.strains_table().lab))
    running_labs = db.labs()

    n1, n2, n3 = st.columns(3)
    new_agendo = n1.text_input("Agendo ID", key="nr_agendo").strip()
    choice = n2.selectbox("Strain", [*known_strains, NEW], key="nr_strain")
    new_strain = (st.text_input("New strain name", key="nr_strain_new") if choice == NEW else choice).strip()
    default_lab = strain_lab.get(choice)
    new_lab = n3.selectbox(
        "Lab", running_labs, key=f"nr_lab_{choice}",
        index=running_labs.index(default_lab) if default_lab in running_labs else 0,
    ) if running_labs else ""
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
by_id = {r["id"]: r for r in requests}

c1, c2, c3 = st.columns(3)
req_id = c1.selectbox("Request", list(by_id), key=f"w_req_{v}",
                      format_func=lambda i: by_id[i]["agendo_id"] or f"(no Agendo ID, #{i})")
req = by_id[req_id]
# keys include the request id so the greyed-out fields refresh when the selection changes
c2.text_input("Strain", value=req["strain"], disabled=True, key=f"w_strain_{v}_{req_id}")
c3.text_input("Lab", value=req["lab"], disabled=True, key=f"w_lab_{v}_{req_id}")

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
        db.add_plan(req["id"], animals)
        st.session_state["flash_winter"] = [
            f"Planned {req['strain']} ({req['lab']}, {req['agendo_id'] or 'no Agendo ID'}): "
            f"{plans.format_animals(animals)}"]
        st.session_state["winter_v"] = v + 1
        st.rerun()

# ---------------------------------------------------------------- planned batches
st.subheader("Planned batches")
saved = db.plans("planned")
if not saved:
    st.caption("Nothing planned yet.")
else:
    st.caption("Age = whole weeks since birth, calculated against today; animals of the same sex and "
               "number of weeks are merged. A planned batch is frozen on the \"Let's get freezing\" page.")
    table = []
    for b in saved:
        for row in plans.merge_by_weeks(b["animals"]):
            table.append({
                "Strain": b["strain"], "Lab": b["lab"] or "—", "Agendo ID": b["agendo_id"] or "—",
                "Sex × age": plans.format_sex_age(row), "DOB": plans.format_dobs(row),
            })
    st.dataframe(table, hide_index=True, use_container_width=True)

    with st.expander("Cancel a plan"):
        opts = {b["batch_id"]: f"{b['agendo_id'] or 'no Agendo ID'} · {b['strain']} · "
                               f"{plans.format_animals(b['animals'])}" for b in saved}
        to_cancel = st.selectbox("Plan", list(opts), format_func=opts.get, key="cancel_pick")
        if st.button("Cancel this plan"):
            try:
                db.cancel_plan(int(to_cancel))
            except ValueError as e:
                st.error(str(e))
            else:
                st.session_state["flash_winter"] = [f"Cancelled plan: {opts[to_cancel]}."]
                st.rerun()
