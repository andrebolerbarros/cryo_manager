import streamlit as st

import db
import plans

st.title("🐺 Winter is coming")

for msg in st.session_state.pop("flash_winter", []):
    st.success(msg)

v = st.session_state.setdefault("winter_v", 0)  # bump to clear the form after a successful save

c1, c2 = st.columns(2)
agendo_id = c1.text_input("Agendo ID", key=f"w_agendo_{v}").strip()
strain_id = c2.text_input("Strain ID", key=f"w_strain_{v}").strip()
comment = st.text_area(
    "Comment", height=220, key=f"w_comment_{v}",
    placeholder="3 females DOB 2026-01-15\n2 males DOB 2026-02-12\n\n"
                "One line per birth date: number of females / males + DOB (or D.O.B.). "
                "Dates as YYYY-MM-DD, DD/MM/YYYY or 15 Jan 2026 (day first). "
                "Anything else you write is kept as a note.",
)

if st.button("Let's get planning!", type="primary"):
    errors = []
    if not agendo_id:
        errors.append("Agendo ID is required.")
    if not strain_id:
        errors.append("Strain ID is required.")
    animals, problems = plans.parse_comment(comment)
    errors += problems
    if errors:
        for e in errors:
            st.error(e)
    else:
        db.add_plan(agendo_id, strain_id, comment, animals)
        st.session_state["flash_winter"] = [
            f"Planned {strain_id} ({agendo_id}): {plans.format_animals(animals)}"]
        st.session_state["winter_v"] = v + 1
        st.rerun()

st.subheader("Planned entries")
rows = db.plans()
if not rows:
    st.caption("Nothing planned yet.")
else:
    st.dataframe(
        [{"Strain ID": r["strain_id"], "Agendo ID": r["agendo_id"],
          "Animals (sex × DOB)": plans.format_animals(r["animals"])} for r in rows],
        hide_index=True, use_container_width=True,
    )
