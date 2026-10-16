"""Unscored issuer disclosures shared by factor 05 and factor 06.

These views deliberately do not register a factor score.  SEC companyfacts
is requested only after the reader opens the company disclosure section.
"""

from __future__ import annotations

from html import escape

import plotly.graph_objects as go
import streamlit as st

from components.ui import panel
from core.credit_transmission import ISSUERS, build_company_snapshot, disclosure_age_label, load_companyfacts


def _text(value: object) -> str:
    return escape(str(value))


def _money(value: float | None) -> str:
    return "不可得" if value is None else f"{value / 1e9:,.2f}"


def _percent(value: float | None) -> str:
    return "不可得" if value is None else f"{value * 100:,.1f}%"


def _link(url: str, label: str) -> str:
    return f'<a href="{escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{_text(label)}</a>'


def _table(title: str, columns: list[str], rows: list[list[str]], note: str = "") -> None:
    headings = "".join(f'<th scope="col">{_text(label)}</th>' for label in columns)
    body = "".join("<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows)
    note_html = f'<div class="metric-sub credit-note">{_text(note)}</div>' if note else ""
    st.markdown(panel(title, f'<div class="table-scroll"><table class="gpu-table evidence-table credit-table"><thead><tr>{headings}</tr></thead><tbody>{body}</tbody></table></div>{note_html}'), unsafe_allow_html=True)


def _figure(title: str, quarters: list[dict], keys: list[str], labels: list[str], colors: list[str], *, kind: str = "bar") -> None:
    available = [row for row in reversed(quarters[:6]) if any(
        (row["values"] if key in row["values"] else row["derived"]).get(key) is not None for key in keys
    )]
    if not available:
        st.info(f"{title}：没有足够的同期间可核验数据，暂不绘制曲线。")
        return
    figure = go.Figure()
    for key, label, color in zip(keys, labels, colors):
        values = [(row["values"] if key in row["values"] else row["derived"]).get(key) for row in available]
        plotted = [value / 1e9 if value is not None else None for value in values]
        if kind == "line":
            figure.add_trace(go.Scatter(x=[row["end"] for row in available], y=plotted, name=label,
                                        mode="lines+markers", connectgaps=False, line=dict(color=color, width=3)))
        else:
            figure.add_trace(go.Bar(x=[row["end"] for row in available], y=plotted, name=label, marker_color=color))
    figure.update_layout(
        title=title, barmode="group", height=340, paper_bgcolor="#0b1120", plot_bgcolor="#0b1120",
        font=dict(color="#e2e8f0", size=13), margin=dict(l=35, r=15, t=45, b=30),
        yaxis_title="十亿美元", legend=dict(orientation="h", y=1.12, x=0),
    )
    figure.update_xaxes(gridcolor="rgba(255,255,255,.05)")
    figure.update_yaxes(gridcolor="rgba(255,255,255,.08)")
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})


def _company_disclosures(snapshot: dict) -> None:
    quarters = snapshot["quarters"]
    st.caption(
        f"{snapshot['company']} · 单位：十亿美元（比率除外） · 读取：{snapshot['retrieved_at']} UTC · "
        f"{disclosure_age_label(snapshot['ttm_end'])} · SEC companyfacts；申报日期见下表。"
    )
    st.markdown(f"[查看 {_text(snapshot['company'])} 的 SEC 原始数据]({snapshot['source']})")
    if not quarters:
        st.warning("SEC 返回了公司数据，但没有足够的可比季度字段；不填充推测值。")
        return

    rows = []
    for quarter in quarters[:5]:
        values, derived = quarter["values"], quarter["derived"]
        filed = max((fact.filed for fact in quarter["facts"].values() if fact), default="不可得")
        rows.append([_text(quarter["end"]), _money(values["revenue"]), _money(values["operating_cash_flow"]),
                     _money(values["cash_capex"]), _money(derived["simple_fcf"]),
                     _percent(derived["capex_coverage"]), _percent(derived["gap_share"]), _text(filed)])
    ttm, derived = snapshot["ttm_values"], snapshot["ttm_derived"]
    rows.insert(0, [f"TTM至 {_text(snapshot['ttm_end'])}", _money(ttm["revenue"]),
                    _money(ttm["operating_cash_flow"]), _money(ttm["cash_capex"]),
                    _money(derived["simple_fcf"]), _percent(derived["capex_coverage"]),
                    _percent(derived["gap_share"]), "四个连续季度计算"])
    _table("资本开支融资质量｜季度与 TTM",
           ["期间", "营业收入", "经营现金流", "现金资本开支", "简化FCF", "OCF/CapEx", "现金缺口/CapEx", "披露日期/口径"],
           rows, "现金缺口=max(现金资本开支－经营现金流, 0)，只是现金覆盖代理，不等于实际借款需求；TTM 缺任一季度即不可得。")
    left, right = st.columns(2)
    with left:
        _figure("资本开支与经营现金流", quarters, ["cash_capex", "operating_cash_flow"],
                ["现金资本开支", "经营现金流"], ["#f97316", "#22c55e"])
    with right:
        _figure("简化自由现金流趋势", quarters, ["simple_fcf"], ["OCF－现金CapEx"], ["#60a5fa"], kind="line")

    debt_rows = []
    for quarter in quarters[:5]:
        values, derived = quarter["values"], quarter["derived"]
        debt_rows.append([_text(quarter["end"]), _money(values["debt_proceeds"]),
                          _money(values["debt_repayments"]), _money(derived["net_debt_financing"]),
                          _percent(derived["net_debt_to_capex"]), _percent(derived["capex_intensity"]),
                          _money(values["interest_expense"]),
                          _text("、".join(sorted({fact.kind for fact in quarter["facts"].values() if fact})) or "不可得")])
    _table("债务融资及资本开支",
           ["期间", "债务流入", "债务偿还", "净债务融资", "净融资/CapEx", "CapEx/收入", "利息费用", "数据类别"],
           debt_rows, "净债务融资=已披露债务现金流入－偿还；不能证明融资用于AI。缺失值不填零。")
    _figure("债务融资与资本开支对比", quarters, ["net_debt_financing", "cash_capex"],
            ["净债务融资代理", "现金资本开支"], ["#a78bfa", "#f97316"])
    _table("资本投入边界｜现金与融资租赁分列", ["期间", "现金资本开支", "融资租赁新增额", "公司公布的FCF"], [
        [_text(row["end"]), _money(row["values"]["cash_capex"]),
         _money(row["values"]["finance_lease_additions"]), "未在标准化接口中识别；需核对IR定义"]
        for row in quarters[:5]
    ], "已确认租赁负债、未开始租赁、担保及采购承诺须查附注并分列；不能与账面债务简单相加。简化FCF不同于公司自定义FCF。")

    rpo = snapshot["rpo"]
    _table("RPO 与合同质量", ["公司", "RPO（十亿美元）", "所属期间", "披露日期", "RPO/TTM收入", "合同质量信息", "来源"], [[
        _text(snapshot["company"]), _money(rpo.value if rpo else None), _text(rpo.end if rpo else "不可得"),
        _text(rpo.filed if rpo else "不可得"), _percent(snapshot["rpo_to_revenue"]),
        "商业RPO、客户集中、预付款与未来12个月确认比例：待逐份申报核验", _link(snapshot["source"], "SEC原始数据"),
    ]], "RPO 是尚未确认的合同未来收入，不等于现金或已实现收入；商业RPO与全公司收入之比仅能标为代理比较。")
    _table("利润质量｜不得用税前数直接调整税后净利",
           ["期间", "经营利润", "税前利润", "净利润", "AI投资损益", "剔除后调整结果"], [
               [_text(row["end"]), _money(row["values"]["operating_income"]),
                _money(row["values"]["pretax_income"]), _money(row["values"]["net_income"]),
                "不可得", "不可得"] for row in quarters[:5]
           ], "AI投资损益需核对公司原始披露及税后影响；标准化XBRL不能自动识别其AI属性，不生成猜测调整值。")
    _figure("经营利润与净利润", quarters, ["operating_income", "net_income"],
            ["经营利润", "净利润"], ["#22c55e", "#60a5fa"])
    with st.expander("查看本公司字段口径与来源", expanded=False):
        latest = quarters[0]
        audit_rows = []
        for key, label in [("revenue", "营业收入"), ("operating_cash_flow", "经营现金流"),
                           ("cash_capex", "现金资本开支"), ("operating_income", "经营利润"),
                           ("pretax_income", "税前利润"), ("net_income", "净利润"),
                           ("interest_expense", "利息费用"), ("debt_proceeds", "债务流入"),
                           ("debt_repayments", "债务偿还"), ("finance_lease_additions", "融资租赁新增额")]:
            fact = latest["facts"][key]
            audit_rows.append([_text(label), _text(fact.kind if fact else "不可得"),
                               _text(fact.tags[0] if fact else "无公司级标准化字段"),
                               _text(fact.filed if fact else "—"),
                               _text(fact.method if fact else "需查原始附注"), _link(snapshot["source"], "SEC")])
        _table("最新季度字段审计", ["指标", "类别", "XBRL标签", "披露日期", "计算方法", "来源"], audit_rows)


def render_structure_evidence() -> None:
    """Factor 05: structural exposure and issuer disclosures, never a score input."""
    st.markdown(panel("05 结构暴露 → 06 信用确认",
        '<div class="credit-path">AI实验室融资依赖 → 云合同与RPO → 云厂商资本开支 → 债务及租赁承诺 → '
        '<a href="/factor-credit-refinancing">信用重新定价（见06）</a> → 融资约束 → 资本开支下调 → 资产及供应商订单承压</div>'
        '<div class="credit-note">这是待数据验证的反馈路径，不是必然的固定因果顺序；下方公司披露证据不纳入AFVI评分。</div>'),
        unsafe_allow_html=True)
    _table("已确认的投资与云采购关系", ["云厂商", "观察对象", "已确认关系", "合同敞口", "来源日期", "原始来源"], [
        ["Microsoft", "OpenAI", "战略投资、云服务与收益分享关系", "未披露完整敞口", "2025-01-21", _link("https://blogs.microsoft.com/blog/2025/01/21/microsoft-and-openai-evolve-partnership-to-drive-the-next-phase-of-ai/", "微软官方")],
        ["Amazon", "Anthropic", "战略投资与AWS云服务关系", "未披露完整敞口", "2023-09", _link("https://www.aboutamazon.com/news/company-news/amazon-aws-anthropic-ai", "亚马逊官方")],
        ["Oracle", "OpenAI", "OCI云服务关系；投资关系未确认", "未披露完整敞口", "2024-06-11", _link("https://www.oracle.com/news/announcement/openai-selects-oracle-cloud-infrastructure-to-extend-microsoft-azure-ai-platform-2024-06-11/", "甲骨文官方")],
    ], "只记录所列原始公告可支持的关系；战略投资与云采购本身不表示虚假收入。未列关系不等于不存在。")
    if not st.toggle("查看五家公司财报、RPO与利润质量明细（按需读取SEC）", value=False, key="factor05_company_disclosures"):
        return
    symbol = st.selectbox("选择公司｜分别观察，Oracle不代表整体", list(ISSUERS),
                          format_func=lambda ticker: f"{ISSUERS[ticker][0]} · {ticker}", key="factor05_issuer")
    if st.button("更新所选公司SEC披露缓存", key="factor05_refresh_companyfacts"):
        load_companyfacts.clear(symbol)
        st.rerun()
    try:
        with st.spinner(f"正在读取 {ISSUERS[symbol][0]} 的SEC结构化披露…"):
            payload, retrieved_at = load_companyfacts(symbol)
            snapshot = build_company_snapshot(payload, symbol, retrieved_at)
    except Exception as exc:
        status = getattr(getattr(exc, "response", None), "status_code", None)
        reason = f"SEC API HTTP {status}" if status else type(exc).__name__
        st.warning(f"本次无法读取SEC结构化财报（{reason}）；财务指标不可得，不以零值或旧数据替代。")
        return
    _company_disclosures(snapshot)


def render_credit_market_evidence() -> None:
    """Factor 06: clarify the boundary between broad proxies and issuer quotes."""
    st.markdown(panel("逐发行人信用重新定价｜证据边界",
        '<div class="metric-sub">本页上方 HY OAS、TIPS 与 NFCI 是广泛市场代理，不是 Microsoft、Amazon、Alphabet、Meta 或 Oracle 的实际债券报价。'
        '这五家的可比公司债利差、CDS、发行溢价、认购倍数及二级市场表现尚无稳定且可核验的数据序列，当前标为“不可得”，不填零、不模拟、不计入CFRI。'
        '数据中心ABS、相关私募信贷以及逐发行人评级与展望也待逐项核验，不以股票波动率替代信用指标。'
        '下方“已核实的AI融资事件”按单笔发行文件展示条款与状态；票息变化不能直接解释为信用利差变化。'
        '<a href="/factor-financing-structure">05 查看现金覆盖、RPO与融资结构证据 →</a></div>'), unsafe_allow_html=True)
