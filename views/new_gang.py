import streamlit as st

import db

st.title("🤝 New gang joining!")
st.caption("Labs and strains added here become the options in \"Let's get freezing\" and "
           "\"Winter is coming\".")

for msg in st.session_state.pop("flash_gang", []):
    st.success(msg)

# ---------------------------------------------------------------- labs
st.subheader("Labs")
c1, c2, c3 = st.columns([2, 2, 1])
name = c1.text_input("Lab name").strip()
institute = c2.text_input("Institute").strip()
running = c3.checkbox("Running", value=True, help="Untick for a lab that has closed.")
if st.button("Add lab", type="primary"):
    if not name:
        st.error("Lab name is required.")
    elif db.add_lab(name, institute, running):
        st.session_state["flash_gang"] = [f"Added '{name}'."]
        st.rerun()
    else:
        st.error(f"'{name}' already exists (case-insensitive).")

labs = db.labs_table()
if labs.empty:
    st.caption("None yet.")
else:
    st.caption("Edit the institute or tick/untick Running, then press Save. Closed labs stay in the "
               "database (their straws and requests are kept) but leave the dropdowns.")
    edited = st.data_editor(
        labs, key="labs_editor", hide_index=True, use_container_width=True,
        disabled=["id", "name"], column_order=["name", "institute", "running"],
        column_config={"name": "Lab", "institute": "Institute",
                       "running": st.column_config.CheckboxColumn("Running")},
    )
    if st.button("Save labs"):
        db.update_labs(edited[["id", "institute", "running"]].to_dict("records"))
        st.session_state["flash_gang"] = ["Labs updated."]
        st.rerun()

# ---------------------------------------------------------------- strains
st.subheader("Strains")
running_labs = db.labs()
s1, s2 = st.columns(2)
strain_name = s1.text_input("Strain name").strip()
strain_lab = s2.selectbox("Associated lab", running_labs) if running_labs else ""
if st.button("Add strain"):
    if not strain_name:
        st.error("Strain name is required.")
    elif db.add_strain(strain_name, strain_lab):
        st.session_state["flash_gang"] = [f"Added strain '{strain_name}'."]
        st.rerun()
    else:
        st.error(f"'{strain_name}' already exists (case-insensitive).")

strains = db.strains_table()
if strains.empty:
    st.caption("None yet.")
else:
    st.dataframe(strains[["name", "lab"]].rename(columns={"name": "Strain", "lab": "Lab"}),
                 hide_index=True, use_container_width=True)
