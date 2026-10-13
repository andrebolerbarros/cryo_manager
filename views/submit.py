import streamlit as st

import db

st.title("➕ Submit cryopreserved material")

existing = db.strains()
NEW = "➕ New strain…"
choice = st.selectbox("Strain / line name", [*existing, NEW])
strain = (st.text_input("New strain name") if choice == NEW else choice).strip()

material = st.selectbox("Material", db.MATERIALS)

c1, c2, c3 = st.columns(3)
n_straws = c1.number_input("Number of straws", min_value=1, value=1, step=1)
start_id = c2.number_input("Starting straw ID", min_value=1, value=1, step=1)
end_id = c3.number_input("Ending straw ID", min_value=1, value=int(n_straws), step=1)

n_embryos = None
if material == "Embryo":
    n_embryos = st.number_input(
        "Total number of embryos in this batch", min_value=1, value=30, step=1,
        help="Summed across all straws; feeds the 'total embryos' counter on the search page.",
    )

c4, c5 = st.columns(2)
shelf = c4.text_input("Shelf ID").strip()
position = c5.text_input("Position in shelf", placeholder="e.g. Rack A, Row 2").strip()

if st.button("Save", type="primary"):
    errors = []
    if not strain:
        errors.append("Strain name is required.")
    elif choice == NEW and strain.casefold() in {s.casefold() for s in existing}:
        errors.append(f"'{strain}' already exists (case-insensitive) — pick it from the list.")
    if end_id < start_id:
        errors.append("Ending ID is smaller than starting ID.")
    elif end_id - start_id + 1 != n_straws:
        errors.append(
            f"Number of straws ({n_straws}) does not match the ID range "
            f"{start_id}–{end_id} ({end_id - start_id + 1} straws)."
        )
    if not shelf or not position:
        errors.append("Shelf ID and position are required.")
    if not errors:
        clash = db.overlap(strain, material, int(start_id), int(end_id))
        if not clash.empty:
            errors.append(
                f"Straw IDs overlap an existing {material.lower()} batch for {strain} "
                f"({clash.iloc[0].start_id}–{clash.iloc[0].end_id} at "
                f"{clash.iloc[0].shelf}/{clash.iloc[0].position})."
            )
    if errors:
        for e in errors:
            st.error(e)
    else:
        db.add_batch(strain, material, int(n_straws), int(start_id), int(end_id),
                     int(n_embryos) if n_embryos else None, shelf, position)
        st.success(f"Saved {n_straws} {material.lower()} straw(s) for {strain}.")
