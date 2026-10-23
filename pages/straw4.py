import streamlit as st
import plotly.graph_objects as go
from components.ui import (counter_card, evidence_table, load_css,
                           metric_card, render_data_freshness, render_footer,
                           render_header, section_intro, source_tag_row)
from core.alert_engine import render_alert, render_osci_card
from core.score_engine import register_score
from components.infra_update_panel import render_infra_updates
from core.infra_current import load_infra, score_infra
from core.energy_cost import load_cost, history as cost_history
from components.energy_cost_panel import render_cost_evidence
from components.energy_cost_status import maintenance_badge
from core.gpu_efficiency import load_gpu_efficiency
from components.gpu_efficiency_panel import automatic_badge, render_gpu_efficiency_evidence
from core import energy_market, infra_updates
from core.energy_quarterly import load_history as load_quarterly_history, make_current_snapshot
from components.energy_quarterly_panel import render_current_quarter, render_quarterly_history
from core.energy_counter_signals import load_counter_signals
from components.energy_counter_panel import render_counter_evidence, review_banner

# =========================================================
# 页面配置
# =========================================================

st.set_page_config(
    page_title="AI能源约束",
    layout="wide"
)
load_css()

# =========================================================
# CSS — 使用全站统一的风险页面样式
# =========================================================


# =========================================================
# 静态基准数据（手动维护）
# 数据来源：EIA报告、NERC评估、行业白皮书
# 更新频率：每季度一次，或重大政策变化后更新
# =========================================================

INFRA_DATA = {
    # 并网排队周期（月）— 来自FERC/NERC互联请求队列报告
    "interconnection_queue_months": 43,
    # 变压器交付周期（月）— 大型电力变压器（LPT）采购周期
    "transformer_lead_time_months": 36,
    # PJM电网储备率（%）
    "pjm_reserve_margin_pct": 16.5,
    # ERCOT电网储备率（%）
    "ercot_reserve_margin_pct": 12.8,
    # 更新时间
    "updated": "2025-01",
}

# =========================================================
# 能源成本采用实际集群口径；IEA工业成对年度快照仅供背景参考
# =========================================================

@st.cache_data(ttl=86400, show_spinner=False)
def get_gpu_efficiency_snapshot(policy_version):
    """Use one reviewed provider for the detail page and overview."""
    if policy_version != "quarterly-v1":
        raise ValueError("未知的系统能效复核策略版本")
    return load_gpu_efficiency(check_remote=True)


# =========================================================
# ESRI 评分计算
# =========================================================

def compute_infra_score():
    return score_infra(INFRA_DATA)


def compute_cost_score(us_price_usd: float):
    return cost_snapshot["score"] if cost_snapshot["available"] else None


def compute_efficiency_score():
    return gpu_snapshot["metrics"]["score"] if gpu_snapshot["available"] else None


def compute_esri(infra_s, cost_s, efficiency_s, market_s):
    if any(s is None for s in (infra_s,cost_s,efficiency_s,market_s)):
        return None
    return round(
        0.40 * infra_s +
        0.25 * cost_s  +
        0.20 * efficiency_s +
        0.15 * market_s,
        1
    )


def get_state(esri):
    if esri is None:
        return "N/A", "gray", "Incomplete Input Data", "必要输入或情景证据不完整，暂不输出完整ESRI。其他有效分项继续展示。"
    if esri < 30:
        return "SAFE",    "green",  "Grid Optimal",               "电力系统承载AI扩张，能源约束尚未成型，美国借电体系运转正常。"
    elif esri < 50:
        return "WATCH",   "yellow", "Infrastructure Lag Emerging", "基建时滞显现，并网排队开始压缩数据中心交付节奏，局部电力紧张。"
    elif esri < 70:
        return "WARNING", "orange", "Thermodynamic Bottleneck",    "热力学瓶颈形成，能源成本上升向推理成本传导，AI ROI开始承压。"
    else:
        return "CRITICAL","red",    "Energy Monetization Crunch",  "货币化能力受物理侧切断，算力扩张撞墙，需联动资本开支偏离确认CASCADE。"


def score_to_color(s):
    if s is None:
        return "gray", "—"
    if s < 30:   return "green",  "↗"
    elif s < 50: return "yellow", "→"
    elif s < 70: return "orange", "↘"
    else:        return "red",    "↓"


# =========================================================
# 顶部标题
# =========================================================

render_header("⚡ AI能源约束", "核心监测维度：AI需求增长速度是否超过可调度能源的扩张速度", symbol="ESRI · 能源系统风险指数")

render_infra_updates(INFRA_DATA)
infra_snapshot = load_infra()
INFRA_DATA = infra_snapshot["inputs"]

# =========================================================
# 数据加载
# =========================================================

with st.spinner("正在从 Yahoo Finance 读取 CEG / VST 电力资产行情..."):
    market_snapshot = energy_market.load_energy_market()

cost_snapshot = load_cost()
us_price_live = cost_snapshot["us_price"]
us_price_tag_html = maintenance_badge(cost_snapshot)
gpu_snapshot = get_gpu_efficiency_snapshot("quarterly-v1")
counter_snapshot = load_counter_signals()

# =========================================================
# 各分项评分
# =========================================================

infra_s      = compute_infra_score()
cost_s       = compute_cost_score(us_price_live)
efficiency_s = compute_efficiency_score()
market_s     = market_snapshot["score"] if market_snapshot["available"] else None
esri         = compute_esri(infra_s, cost_s, efficiency_s, market_s)
if esri is not None:
    register_score("straw4", esri)
else:
    st.session_state.setdefault("straw_scores",{}).pop("straw4",None)

state, state_color, state_eng, state_cn = get_state(esri)

bar_color_map = {
    "green": "#22c55e", "yellow": "#fbbf24",
    "orange": "#f97316", "red": "#ef4444"
}
bar_color = bar_color_map.get(state_color, "#94a3b8")

infra_color,  infra_arrow  = score_to_color(infra_s)
cost_color,   cost_arrow   = score_to_color(cost_s)
eff_color,    eff_arrow    = score_to_color(efficiency_s)
mkt_color,    mkt_arrow    = score_to_color(market_s)

# =========================================================
# ESRI 总分大卡片
# =========================================================

st.markdown(render_osci_card(
    "ENERGY SYSTEM RISK INDEX", esri, state, f"情景综合评分：{state_cn}<br>变压器采用48个月交付压力上限情景，不是平均交期。",
    bar_color=bar_color, state_detail=state_eng,
    components_html="基础设施 ×0.40 · 成本压力 ×0.25<br>系统能效对冲 ×0.20 · 电力市场信号 ×0.15",
    score_display=f"{esri:.0f}" if esri is not None else "N/A",
), unsafe_allow_html=True)

# =========================================================
# 四张指标卡片
# =========================================================

c1, c2, c3, c4 = st.columns(4)

# 卡片1：基础设施约束（静态）
with c1:
    queue   = INFRA_DATA["interconnection_queue_months"]
    xfmr    = INFRA_DATA["transformer_lead_time_months"]
    pjm_r   = INFRA_DATA["pjm_reserve_margin_pct"]
    ercot_r = INFRA_DATA["ercot_reserve_margin_pct"]
    fresh1 = '<span class="source-tag">官方资料＋交付压力情景</span>'
    queue_display=f"{queue:g}mo" if queue is not None else "N/A"
    pjm_text=f"{pjm_r:g}%" if pjm_r is not None else "N/A"
    ercot_text=f"{ercot_r:g}%" if ercot_r is not None else "N/A"
    st.markdown(metric_card(f"基础设施约束 {fresh1}", queue_display, infra_color, infra_arrow,
                            "发电项目申请→投运中位时长 · 2025年建成项目<br>"
                            f"夏季预期备用裕度（2026）：PJM {pjm_text} · ERCOT {ercot_text}<br>"
                            + (f"变压器交付压力：{xfmr:g}个月近似上限情景（非平均值）<br>基础设施情景分：{infra_s:g}/100" if xfmr is not None and infra_s is not None else "变压器情景证据待核验 · 本分项N/A")), unsafe_allow_html=True)

# 卡片2：能源成本压力（实际集群资料，尚缺可比成对价格）
with c2:
    bounds = cost_snapshot.get("ratio_range")
    ratio_text = f"{bounds[0]:.2f}—{bounds[1]:.2f}" if bounds else "N/A"
    st.markdown(metric_card(
        f"能源成本压力 {us_price_tag_html}", ratio_text, cost_color, cost_arrow,
        "中美算力地区参考电价比（中国÷美国）<br>"
        "中国2地区公开参考价 · 美国4州工业代理<br>"
        "地区等权中位数；非全国均价、非同口径实测<br>"
        + (f"区间两端均为{cost_snapshot['state']} · {cost_s:g}分；费用占比不再计分" if cost_s is not None else cost_snapshot["missing_reason"]),
    ), unsafe_allow_html=True)

# 卡片3：AI推理系统能效对冲（MLPerf整机实测）
with c3:
    gpu_metrics = gpu_snapshot["metrics"]
    gain = gpu_metrics["generation_gain"]
    fresh3 = automatic_badge(gpu_snapshot)
    st.markdown(metric_card(
        f"AI推理系统能效对冲 {fresh3}", f"{gain:.2f}x", eff_color, eff_arrow,
        f"MLPerf整机实测 · {gpu_metrics['pair_count']}组同口径配对<br>"
        f"{gpu_snapshot['baseline_generation']} {gpu_snapshot['baseline_release']} → "
        f"{gpu_snapshot['target_generation']} {gpu_snapshot['target_release']}<br>"
        f"同等基准工作残余能源强度：{gpu_metrics['score']:.1f}%",
    ), unsafe_allow_html=True)

# 卡片4：电力市场信号
with c4:
    if market_snapshot["available"]:
        ceg = market_snapshot["rows"]["CEG"]
        vst = market_snapshot["rows"]["VST"]
        desc4 = (f"CEG ${ceg['current_price']:.1f}（52周位置 {ceg['position_pct']:.0f}%）<br>"
                 f"VST ${vst['current_price']:.1f}（52周位置 {vst['position_pct']:.0f}%）<br>"
                 f"行情日期 {market_snapshot['observed_on']} · 分项{market_s:g}分")
        display4 = f"{market_snapshot['mean_position_pct']:.0f}%"
    else:
        desc4 = market_snapshot["missing_reason"]
        display4 = "N/A"
    st.markdown(metric_card('电力市场信号 <span class="source-tag">Yahoo 行情 · CEG/VST · 1小时缓存</span>', display4,
                            mkt_color, mkt_arrow, desc4), unsafe_allow_html=True)

# =========================================================
# Alert 结论框
# =========================================================

if esri is None:
    st.markdown(section_intro("必要资料不完整，完整ESRI暂不可用",
        cost_snapshot["missing_reason"] if not cost_snapshot["available"] else
        "基础设施必要输入或48月情景证据不完整；不补旧值、不改权重。"),unsafe_allow_html=True)
else:
    st.markdown(render_alert(state,"结论：能源约束情景评分，不是已确认缺电",
        f"当前情景ESRI={esri:.1f}，状态{state}。基础设施情景分{infra_s:.1f}，按原40%权重贡献{infra_s*.4:.1f}分。"
        "变压器48月为已确认采用的交付压力上限情景，不是平均值；并网耗时及备用裕度分别使用各自期间。"
        "成本采用固定地区中位数代理比较，按0.80/0.60/0.40分档，双方费用与期间不完全一致；15%费用占比不再计分。"
        f"系统能效采用MLPerf整机实测，{gpu_snapshot['baseline_generation']}→{gpu_snapshot['target_generation']}的"
        f"{gpu_metrics['pair_count']}组可比结果中位提升{gain:.2f}倍，按100÷提升倍数计{efficiency_s:.1f}分。"
        "新旧有口径断点，不能把分差当作市场突然恶化；本页不单独确认CASCADE。"),unsafe_allow_html=True)

# =========================================================
# 评分构成图直接展示；检测方法和分项值留在底部标签页。
# =========================================================

def _render_detection_logic():
    sections = [
        ("1", "基础设施约束（×0.40）",
         "发电项目申请至投运中位时长（45%）+ 大型变压器48月交付压力上限情景（30%，不是平均值）+ PJM/ERCOT夏季预期备用裕度ARM（25%）。时长不是数据中心接电等待，ARM不是晚间风险裕度。沿用原公式：q=clamp((月数−12)/36×100)，t同式；r=clamp((20−两地裕度均值)/12×100)；分项=round(0.45q+0.30t+0.25r,1)。本期q=100、t=100、r=0，分项75分，×40%贡献30分。必要值或情景证据缺失则N/A，不重分配权重。以下旧研究分档未重新校准；新旧有口径断点。",
         ["🟢 排队 <12月 · 储备率 >20% · SAFE",
          "🟡 排队 12–24月 · 储备率 15–20% · WATCH",
          "🟠 排队 24–36月 · 储备率 10–15% · WARNING",
          "🔴 排队 >36月 · 储备率 <10% · CRITICAL"]),
        ("2", "能源成本压力（×0.25）",
         "R=中国地区中位数÷美国地区中位数。固定两国地区名单，分别计算报价上下限，不取中点。分项按档位映射15/40/60/85分，整页25%权重不变；不是行业标准、实测风险概率或全国同口径比较。15%费用占比仅作旧假设参考，不再计分。区间两端同档才计入整页；跨档则展示状态范围，单点N/A。旧55/45加权公式及旧9分保留在历史。",
         ["🟢 R ≥ 0.80 · 15分 · SAFE",
          "🟡 0.60 ≤ R < 0.80 · 40分 · WATCH",
          "🟠 0.40 ≤ R < 0.60 · 60分 · WARNING",
          "🔴 0 < R < 0.40 · 85分 · CRITICAL"]),
        ("3", "AI推理系统能效对冲（×0.20）",
         f"使用MLPerf官方整机实测功耗。先在{gpu_snapshot['baseline_release']}与{gpu_snapshot['target_release']}之间筛选同任务、同场景、同单位、同卡数记录，再取各配对性能/瓦提升倍数的中位数G。本期{gpu_snapshot['baseline_generation']}→{gpu_snapshot['target_generation']}共有{gpu_snapshot['metrics']['pair_count']}组，G={gpu_snapshot['metrics']['generation_gain']:.3f}×；分项=clamp(100÷G,0,100)={gpu_snapshot['metrics']['score']:.1f}分，×20%贡献{gpu_snapshot['metrics']['contribution']:.1f}分。只采纳实测整机功耗；TDP、路线图预测与单卡理论规格不计分。新版本没有足够合格配对时保留上次有效结果。",
         None),
        ("4", "电力市场信号（×0.15）",
         "固定使用CEG与VST。先计算两者各自在52周高低区间的位置P，再取平均；P≤40%计20分，40%<P≤60%计35分，60%<P≤80%计55分，P>80%计75分。它只是美国电力资产市场定价代理，不证明物理缺电。两者任一缺失或行情日期不一致时分项N/A，不使用后备分。详情页与总览共用同一入口。",
         ["🟢 P ≤ 40% · 20分 · SAFE",
          "🟡 40% < P ≤ 60% · 35分 · WATCH",
          "🟠 60% < P ≤ 80% · 55分 · WARNING",
          "🔴 P > 80% · 75分 · CRITICAL"]),
    ]
    for number, title, explanation, thresholds in sections:
        with st.expander(f"{number}　{title}", expanded=False):
            st.write(explanation)
            if thresholds:
                st.markdown("**评分规则**")
                for line in thresholds:
                    st.markdown(line)

with st.container(border=True):
    st.markdown('<div class="panel-title">📊 ESRI分项评分构成 · 能源风险传导链</div>', unsafe_allow_html=True)

    categories = ["基础设施约束", "能源成本压力", "系统能效对冲", "电力市场信号"]
    scores     = [infra_s, cost_s, efficiency_s, market_s]
    weights    = [0.40, 0.25, 0.20, 0.15]
    bar_labels = [f"{c}  ×{w:.2f}  →  {f'{s:.0f}分' if s is not None else 'N/A（待核验）'}"
                  for c, w, s in zip(categories, weights, scores)]

    bar_colors_list = []
    for s in scores:
        if s is None: bar_colors_list.append("#94a3b8")
        elif s < 30:   bar_colors_list.append("#22c55e")
        elif s < 50: bar_colors_list.append("#fbbf24")
        elif s < 70: bar_colors_list.append("#f97316")
        else:        bar_colors_list.append("#ef4444")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=scores,
        y=bar_labels,
        orientation="h",
        marker_color=bar_colors_list,
        marker_line_width=0,
        width=0.55,
        text=[f"{s:.0f}" if s is not None else "N/A" for s in scores],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=15),
    ))
    if esri is not None:
        fig.add_shape(type="line", x0=esri, x1=esri, y0=-0.5, y1=3.5,
                      line=dict(color="rgba(255,255,255,0.3)", width=1.5, dash="dash"))
        fig.add_annotation(x=esri, y=3.7, text=f"ESRI={esri}",
                           showarrow=False, font=dict(color="#94a3b8", size=13), xanchor="center")
    fig.update_layout(
        height=280,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", size=12),
        margin=dict(l=10, r=60, t=30, b=10),
        xaxis=dict(range=[0, 105], showgrid=True,
                   gridcolor="rgba(255,255,255,0.05)", zeroline=False,
                   tickfont=dict(color="#94a3b8", size=11)),
        yaxis=dict(showgrid=False, tickfont=dict(color="#94a3b8", size=13)),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    ceg_pos_str = (f"CEG: {market_snapshot['rows']['CEG']['position_pct']:.0f}% 52w位"
                   if market_snapshot["available"] else "CEG: N/A")
    vst_pos_str = (f"VST: {market_snapshot['rows']['VST']['position_pct']:.0f}% 52w位"
                   if market_snapshot["available"] else "VST: N/A")
    eia_tag = ('<span class="source-tag">地区中位数代理 · 区间同分</span>' if cost_snapshot["available"]
               else '<span class="source-tag-warn">地区参考电价：单点评分待核验</span>')
    st.markdown(source_tag_row([
        '<span class="source-tag">Yahoo Finance ✓</span>', eia_tag,
        '<span class="source-tag-warn">基础设施：2025投运 / 2026夏季 · 48月压力情景</span>',
        f'<span class="source-tag">MLPerf整机实测 {gpu_snapshot["metrics"]["pair_count"]}/3 · 自动季度检查</span>',
        f'<span class="source-tag-gray">{ceg_pos_str}</span>',
        f'<span class="source-tag-gray">{vst_pos_str}</span>',
    ]), unsafe_allow_html=True)

# =========================================================
# 反证模块
# =========================================================

st.markdown(section_intro("🛡️ 反证模块（Counter Signals）— 能源风险对冲因素",
                          "以下是降低能源约束的反证观察，不计入ESRI，不自动改分"), unsafe_allow_html=True)
st.markdown(review_banner(counter_snapshot), unsafe_allow_html=True)

cc1, cc2, cc3 = st.columns(3)

with cc1:
    signal_a = counter_snapshot["signals"]["overseas_ai_expansion"]
    st.markdown(counter_card(signal_a["title"], signal_a["summary"],
                             label=signal_a["status_label"], value=signal_a["display_value"]), unsafe_allow_html=True)

with cc2:
    st.markdown(counter_card(
        "Counter B · AI推理系统能效提升",
        f"MLPerf官方整机实测显示，{gpu_snapshot['target_generation']}相对{gpu_snapshot['baseline_generation']}的"
        f"三组同口径配对中位能效提升为{gain:.2f}倍。同等基准工作对应残余能源强度为"
        f"{gpu_metrics['score']:.1f}%；它可对冲单位工作量耗电，但不代表总需求反弹或数据中心总功耗已经下降。",
        label="整机实测效率增益：", value=f"{gpu_snapshot['baseline_generation']}→{gpu_snapshot['target_generation']}={gain:.2f}x",
    ), unsafe_allow_html=True)

with cc3:
    signal_c = counter_snapshot["signals"]["dedicated_power_progress"]
    st.markdown(counter_card(signal_c["title"], signal_c["summary"],
                             label=signal_c["status_label"], value=signal_c["display_value"]), unsafe_allow_html=True)

# =========================================================
# 底部注释：数据说明（IEA年度核验快照，不再请求EIA）
# =========================================================

logic_tab, evidence_tab, source_tab = st.tabs(["检测逻辑", "指标与历史证据", "数据覆盖与来源"])
with logic_tab:
    with st.container(key="energy_detection_logic"):
        _render_detection_logic()
with evidence_tab:
    current_quarter = make_current_snapshot(infra_snapshot, cost_snapshot, gpu_snapshot, market_snapshot)
    quarterly_history = load_quarterly_history()
    render_current_quarter(current_quarter)
    render_counter_evidence(counter_snapshot)
    render_cost_evidence(cost_snapshot, include_history=False)
    render_gpu_efficiency_evidence(gpu_snapshot, include_history=False)
    infra_history = infra_updates.history()
    legacy_evidence = {
        "infrastructure": {
            "baselines": infra_history["baselines"],
            "input_versions": infra_history["input_versions"],
        },
        "energy_cost": cost_history(),
        "system_efficiency": gpu_snapshot["history"],
        "market_signal": "旧五标的混合口径不再计分；2026Q3页面基准已统一归档。",
        "counter_signals": counter_snapshot,
    }
    render_quarterly_history(quarterly_history, current_quarter, legacy_evidence)
with source_tab:
    render_data_freshness([
        {"name": "算力地区参考电价", "source": "中国2地区公开参考价 / 美国EIA 4州工业代理；人工季度复核", "updated_at": cost_snapshot["period"], "mode": "static"},
        {"name": "电力市场信号", "source": "Yahoo Finance · CEG / VST；两者52周位置均值", "updated_at": market_snapshot.get("observed_on", "N/A") + "；每小时缓存", "mode": "live"},
        {"name": "基础设施约束", "source": "LBNL 2026版 · NERC 2026夏季 · DOE描述＋用户确认48月上限情景（非平均）", "updated_at": INFRA_DATA["updated"], "mode": "fallback"},
        {"name": "AI推理系统能效", "source": "MLCommons MLPerf官方整机性能与实测功耗；季度自动检查，未通过门槛则保留上期", "updated_at": gpu_snapshot["checked_at"], "mode": "live"},
        {"name": "反证模块A/C", "source": "官方公告与监管页面；跨季度后人工复核，不自动累加容量", "updated_at": counter_snapshot["reviewed_on"], "mode": "static"},
        {"name": "电力占运营费用", "source": "15%沿用研究假设，出处待核验；非本期实测", "updated_at": "原录入2025-01，观察期未知", "mode": "static"},
    ])
render_footer(f'Yahoo Finance（CEG/VST）· 中国地区参考价 / 美国EIA工业代理（非同口径全国均价）· IEA旧工业背景 · LBNL · NERC · DOE · MLCommons MLPerf官方整机实测（{INFRA_DATA["updated"]}）')
