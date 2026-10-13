import streamlit as st

import db

st.set_page_config(page_title="Mouse Cryo Manager", page_icon="🧊")
db.seed_if_empty()  # toy data on first run only

st.navigation([
    st.Page("views/home.py", title="Home", icon="🧊", default=True),
    st.Page("views/submit.py", title="Submit", icon="➕"),
    st.Page("views/search.py", title="Search", icon="🔎"),
]).run()
