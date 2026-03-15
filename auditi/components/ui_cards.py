import streamlit as st

def metric_card(title: str, value, delta=None):
    st.metric(label=title, value=value, delta=delta)

def section_title(title: str):
    st.markdown(f"### {title}")