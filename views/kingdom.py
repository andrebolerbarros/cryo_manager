import streamlit as st

import db

st.title("👑 Look at my kingdom!")

all_labs = db.labs()
if not all_labs:
    st.info("No labs yet — add one on the 'New gang joining!' page.")
    st.stop()

lab = st.selectbox("Lab", all_labs)

df = db.live_straws(exact_lab=lab)
if df.empty:
    st.warning(f"{lab} has no straws in the freezer.")
    st.stop()

df["is_embryo"] = df.material == "Embryo"
df["is_sperm"] = df.material == "Sperm"
df["embryos"] = df.n_embryos.fillna(0)

st.subheader(lab)
t = (df.groupby("strain", sort=True)
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
