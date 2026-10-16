"""Streamlit test harness for the unscored factor-06 credit evidence view."""

import streamlit as st

from components.credit_transmission_views import render_credit_market_evidence


st.set_page_config(page_title="Credit market test")
render_credit_market_evidence()
