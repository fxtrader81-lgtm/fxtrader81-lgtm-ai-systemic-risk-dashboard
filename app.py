# ======================================================
    # KPI (修改后)
    # ======================================================

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        # 移除了 unsafe_allow_html=True，改用 st.html
        st.html(f"""
        <div class="metric-card">
            <div class="metric-label">收入增长率 (YoY)</div>
            <div class="metric-number green">{rev_growth*100:.2f}%</div>
            <div class="metric-desc">
            AI需求仍维持高增长，<br>
            当前收入扩张速度保持强劲。
            </div>
        </div>
        """)

    with c2:
        st.html(f"""
        <div class="metric-card">
            <div class="metric-label">资本开支增长率 (YoY)</div>
            <div class="metric-number red">{capex_growth*100:.2f}%</div>
            <div class="metric-desc">
            企业正在加速AI基础设施投入，<br>
            CapEx扩张速度持续提升。
            </div>
        </div>
        """)

    with c3:
        st.html(f"""
        <div class="metric-card">
            <div class="metric-label">增速差 (CapEx - Revenue)</div>
            <div class="metric-number yellow">+{diff*100:.2f}%</div>
            <div class="metric-desc">
            资本扩张速度已经开始超过<br>
            收入增长速度。
            </div>
        </div>
        """)

    with c4:
        st.html(f"""
        <div class="metric-card">
            <div class="metric-label">状态判断</div>
            <div class="metric-number {status_color}">{status}</div>
            <div class="metric-desc">
            当前AI资本扩张已经进入<br>
            高波动风险阶段。
            </div>
        </div>
        """)

    # ======================================================
    # ALERT (同样改成 st.html)
    # ======================================================

    st.html(f"""
    <div class="alert-box">
        <div class="alert-title">结论：AI资本开支扩张速度明显高于收入增长</div>
        <div class="alert-text">
        当前资本开支增速比收入增速高出
        <span class="yellow">{diff*100:.2f}%</span>，
        企业AI基础设施投入已经开始超出现实需求支撑。
        <br><br>
        若趋势持续，将提升未来盈利与现金流压力。
        </div>
    </div>
    """)
