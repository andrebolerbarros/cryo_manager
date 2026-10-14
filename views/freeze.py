import pandas as pd
import streamlit as st

import db
import plans

st.title("❄️ Let's get freezing")

for msg in st.session_state.pop("flash_freeze", []):
    st.success(msg)

COLS = ["straw_no", "material", "n_embryos", "shelf", "position"]


def empty_rows() -> pd.DataFrame:
    return pd.DataFrame({
        "straw_no": pd.Series(dtype="int64"), "material": pd.Series(dtype="object"),
        "n_embryos": pd.Series(dtype="float64"), "shelf": pd.Series(dtype="object"),
        "position": pd.Series(dtype="object"),
    })


# ---------------------------------------------------------------- which planned batch
planned = db.plans("planned")
if not planned:
    st.info("Nothing is planned yet — plan the animals on the 'Winter is coming' page first.")
    st.stop()

labels = {
    b["batch_id"]: f"{b['agendo_id'] or 'no Agendo ID'} · {b['strain']} · {b['lab']}"
                   f" · {plans.format_animals(b['animals']) or 'no animals listed'}"
    for b in planned
}
batch_id = st.selectbox("Planned batch", list(labels), format_func=labels.get)

# the straw table is kept per planned batch, so switching batches does not mix them up
key = f"freeze_rows_{batch_id}"
if key not in st.session_state:
    st.session_state[key] = empty_rows()
rows: pd.DataFrame = st.session_state[key]

# ---------------------------------------------------------------- add a block of straws
st.subheader("Add straws")
st.caption("A batch can hold sperm and embryo straws, in several places. Add one block at a time, "
           "then correct individual straws (e.g. the number of embryos in each) in the table below.")

c1, c2, c3 = st.columns(3)
material = c1.selectbox("Material", db.MATERIALS)
n_new = c2.number_input("Number of straws", min_value=1, value=1, step=1)
used_here = int(rows.straw_no.max()) + 1 if len(rows) else 0
default_start = max(db.next_straw_no(), used_here)
start_no = c3.number_input("Starting straw ID", min_value=1, value=default_start, step=1,
                           help="Straw IDs are global: unique across all strains and materials.")

c4, c5, c6 = st.columns(3)
shelf = c4.text_input("Shelf ID").strip()
position = c5.text_input("Position in shelf", placeholder="e.g. Rack A, Row 2").strip()
per_straw = None
if material == "Embryo":
    per_straw = c6.number_input("Embryos per straw", min_value=0, value=10, step=1,
                                help="Fills every new straw; edit single straws in the table below.")

if st.button("Add to table"):
    if not shelf or not position:
        st.error("Shelf ID and position are required.")
    else:
        new = pd.DataFrame({
            "straw_no": range(int(start_no), int(start_no) + int(n_new)),
            "material": material,
            "n_embryos": float(per_straw) if per_straw is not None else None,
            "shelf": shelf, "position": position,
        })
        st.session_state[key] = pd.concat([rows, new], ignore_index=True)
        st.rerun()

# ---------------------------------------------------------------- straw table
st.subheader("Straws of this batch")
if rows.empty:
    st.caption("No straws added yet.")
else:
    edited = st.data_editor(
        rows, key=f"freeze_editor_{batch_id}_{len(rows)}", num_rows="dynamic", hide_index=True,
        use_container_width=True,
        column_config={
            "straw_no": st.column_config.NumberColumn("Straw ID", min_value=1, step=1, required=True),
            "material": st.column_config.SelectboxColumn("Material", options=list(db.MATERIALS), required=True),
            "n_embryos": st.column_config.NumberColumn("Embryos", min_value=0, step=1,
                                                       help="Embryo straws only; leave empty for sperm."),
            "shelf": st.column_config.TextColumn("Shelf", required=True),
            "position": st.column_config.TextColumn("Position", required=True),
        },
    )
    m1, m2, m3 = st.columns(3)
    m1.metric("Sperm straws", int((edited.material == "Sperm").sum()))
    m2.metric("Embryo straws", int((edited.material == "Embryo").sum()))
    m3.metric("Embryos", int(edited.loc[edited.material == "Embryo", "n_embryos"].fillna(0).sum()))

    if st.button("Save", type="primary"):
        errors, out = [], []
        for i, r in enumerate(edited.itertuples(index=False), start=1):
            if pd.isna(r.straw_no) or pd.isna(r.material) or not str(r.shelf or "").strip() \
                    or not str(r.position or "").strip():
                errors.append(f"Row {i}: straw ID, material, shelf and position are required.")
            elif r.material == "Embryo" and pd.isna(r.n_embryos):
                errors.append(f"Row {i} (straw {int(r.straw_no)}): number of embryos is required for embryo straws.")
            else:
                out.append({"straw_no": int(r.straw_no), "material": r.material,
                            "n_embryos": None if pd.isna(r.n_embryos) else int(r.n_embryos),
                            "shelf": str(r.shelf).strip(), "position": str(r.position).strip()})
        if not errors and not out:
            errors.append("Add at least one straw.")
        if not errors:
            try:
                n = db.freeze_batch(int(batch_id), out)
            except ValueError as e:
                errors.append(str(e))
        if errors:
            for e in errors:
                st.error(e)
        else:
            del st.session_state[key]
            st.session_state["flash_freeze"] = [f"Saved {n} straw(s) for {labels[batch_id]}."]
            st.rerun()

# ---------------------------------------------------------------- frozen batches (derived counts)
with st.expander("Frozen batches"):
    ov = db.batch_overview()
    if ov.empty:
        st.caption("Nothing frozen yet.")
    else:
        st.dataframe(
            ov.drop(columns=["batch_id"]).rename(columns={
                "agendo_id": "Agendo ID", "strain": "Strain", "lab": "Lab", "frozen_at": "Frozen",
                "sperm_straws": "Sperm straws", "embryo_straws": "Embryo straws",
                "embryo_nr": "Embryos", "in_freezer": "Straws in freezer"}),
            hide_index=True, use_container_width=True)
