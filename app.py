# =========================================================
# app.py — Compute-Dollar Risk Terminal 主入口
# =========================================================

import streamlit as st
import os

st.set_page_config(
    page_title="Compute-Dollar Risk Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- 公共 CSS -----------------------------------------------
import pathlib
css_path = pathlib.Path(__file__).parent / "styles" / "bloomberg.css"
if css_path.exists():
    st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)

# ---- 页面定义 -----------------------------------------------
dashboard_page = st.Page("pages/dashboard.py", title="📡 总览 Dashboard", icon="📡", default=True)
straw1_page    = st.Page("pages/straw1.py",    title="🌾 Straw 1 · 资本开支",     icon="🌾")
straw2_page    = st.Page("pages/straw2.py",    title="💻 Straw 2 · 开源压缩",     icon="💻")
straw3_page    = st.Page("pages/straw3.py",    title="🏗 Straw 3 · 数据中心减值",  icon="🏗")
straw4_page    = st.Page("pages/straw4.py",    title="⚡ Straw 4 · 能源控制",      icon="⚡")
straw6_page    = st.Page("pages/straw6.py",    title="📊 Straw 6 · 宏观预警",      icon="📊")

pg = st.navigation(
    {
        "系统总览": [dashboard_page],
        "风险因子": [straw1_page, straw2_page, straw3_page,
                     straw4_page, straw6_page],
    }
)

pg.run()
