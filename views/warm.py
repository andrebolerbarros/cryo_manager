import streamlit as st

import db

st.title("🔥 Let's warm up!")

for msg in st.session_state.pop("flash", []):
    st.success(msg)

q = st.text_input("Line name", placeholder="e.g. GDF15, B6J")
if not q.strip():
    st.caption(f"Known lines: {', '.join(db.strains()) or '— none yet —'}")
    st.stop()

df = db.search(q)
if df.empty:
    st.warning(f"No line matches '{q}'.")
    st.stop()

WIDTHS = [2, 1.5, 2.5, 2, 1.3, 1.6, 2]
selection: dict[int, int] = {}

for strain, g in df.groupby("strain", sort=False):
    st.subheader(strain)
    for material in db.MATERIALS:
        part = g[g.material == material]
        st.markdown(f"**{material}**")
        if part.empty:
            st.caption("None stored.")
            continue
        for col, h in zip(st.columns(WIDTHS),
                          ["Straw IDs", "Shelf", "Position", "Lab", "Straws", "Embryos", "Straws to thaw"]):
            col.caption(h)
        for r in part.itertuples():
            c = st.columns(WIDTHS)
            c[0].write(f"{r.start_id}–{r.end_id}" if r.n_straws > 1 else f"{r.start_id}")
            c[1].write(r.shelf)
            c[2].write(r.position)
            c[3].write(r.lab or "—")
            c[4].write(str(r.n_straws))
            c[5].write("—" if material == "Sperm" or r.n_embryos != r.n_embryos else str(int(r.n_embryos)))
            # key carries n_straws so the widget resets after a thaw changes the batch
            k = c[6].selectbox("Straws to thaw", range(r.n_straws + 1),
                               key=f"thaw_{r.id}_{r.n_straws}", label_visibility="collapsed")
            if k:
                selection[r.id] = k
    st.divider()

if st.button("warm it up!", type="primary"):
    if not selection:
        st.info("Nothing selected — pick a number of straws in the last column.")
    else:
        try:
            done = db.thaw_many(selection)
        except ValueError as e:
            st.error(str(e))
        else:
            st.session_state["flash"] = [
                f"{d['strain']} · {d['material']}: thawed {d['straws']} straw(s), IDs "
                f"{d['ids'][0]}–{d['ids'][1]}"
                + (f" ({d['embryos']} embryos)." if d["embryos"] is not None else ".")
                for d in done
            ]
            st.rerun()  # redraw the table with the updated inventory

with st.expander("Recent thaws"):
    log = db.recent_thaws()
    if log.empty:
        st.caption("Nothing thawed yet.")
    else:
        st.dataframe(log, hide_index=True, use_container_width=True)
