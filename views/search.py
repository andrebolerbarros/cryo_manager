import streamlit as st

import db

st.title("🔎 Search inventory")

q = st.text_input("Line name", placeholder="e.g. GDF15, FXR, B6J")
if not q.strip():
    st.caption(f"Known lines: {', '.join(db.strains()) or '— none yet —'}")
    st.stop()

df = db.search(q)
if df.empty:
    st.warning(f"No line matches '{q}'.")
    st.stop()

COLS = {"start_id": "From", "end_id": "To", "n_straws": "Straws", "shelf": "Shelf", "position": "Position",
        "lab": "Lab", "agendo_id": "Agendo ID"}

for strain, g in df.groupby("strain", sort=False):
    st.subheader(strain)
    sp, em = g[g.material == "Sperm"], g[g.material == "Embryo"]
    m1, m2, m3 = st.columns(3)
    m1.metric("Sperm straws", int(sp.n_straws.sum()))
    m2.metric("Embryo straws", int(em.n_straws.sum()))
    m3.metric("Cryopreserved embryos", int(em.n_embryos.sum()))

    for label, part in (("Sperm", sp), ("Embryo", em)):
        st.markdown(f"**{label}**")
        if part.empty:
            st.caption("None stored.")
        else:
            cols = [*COLS, "n_embryos"] if label == "Embryo" else list(COLS)
            st.dataframe(
                part[cols].rename(columns={**COLS, "n_embryos": "Embryos"}),
                hide_index=True, use_container_width=True,
            )
    st.divider()
