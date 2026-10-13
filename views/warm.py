import streamlit as st

import db

st.title("🔥 Let's warm up!")

for msg in st.session_state.pop("flash", []):
    st.success(msg)

q = st.text_input("Line name", placeholder="e.g. GDF15, B6J")
if not q.strip():
    st.caption(f"Known lines: {', '.join(db.strains()) or '— none yet —'}")
    st.stop()

df = db.live_straws(strain_like=q)
if df.empty:
    st.warning(f"No straws in the freezer for '{q}'.")
    st.stop()

version = st.session_state.setdefault("warm_version", 0)  # bump to reset the tick boxes after a thaw
selected: list[int] = []

for strain, g in df.groupby("strain", sort=False):
    st.subheader(strain)
    for material in db.MATERIALS:
        part = g[g.material == material]
        st.markdown(f"**{material}** — {len(part)} straw(s)")
        if part.empty:
            st.caption("None stored.")
            continue
        cols = ["straw_no", "shelf", "position", "lab", "agendo_id"]
        if material == "Embryo":
            cols.append("n_embryos")
        tbl = part.set_index("straw_id")[cols].copy()
        tbl["thaw"] = False
        edited = st.data_editor(
            tbl,
            key=f"warm_{version}_{strain}_{material}_{q}",
            hide_index=True,
            use_container_width=True,
            disabled=cols,
            column_config={
                "straw_no": "Straw ID", "shelf": "Shelf", "position": "Position", "lab": "Lab",
                "agendo_id": "Agendo ID", "n_embryos": "Embryos",
                "thaw": st.column_config.CheckboxColumn("Thaw?"),
            },
        )
        selected += [int(i) for i in edited.index[edited["thaw"]]]
    st.divider()

st.caption(f"{len(selected)} straw(s) selected")
if st.button("warm it up!", type="primary"):
    if not selected:
        st.info("Nothing selected — tick the boxes in the last column.")
    else:
        try:
            done = db.thaw_straws(selected)
        except ValueError as e:
            st.error(str(e))
        else:
            st.session_state["flash"] = [
                f"{d['strain']} · {d['material']}: thawed {d['straws']} straw(s), IDs {d['ids']}"
                + (f" ({d['embryos']} embryos)." if d["embryos"] is not None else ".")
                for d in done
            ]
            st.session_state["warm_version"] = version + 1
            st.rerun()  # redraw with the updated inventory

with st.expander("Recent thaws"):
    log = db.recent_thaws()
    if log.empty:
        st.caption("Nothing thawed yet.")
    else:
        st.dataframe(log, hide_index=True, use_container_width=True)
