"""Streamlit test harness for the unscored factor-05 disclosure view."""

import streamlit as st

from components.credit_transmission_views import render_structure_evidence


st.set_page_config(page_title="Credit structure test")
render_structure_evidence()
