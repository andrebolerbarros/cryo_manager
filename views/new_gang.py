import streamlit as st

import db

st.title("🤝 New gang joining!")
st.caption("Labs added here become the options in the Lab dropdown of \"Let's get freezing\".")

name = st.text_input("Lab name").strip()
if st.button("Add lab", type="primary"):
    if not name:
        st.error("Lab name is required.")
    elif db.add_lab(name):
        st.success(f"Added '{name}'.")
    else:
        st.error(f"'{name}' already exists (case-insensitive).")

st.subheader("Current gangs (labs)")
current = db.labs()
if current:
    st.dataframe({"Lab": current}, hide_index=True, use_container_width=True)
else:
    st.caption("None yet.")
