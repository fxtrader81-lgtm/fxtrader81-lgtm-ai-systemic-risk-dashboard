# =========================================================
# app.py — Compute-Dollar Risk Terminal 主入口
#
# 结构：
#   Dashboard（总览）→ AI结构风险评分 + 七个风险因子
#   
# 运行方式：
#   streamlit run app.py
# =========================================================

import streamlit as st
from datetime import datetime
from pathlib import Path

st.set_page_config(
    page_title="Compute-Dollar Risk Terminal",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---- 公共 CSS -----------------------------------------------
from components.ui import load_css
load_css()

# ---- 导航品牌 ------------------------------------------------
st.sidebar.markdown(
    """
    <div class="nav-brand">
      <div class="nav-brand-kicker">COMPUTE-DOLLAR</div>
      <div class="nav-brand-title">风险监测终端</div>
      <div class="nav-brand-subtitle">SYSTEMIC RISK MONITOR</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---- 页面定义 -----------------------------------------------
# icon 仅在 st.Page 的 icon 参数中声明一次，避免标题中重复出现图标。
dashboard_page = st.Page("pages/dashboard.py", title="系统风险总览", icon="📡", url_path="dashboard", default=True)
factor_pages = [
    st.Page("pages/straw1.py", title="01 · 资本开支偏离", icon="🌾", url_path="factor-capex-divergence"),
    st.Page("pages/straw2.py", title="02 · 开源商业化压缩", icon="💻", url_path="factor-open-source"),
    st.Page("pages/straw3.py", title="03 · 数据中心资产减值", icon="🏗", url_path="factor-data-center-assets"),
    st.Page("pages/straw4.py", title="04 · AI能源约束", icon="⚡", url_path="factor-energy"),
]

if (Path(__file__).parent / "pages" / "straw5.py").exists():
    factor_pages.append(st.Page("pages/straw5.py", title="05 · AI融资结构脆弱性", icon="🏦", url_path="factor-financing-structure"))

factor_pages.extend([
    st.Page("pages/straw6.py", title="06 · AI信贷与再融资压力", icon="💳", url_path="factor-credit-refinancing"),
    st.Page("pages/straw7.py", title="07 · 宏观与跨市场预警", icon="📊", url_path="factor-macro-market"),
])

pg = st.navigation({"监测总览": [dashboard_page], "风险因子": factor_pages})

pg.run()
