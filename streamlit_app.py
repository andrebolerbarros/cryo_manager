import streamlit as st

import db

st.set_page_config(page_title="Mouse Cryo Manager", page_icon="🧊")
db.seed_if_empty()  # toy data on first run only

st.navigation([
    st.Page("views/home.py", title="Home", icon="🧊", default=True),
    st.Page("views/freeze.py", title="Let's get freezing", icon="❄️", url_path="freeze"),
    st.Page("views/warm.py", title="Let's warm up!", icon="🔥", url_path="warm"),
    st.Page("views/search.py", title="Search", icon="🔎"),
    st.Page("views/new_lab.py", title="New Lab", icon="🏷️", url_path="new-lab"),
]).run()
