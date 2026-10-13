import streamlit as st

import db

st.title("👑 Look at my kingdom!")

q = st.text_input("Lab name", placeholder="e.g. Silva, Costa")
if not q.strip():
    st.caption(f"Known labs: {', '.join(db.labs()) or '— none yet —'}")
    st.stop()

df = db.live_straws(lab_like=q)
if df.empty:
    st.warning(f"No straws in the freezer for a lab matching '{q}'.")
    st.stop()

df["is_embryo"] = df.material == "Embryo"
df["is_sperm"] = df.material == "Sperm"
df["embryos"] = df.n_embryos.fillna(0)

for lab, g in df.groupby("lab", sort=True):
    st.subheader(lab or "(no lab)")
    t = (g.groupby("strain", sort=True)
          .agg(embryos=("embryos", "sum"), embryo_straws=("is_embryo", "sum"),
               sperm_straws=("is_sperm", "sum"))
          .astype(int))
    t.loc["TOTAL"] = t.sum()
    st.dataframe(
        t.reset_index().rename(columns={
            "strain": "Strain", "embryos": "Embryos", "embryo_straws": "Embryo straws",
            "sperm_straws": "Sperm straws"}),
        hide_index=True, use_container_width=True,
    )
