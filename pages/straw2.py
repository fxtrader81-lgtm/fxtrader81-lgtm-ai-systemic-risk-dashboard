import streamlit as st
import requests
import plotly.graph_objects as go
from html import escape
from components.capability_panel import render_capability_controls
from components.factor_quarterly_panel import render_current_quarter, render_quarterly_history
from components.ui import (load_css, metric_card, render_data_freshness,
                           render_footer, render_header, source_tag_row)
from core.alert_engine import render_alert, render_osci_card
from core.score_engine import register_score
from core import capability_gap as capability_store
from core.model_prices import load_prices, history as price_history
from core.deployment_interest import load_deployment, history as deployment_history
from core.ecology_downloads import load_ecology, history as ecology_history
from core.open_source_quarterly import load_history as load_quarterly_history, make_current_snapshot

# =========================================================
# 页面配置
# =========================================================

st.set_page_config(
    page_title="开源商业化压缩",
    layout="wide"
)
load_css()

# =========================================================
# CSS — 使用全站统一的风险页面样式
# =========================================================


# =========================================================
# 工具函数
# =========================================================

def fetch_json(url, headers=None):
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        return None
    except:
        return None

def safe_get(d, *keys, default=0):
    try:
        for k in keys:
            d = d[k]
        return d
    except:
        return default

# =========================================================
# 能力原始资料与旧版数据在config/capability_baseline.json中保留。
# 当前输入由独立刷新按钮管理，不随页面加载执行模型测试或网络搜索。
# =========================================================

# =========================================================
# 数据获取函数
# =========================================================

# =========================================================
# OSCI 评分计算
# =========================================================

def compute_osci(cap_gap_pct, price_compression_pct, deploy_proxy_value, os_velocity_score):
    """
    OSCI = 0.20 x cap + 0.35 x price + 0.30 x deploy + 0.15 x velocity
    各分项标准化到 0-100，越高代表开源对闭源商业侵蚀风险越大

    权重逻辑：
    能力代差降至0.20：benchmark追平是技术事实，商业传导滞后12-18个月
    价格压缩升至0.35：最直接的商业信号，定价权松动立即影响营收
    部署动能沿用0.30：部署工具累计关注度代理，不是企业实际部署/迁移证据
    生态速度保持0.15：领先指标，辅助验证

    商业粘性缓冲（关键）：
    能力代差即使归零，分项上限压至60而非100
    原因：SOC2/HIPAA/SLA/多区域部署/企业支持等商业壁垒
    不会因benchmark追平而立即消失
    """

    # 能力代差：上限60分（商业粘性缓冲）
    # 输入为相对闭源均分的百分比差距（不是两均分直接相减）。
    # gap >= 25% -> 0分; gap <= 0% -> 60分；保留原研究映射。
    cap_score = max(0, min(60, (25 - cap_gap_pct) / 25 * 60))

    # 价格压缩：压缩幅度越大风险越高
    # 压缩 < 10% -> 0分; 压缩 > 60% -> 100分
    price_score = max(0, min(100, (price_compression_pct - 10) / 50 * 100))

    # 部署动能：stars总量映射
    # 输入为原有stars阶梯映射值，不是真实部署增长百分比。
    deploy_score = max(0, min(100, (deploy_proxy_value - 20) / 180 * 100))

    # 生态速度：直接传入 0-100
    os_score = max(0, min(100, os_velocity_score))

    osci = (0.20 * cap_score + 0.35 * price_score +
            0.30 * deploy_score + 0.15 * os_score)

    return round(osci, 1), cap_score, price_score, deploy_score, os_score


def get_state(osci):
    if osci < 25:
        return "SAFE", "green", "22c55e", "Closed-source premium intact", "闭源护城河稳固，技术代差明显，商业溢价成立。"
    elif osci < 45:
        return "WATCH", "yellow", "fbbf24", "Open-source convergence accelerating", "开源追赶加速，中小企业和个人开发者迁移信号出现，大客户尚未动摇。"
    elif osci < 65:
        return "WARNING", "orange", "f97316", "Commercial moat under pressure", "商业护城河受压：API降价、本地部署增加、中小客户流失加速。"
    else:
        return "CRITICAL", "red", "ef4444", "Monetization compression detected", "货币化能力开始恶化：开始监控云厂商 inference margin 与大客户续签率。"


# =========================================================
# 顶部标题
# =========================================================

render_header("🔬 开源商业化压缩", "核心监测维度：AI智力垄断是否正在被开源生态商品化", symbol="OSCI · 开源压缩指数")

capability = render_capability_controls()
cap_metrics = capability["metrics"]

# =========================================================
# 数据加载
# =========================================================

with st.spinner("正在从 OpenRouter · GitHub · HuggingFace 拉取实时数据..."):
    price_data   = load_prices(capability)
    deployment_data = load_deployment()
    ecology_data = load_ecology(capability)

# =========================================================
# 指标1：同版固定任务的相对得分差距
# =========================================================

closed_avg = cap_metrics["closed_avg"]
open_avg = cap_metrics["open_avg"]
cap_gap_pct = cap_metrics["risk_gap"]

if cap_gap_pct > 12:
    cap_color, cap_arrow, cap_status = "green", "↗", "SAFE"
elif cap_gap_pct > 6:
    cap_color, cap_arrow, cap_status = "yellow", "→", "WATCH"
elif cap_gap_pct > 2:
    cap_color, cap_arrow, cap_status = "orange", "↘", "WARNING"
else:
    cap_color, cap_arrow, cap_status = "red", "↓", "CRITICAL"

# =========================================================
# 指标2：Token 价格压缩
# =========================================================

if price_data["available"]:
    avg_closed_price = price_data["metrics"]["closed_avg"]
    avg_open_price = price_data["metrics"]["open_avg"]
    price_ratio = price_data["metrics"]["ratio"]
    price_compression_pct = price_data["metrics"]["compression"]

    if price_compression_pct < 30:
        price_color, price_arrow, price_status = "green", "↗", "SAFE"
    elif price_compression_pct < 55:
        price_color, price_arrow, price_status = "yellow", "→", "WATCH"
    elif price_compression_pct < 75:
        price_color, price_arrow, price_status = "orange", "↘", "WARNING"
    else:
        price_color, price_arrow, price_status = "red", "↓", "CRITICAL"
    price_data_ok = True
else:
    avg_closed_price     = 0
    avg_open_price       = 0
    price_ratio          = None
    price_compression_pct = 0  # Internal argument only; not displayed or scored when unavailable.
    price_color, price_arrow, price_status = "gray", "—", "N/A"
    price_data_ok = False

# =========================================================
# 指标3：开源部署动能（GitHub stars 总量作为代理）
# =========================================================

deploy_data_ok = deployment_data["available"]
if deploy_data_ok:
    total_stars = deployment_data["metrics"]["total_stars"]
    deploy_proxy_value = deployment_data["metrics"]["proxy_value"]
    deploy_status = deployment_data["metrics"]["state"]
    deploy_color, deploy_arrow = {"SAFE": ("green", "↗"), "WATCH": ("yellow", "→"),
                                 "WARNING": ("orange", "↘"), "CRITICAL": ("red", "↓")}[deploy_status]
else:
    total_stars = None
    deploy_proxy_value = 0  # Internal call only; discarded below, never a missing-data score.
    deploy_color, deploy_arrow, deploy_status = "gray", "—", "N/A"

# =========================================================
# 指标4：开源生态速度（HuggingFace 下载量）
# =========================================================

vel_data_ok = ecology_data["available"]
if vel_data_ok:
    total_downloads = ecology_data["metrics"]["total_downloads"]
    os_velocity_score = ecology_data["metrics"]["score"]
    vel_status = ecology_data["metrics"]["state"]
    vel_color, vel_arrow = {"SAFE": ("green", "↗"), "WATCH": ("yellow", "→"),
                           "WARNING": ("orange", "↘"), "CRITICAL": ("red", "↓")}[vel_status]
else:
    total_downloads = None
    os_velocity_score = 0  # Internal call only; not used as a missing-data score.
    vel_color, vel_arrow, vel_status = "gray", "—", "N/A"

# =========================================================
# OSCI 综合评分
# =========================================================

osci, cap_s, price_s, deploy_s, vel_s = compute_osci(
    cap_gap_pct, price_compression_pct, deploy_proxy_value, os_velocity_score
)
if price_data_ok and deploy_data_ok and vel_data_ok:
    register_score("straw2", osci)
    state, state_color, state_hex, state_eng, state_cn = get_state(osci)
else:
    osci = None
    if not price_data_ok:
        price_s = None
    if not deploy_data_ok:
        deploy_s = None
    if not vel_data_ok:
        vel_s = None
    st.session_state.get("straw_scores", {}).pop("straw2", None)
    state, state_color, state_hex = "N/A", "gray", "94a3b8"
    state_eng = "Price evidence incomplete" if not price_data_ok else "Deployment evidence incomplete" if not deploy_data_ok else "Ecology evidence incomplete"
    missing = []
    if not price_data_ok:
        missing.append("本期六型号输入价格不完整")
    if not deploy_data_ok:
        missing.append(f"部署工具仓库覆盖不足（{deployment_data['coverage']}/3）")
    if not vel_data_ok:
        missing.append(f"本期模型下载资料覆盖不足（{ecology_data['coverage']}/3）")
    state_cn = "；".join(missing) + "。暂不输出完整OSCI；不补预设值、不把少取数据当作风险下降。"

# =========================================================
# OSCI 总分大卡片
# =========================================================

bar_color_map = {
    "green": "#22c55e",
    "yellow": "#fbbf24",
    "orange": "#f97316",
    "red": "#ef4444"
}
bar_color = bar_color_map.get(state_color, "#94a3b8")

st.markdown(render_osci_card(
    "OPEN SOURCE COMPRESSION INDEX", osci, state, f"综合评分：{state_cn}",
    bar_color=bar_color, state_detail=state_eng,
    components_html="能力代差 ×0.20 · 价格压缩 ×0.35<br>部署动能 ×0.30 · 生态速度 ×0.15",
    score_display=f"{osci:.0f}" if osci is not None else "N/A",
), unsafe_allow_html=True)

# =========================================================
# 四张指标卡片
# =========================================================

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(metric_card(
        '能力代差 <span class="source-tag">LiveBench · 独立刷新</span>',
        f"{cap_metrics['signed_gap']:+.2f}%", cap_color, cap_arrow,
        f'{escape(capability["closed_model"])} vs {escape(capability["open_model"])}<br>'
        f'平台总分均值 {closed_avg:.3f} vs {open_avg:.3f} · 能力状态 {cap_status}<br>'
        f'全部{capability.get("task_count", 3)}项测试 · 分项 {cap_metrics["score"]:.2f}/60 · 评测版本 {capability["release"]}',
    ), unsafe_allow_html=True)

with c2:
    if price_data_ok:
        display_ratio = f"{price_ratio:.1f}%"
        desc2 = f"同本期能力样本：中国开放权重组均价为美国闭源组的 {price_ratio:.1f}%<br>输入均价 ${avg_closed_price:.4f}/M vs ${avg_open_price:.4f}/M · 各3家；输出价不计分"
    else:
        display_ratio = "N/A"
        desc2 = f"本期同型号输入价覆盖 {price_data['coverage']}/6<br>不足两组各3家，暂不计算价格分；详见下方价格依据"
    st.markdown(metric_card('价格压缩 <span class="source-tag">OpenRouter</span>', display_ratio,
                            price_color, price_arrow, desc2), unsafe_allow_html=True)

with c3:
    if deploy_data_ok:
        stars_display = f"{total_stars/1000:.0f}K"
        desc3 = f"Ollama＋vLLM＋llama.cpp 合计 {total_stars:,} stars · 覆盖3/3<br>自主部署工具累计关注度代理；不是实际部署量或增速"
    else:
        stars_display = "N/A"
        desc3 = f"仓库覆盖 {deployment_data['coverage']}/3，暂不评分<br>不把缺失仓库当作0；详见下方取数状态"
    st.markdown(metric_card('部署动能 <span class="source-tag">GitHub</span>', stars_display,
                            deploy_color, deploy_arrow, desc3), unsafe_allow_html=True)

with c4:
    if vel_data_ok:
        dl_display = f"{total_downloads/1_000_000:.1f}M" if total_downloads > 1_000_000 else f"{total_downloads/1000:.0f}K"
        desc4 = f"本期三家入选模型近30天下载合计 {total_downloads:,} · 覆盖3/3<br>下载热度代理，非平台整体规模或增长率；更换样本不直接比较旧分"
    else:
        dl_display = "N/A"
        desc4 = f"本期三模型下载覆盖 {ecology_data['coverage']}/3，暂不评分<br>缺失不填0，不以旧型号或衍生版补足"
    st.markdown(metric_card('生态速度 <span class="source-tag">HuggingFace</span>', dl_display,
                            vel_color, vel_arrow, desc4), unsafe_allow_html=True)

# =========================================================
# Alert 结论框
# =========================================================

alert_map = {
    "SAFE": {
        "box_class": "alert-box-green",
        "icon": "✅",
        "title_color": "#22c55e",
        "title": "结论：闭源护城河稳固，AI商业溢价仍然成立",
        "body": f'当前 OSCI = <span class="green"><b>{osci}</b></span>，处于安全区间。闭源模型在能力、定价和企业服务上仍具明显优势，大规模商业迁移的经济动因不足。建议持续追踪价格压缩速度。'
    },
    "WATCH": {
        "box_class": "alert-box",
        "icon": "👁",
        "title_color": "#fbbf24",
        "title": "结论：开源收敛加速，商业护城河出现早期压力",
        "body": f'当前 OSCI = <span class="yellow"><b>{osci}</b></span>，进入观察区间。开源模型技术追赶加速、价格剪刀差扩大，中小企业和个人开发者开始流向开源体系。大型企业迁移尚未启动，闭源财务数据仍健康。建议关注云厂商下季度 inference margin 变化。'
    },
    "WARNING": {
        "box_class": "alert-box",
        "icon": "⚠️",
        "title_color": "#f97316",
        "title": "结论：商业护城河受压，开始出现可量化的货币化侵蚀",
        "body": f'当前 OSCI = <span class="orange"><b>{osci}</b></span>，进入高危区间。API降价幅度超过防御性阈值，本地部署生态快速扩张，中小客户流失加速。注意：这是商业侵蚀信号，尚未构成金融传导事件。建议对纯 API 订阅驱动的 AI 公司开始估值减记。'
    },
    "CRITICAL": {
        "box_class": "alert-box-red",
        "icon": "🔴",
        "title_color": "#ef4444",
        "title": "结论：货币化能力恶化，需联动资本开支数据确认传导",
        "body": f'当前 OSCI = <span class="red"><b>{osci}</b></span>，进入危机区间。开源对闭源的商业侵蚀已可量化。注意：本因子只监控开源商业化压缩，CASCADE 事件（GPU订单取消/数据中心减值/ABS风险）需要资本开支偏离同步触发才能确认。当前建议：监控云厂商下一份财报的 AI 服务收入增速与 inference gross margin。'
    }
}

alert = alert_map.get(state, {"title": "结论：必要资料不完整，暂不判断完整OSCI状态", "body": state_cn})
st.markdown(render_alert(state, alert["title"], alert["body"]), unsafe_allow_html=True)

# =========================================================
# 主图直接展示；计算方法与原始分项值留在底部标签页。
# =========================================================

def _render_detection_logic():
    sections = [
        ("1", "能力代差（×0.20）",
         "读取同一Git提交的最新一期LiveBench全部测试列；单型号总分=全部测试成绩之和。各平台选最高完整型号/档位，美国闭源与中国开放权重各取不同平台前三家，分别平均得C与O。相对差距=(C－O)÷C×100%；保留正负值展示，风险输入取max(0,相对差距)。能力分=clamp[60×(25－输入)÷25,0,60]。缺项不补0、不足三家不采用；半年建议复核，未设定时。不是官方七类等权综合分。闭源优势越大风险贡献越低，不直接抵扣价格分；2/6/12/25参数仍是未校准研究规则。",
         ["🟢 代差 > 12% · SAFE", "🟡 6% < 相对代差 ≤ 12% · WATCH",
          "🟠 2% < 相对代差 ≤ 6% · WARNING", "🔴 相对代差 ≤ 2% · CRITICAL"]),
        ("2", "价格压缩（×0.35）",
         "使用能力代差本期选中的美国闭源、中国开放权重各三家确切型号。各组输入单价求和÷3，R=中国组均价÷美国组均价×100%，P=max(0,100－R)，价格分=clamp[(P－10)÷50×100,0,100]。单位USD/百万Token，输出价只展示；不使用缓存、batch及相似型号补价。保留旧阈值和35%权重，状态与分数映射仍是两套既有研究规则；缺价不计算完整OSCI。",
         ["🟢 开源价格 > 70% 闭源 · SAFE", "🟡 开源价格 45–70% 闭源 · WATCH",
          "🟠 开源价格 25–45% 闭源 · WARNING", "🔴 开源价格 < 25% 闭源 · CRITICAL"]),
        ("3", "部署动能（×0.30；自主部署工具关注度代理）",
         "固定Ollama、vLLM、llama.cpp三仓库累计stars求和S；按S<150,000/300,000/500,000及其以上映射为30/80/140/220，再以clamp[(映射值－20)÷180×100,0,100]计算。映射值不是增长百分比；不等于企业部署量或迁移事实。保留原阈值、公式及30%权重，三项不完整不评分，不补预设数字。",
         ["🟢 S < 150,000 · 代理值30 · SAFE", "🟡 150,000 ≤ S < 300,000 · 代理值80 · WATCH",
          "🟠 300,000 ≤ S < 500,000 · 代理值140 · WARNING", "🔴 S ≥ 500,000 · 代理值220 · CRITICAL"]),
        ("4", "生态速度（×0.15；本期入选模型下载热度代理）",
         "从本期能力代差选中的三家中国开放权重模型元数据中读取官方Hugging Face仓库，各取downloads字段（最近30天滚动窗口）后求和D。暂沿用D<50万/200万/800万及以上对应15/40/65/85分和15%权重；三项必须完整，不填0或预设30分。不是整个平台生态、去重用户或真实增长率；新三模型替换旧四模型有方法断点，旧阈值未重校准，不直接解释新旧分差。",
         ["🟢 D < 50万 · 15分 · SAFE", "🟡 50万 ≤ D < 200万 · 40分 · WATCH",
          "🟠 200万 ≤ D < 800万 · 65分 · WARNING", "🔴 D ≥ 800万 · 85分 · CRITICAL"]),
    ]
    for number, title, explanation, thresholds in sections:
        with st.expander(f"{number}　{title}", expanded=False):
            st.write(explanation)
            st.markdown("**评分规则**")
            for line in thresholds:
                st.markdown(line)

with st.container(border=True):
    st.markdown('<div class="panel-title">📊 指标分项评分（OSCI 构成）</div>', unsafe_allow_html=True)

    categories = ["能力代差", "价格压缩", "部署动能", "生态速度"]
    scores     = [cap_s, price_s, deploy_s, vel_s]
    weights    = [0.20, 0.35, 0.30, 0.15]
    colors_bar = []
    for s in scores:
        if s is None:
            colors_bar.append("#94a3b8")
        elif s < 25:
            colors_bar.append("#22c55e")
        elif s < 50:
            colors_bar.append("#fbbf24")
        elif s < 75:
            colors_bar.append("#f97316")
        else:
            colors_bar.append("#ef4444")

    weighted_scores = [s * w if s is not None else None for s, w in zip(scores, weights)]
    # Capability status is defined by the relative-gap thresholds, not generic score bins.
    colors_bar[0] = bar_color_map[cap_color]
    bar_labels = [f"{c}  ×{w:.2f}  →  " + (f"{s:.0f}分" if s is not None else "N/A（缺失）") for c, w, s in zip(categories, weights, scores)]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=scores,
        y=bar_labels,
        orientation="h",
        marker_color=colors_bar,
        marker_line_width=0,
        width=0.55,
        text=[f"{s:.0f}" if s is not None else "N/A" for s in scores],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=16),
    ))

    if osci is not None:
        fig.add_shape(
            type="line", x0=osci, x1=osci, y0=-0.5, y1=3.5,
            line=dict(color="rgba(255,255,255,0.3)", width=1.5, dash="dash")
        )
        fig.add_annotation(
            x=osci, y=3.6, text=f"OSCI={osci}", showarrow=False,
            font=dict(color="#94a3b8", size=14), xanchor="center"
        )

    fig.update_layout(
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#94a3b8", size=12),
        margin=dict(l=10, r=60, t=30, b=10),
        xaxis=dict(
            range=[0, 105],
            showgrid=True,
            gridcolor="rgba(255,255,255,0.05)",
            zeroline=False,
            tickfont=dict(color="#94a3b8", size=11),
        ),
        yaxis=dict(
            showgrid=False,
            tickfont=dict(color="#94a3b8", size=15),
        ),
        bargap=0.35,
    )

    st.plotly_chart(fig, use_container_width=True)

    # 数据来源状态行
    repo_tags = [f'<span class="source-tag-gray">{escape(r["name"])}: ' +
                 (f'{r["stars"]//1000}K ★' if r["stars"] is not None else 'N/A') + '</span>'
                 for r in deployment_data["rows"]]

    st.markdown(source_tag_row([
        f'<span class="source-tag">OpenRouter 输入价 {price_data["coverage"]}/6</span>',
        f'<span class="source-tag">GitHub 仓库覆盖 {deployment_data["coverage"]}/3</span>',
        f'<span class="source-tag">Hugging Face 模型覆盖 {ecology_data["coverage"]}/3</span>',
        *repo_tags,
    ]), unsafe_allow_html=True)

# =========================================================
# 页脚
# =========================================================

# =========================================================
# 底部注释：静态基准数据说明
# =========================================================

logic_tab, evidence_tab, source_tab = st.tabs(["检测逻辑", "指标与历史证据", "数据覆盖与来源"])
with logic_tab:
    with st.container(key="open_source_detection_logic"):
        _render_detection_logic()
with evidence_tab:
    current_quarter = make_current_snapshot(capability, price_data, deployment_data, ecology_data)
    quarterly_history = load_quarterly_history()
    render_current_quarter(current_quarter, container_key="open_source_quarterly_current")
    legacy_evidence = {
        "capability": {"legacy": capability_store.baseline()["legacy"], "records": capability_store.history()},
        "price": price_history(),
        "deployment": deployment_history(),
        "ecology": ecology_history(),
    }
    render_quarterly_history(
        quarterly_history, current_quarter, legacy_evidence,
        container_key="open_source_quarterly_history", page_number="02",
        page_title="开源商业化压缩", file_prefix="factor02-open-source",
        method_summary=[
            "能力代差使用同版LiveBench全部测试、两组三平台；独立检查更新。",
            "价格压缩使用本期能力样本对应的OpenRouter输入基础价。",
            "部署动能使用Ollama、vLLM、llama.cpp累计stars代理。",
            "生态速度使用本期三家开放权重模型的Hugging Face近30天下载量。",
        ],
    )

with source_tab:
    render_data_freshness([
        {"name": "模型价格", "source": f"OpenRouter API · 输入价覆盖{price_data['coverage']}/6", "updated_at": price_data["checked_at"], "mode": "live"},
        {"name": "自主部署工具关注度", "source": f"GitHub REST · 仓库覆盖{deployment_data['coverage']}/3", "updated_at": deployment_data["checked_at"], "mode": "live"},
        {"name": "本期入选模型下载热度", "source": f"Hugging Face API · 近30天 · 模型覆盖{ecology_data['coverage']}/3", "updated_at": ecology_data["checked_at"], "mode": "live"},
    ])
    st.caption(f"能力基准：LiveBench全部测试／两组三平台 · 评测版本 {capability['release']} · "
               f"已保存快照读取时间 {capability['checked_at']} · 模型测试日期未提供。独立按钮检查更新。")
render_footer(f'OpenRouter API · GitHub REST API · HuggingFace API · LiveBench评测版本 {capability["release"]}（模型测试日期未提供）')
