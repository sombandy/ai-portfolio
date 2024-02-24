# first-party
import src.portfolio as pf

# third-party
import streamlit as st

st.set_page_config(
    page_title="AI Portfolio",
    page_icon="📈",
    initial_sidebar_state="collapsed"
)

st.sidebar.success("Select a page")

s, t = pf.summary()

st.dataframe(s, use_container_width=True)
st.markdown("Overall Postions")
st.dataframe(t, use_container_width=True)