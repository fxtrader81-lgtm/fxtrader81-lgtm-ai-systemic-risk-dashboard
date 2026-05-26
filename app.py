import streamlit as st

st.set_page_config(layout="wide")

st.markdown("""

<style>

.metric-card{
    background:#111827;
    padding:30px;
    border-radius:20px;
    border:1px solid #374151;
}

.metric-label{
    color:#94a3b8;
    font-size:14px;
}

.metric-number{
    font-size:42px;
    font-weight:700;
    color:#22c55e;
}

.metric-desc{
    color:white;
    margin-top:10px;
}

</style>

""", unsafe_allow_html=True)

st.markdown("""

<div class="metric-card">

    <div class="metric-label">
    收入增长率 (YoY)
    </div>

    <div class="metric-number">
    65.47%
    </div>

    <div class="metric-desc">
    AI需求仍维持高增长，
    当前收入扩张速度保持强劲。
    </div>

</div>

""", unsafe_allow_html=True)
