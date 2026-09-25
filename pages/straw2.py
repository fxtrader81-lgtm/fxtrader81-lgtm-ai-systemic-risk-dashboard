import streamlit as st
import requests
import plotly.graph_objects as go
from components.ui import (load_css, logic_panel, metric_card, note_panel,
                           render_data_freshness, render_footer, render_header,
                           source_tag_row)
from core.alert_engine import render_alert, render_osci_card
from core.score_engine import register_score

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
# 静态基准数据（每季度人工更新一次）
# 记录主流模型在核心 benchmark 上的最新得分
# =========================================================

BENCHMARK_DATA = {
    "closed": {
        "name": "GPT-4o (2024-11)",
        "mmlu": 85.7,
        "humaneval": 90.2,
        "math": 76.6,
        "updated": "2025-01"
    },
    "open": {
        "name": "DeepSeek-V3",
        "mmlu": 88.5,
        "humaneval": 89.1,
        "math": 75.7,
        "updated": "2025-01"
    }
}

# =========================================================
# 数据获取函数
# =========================================================

@st.cache_data(ttl=3600)
def get_openrouter_prices():
    """从 OpenRouter 获取主流模型实时价格"""
    data = fetch_json("https://openrouter.ai/api/v1/models")
    if not data or "data" not in data:
        return None

    targets = {
        "closed": [
            "openai/gpt-4o",
            "openai/gpt-4o-2024-11-20",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-pro-1.5",
        ],
        "open": [
            "meta-llama/llama-3.3-70b-instruct",
            "deepseek/deepseek-chat",
            "qwen/qwen-2.5-72b-instruct",
            "mistralai/mistral-large",
        ]
    }

    results = {"closed": [], "open": []}
    for model in data["data"]:
        mid = model.get("id", "")
        pricing = model.get("pricing", {})
        try:
            prompt_price = float(pricing.get("prompt", 0)) * 1_000_000
        except:
            prompt_price = 0

        if prompt_price <= 0:
            continue

        for category, ids in targets.items():
            if any(mid.startswith(t) or t in mid for t in ids):
                results[category].append({
                    "id": mid,
                    "name": model.get("name", mid),
                    "price_per_m": prompt_price
                })

    return results if (results["closed"] or results["open"]) else None


@st.cache_data(ttl=3600)
def get_github_stars():
    """从 GitHub API 获取主流开源推理框架的 star 数"""
    repos = {
        "ollama": "ollama/ollama",
        "vllm": "vllm-project/vllm",
        "llama.cpp": "ggerganov/llama.cpp",
        "lm-studio": "lmstudio-ai/lmstudio-community",
    }
    results = {}
    headers = {"Accept": "application/vnd.github.v3+json"}
    for name, repo in repos.items():
        data = fetch_json(f"https://api.github.com/repos/{repo}", headers=headers)
        if data and "stargazers_count" in data:
            results[name] = {
                "stars": data["stargazers_count"],
                "forks": data.get("forks_count", 0),
                "watchers": data.get("watchers_count", 0),
            }
    return results if results else None


@st.cache_data(ttl=3600)
def get_hf_downloads():
    """从 HuggingFace 获取顶级开源模型下载趋势"""
    models = [
        "meta-llama/Llama-3.3-70B-Instruct",
        "deepseek-ai/DeepSeek-V3",
        "Qwen/Qwen2.5-72B-Instruct",
        "mistralai/Mistral-Large-Instruct-2411",
    ]
    results = []
    for m in models:
        data = fetch_json(f"https://huggingface.co/api/models/{m}")
        if data:
            results.append({
                "name": m.split("/")[-1],
                "downloads": data.get("downloads", 0),
                "likes": data.get("likes", 0),
            })
    return results if results else None


# =========================================================
# OSCI 评分计算
# =========================================================

def compute_osci(cap_gap_pct, price_compression_pct, deploy_growth_pct, os_velocity_score):
    """
    OSCI = 0.20 x cap + 0.35 x price + 0.30 x deploy + 0.15 x velocity
    各分项标准化到 0-100，越高代表开源对闭源商业侵蚀风险越大

    权重逻辑：
    能力代差降至0.20：benchmark追平是技术事实，商业传导滞后12-18个月
    价格压缩升至0.35：最直接的商业信号，定价权松动立即影响营收
    部署动能升至0.30：企业真正开始动脚才是商业侵蚀的实质证据
    生态速度保持0.15：领先指标，辅助验证

    商业粘性缓冲（关键）：
    能力代差即使归零，分项上限压至60而非100
    原因：SOC2/HIPAA/SLA/多区域部署/企业支持等商业壁垒
    不会因benchmark追平而立即消失
    """

    # 能力代差：上限60分（商业粘性缓冲）
    # gap > 25% -> 0分; gap <= 0% -> 60分
    cap_score = max(0, min(60, (25 - cap_gap_pct) / 25 * 60))

    # 价格压缩：压缩幅度越大风险越高
    # 压缩 < 10% -> 0分; 压缩 > 60% -> 100分
    price_score = max(0, min(100, (price_compression_pct - 10) / 50 * 100))

    # 部署动能：stars总量映射
    # 增长 < 20% -> 0分; 增长 > 200% -> 100分
    deploy_score = max(0, min(100, (deploy_growth_pct - 20) / 180 * 100))

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

# =========================================================
# 数据加载
# =========================================================

with st.spinner("正在从 OpenRouter · GitHub · HuggingFace 拉取实时数据..."):
    price_data   = get_openrouter_prices()
    github_data  = get_github_stars()
    hf_data      = get_hf_downloads()

# =========================================================
# 指标1：能力代差（静态基准）
# =========================================================

closed_avg = (BENCHMARK_DATA["closed"]["mmlu"] +
              BENCHMARK_DATA["closed"]["humaneval"] +
              BENCHMARK_DATA["closed"]["math"]) / 3

open_avg   = (BENCHMARK_DATA["open"]["mmlu"] +
              BENCHMARK_DATA["open"]["humaneval"] +
              BENCHMARK_DATA["open"]["math"]) / 3

cap_gap_pct = max(0, closed_avg - open_avg)

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

if price_data and price_data["closed"] and price_data["open"]:
    closed_prices = [m["price_per_m"] for m in price_data["closed"]]
    open_prices   = [m["price_per_m"] for m in price_data["open"]]
    avg_closed_price = sum(closed_prices) / len(closed_prices)
    avg_open_price   = sum(open_prices)   / len(open_prices)
    price_ratio      = avg_open_price / avg_closed_price * 100  # 开源/闭源 %
    price_compression_pct = max(0, 100 - price_ratio)           # 闭源贵了多少%

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
    price_ratio          = 50
    price_compression_pct = 40
    price_color, price_arrow, price_status = "gray", "—", "N/A"
    price_data_ok = False

# =========================================================
# 指标3：开源部署动能（GitHub stars 总量作为代理）
# =========================================================

if github_data:
    total_stars = sum(v["stars"] for v in github_data.values())
    # 用 stars 总量做阶梯判断（参考：ollama 2025年初 ~120k stars）
    # 50k以下=低，50-150k=中，150-300k=高，300k+=极高
    if total_stars < 150_000:
        deploy_growth_pct = 30
        deploy_color, deploy_arrow, deploy_status = "green", "↗", "SAFE"
    elif total_stars < 300_000:
        deploy_growth_pct = 80
        deploy_color, deploy_arrow, deploy_status = "yellow", "→", "WATCH"
    elif total_stars < 500_000:
        deploy_growth_pct = 140
        deploy_color, deploy_arrow, deploy_status = "orange", "↘", "WARNING"
    else:
        deploy_growth_pct = 220
        deploy_color, deploy_arrow, deploy_status = "red", "↓", "CRITICAL"
    deploy_data_ok = True
else:
    total_stars       = 0
    deploy_growth_pct = 50
    deploy_color, deploy_arrow, deploy_status = "gray", "—", "N/A"
    deploy_data_ok = False

# =========================================================
# 指标4：开源生态速度（HuggingFace 下载量）
# =========================================================

if hf_data:
    total_downloads = sum(m["downloads"] for m in hf_data)
    total_likes     = sum(m["likes"]     for m in hf_data)
    # 下载量阶梯：月下载量代理生态热度
    if total_downloads < 500_000:
        os_velocity_score = 15
        vel_color, vel_arrow, vel_status = "green", "↗", "SAFE"
    elif total_downloads < 2_000_000:
        os_velocity_score = 40
        vel_color, vel_arrow, vel_status = "yellow", "→", "WATCH"
    elif total_downloads < 8_000_000:
        os_velocity_score = 65
        vel_color, vel_arrow, vel_status = "orange", "↘", "WARNING"
    else:
        os_velocity_score = 85
        vel_color, vel_arrow, vel_status = "red", "↓", "CRITICAL"
    vel_data_ok = True
else:
    total_downloads   = 0
    os_velocity_score = 30
    vel_color, vel_arrow, vel_status = "gray", "—", "N/A"
    vel_data_ok = False

# =========================================================
# OSCI 综合评分
# =========================================================

osci, cap_s, price_s, deploy_s, vel_s = compute_osci(
    cap_gap_pct, price_compression_pct, deploy_growth_pct, os_velocity_score
)
register_score("straw2", osci)

state, state_color, state_hex, state_eng, state_cn = get_state(osci)

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
    score_display=f"{osci:.0f}",
), unsafe_allow_html=True)

# =========================================================
# 四张指标卡片
# =========================================================

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(metric_card(
        '能力代差 <span class="source-tag-gray static-data-badge">⚠ 静态基准</span>',
        f"{cap_gap_pct:+.1f}%", cap_color, cap_arrow,
        f'{BENCHMARK_DATA["closed"]["name"]} vs {BENCHMARK_DATA["open"]["name"]}<br>'
        f'均分 {closed_avg:.1f} vs {open_avg:.1f} · 数据期 {BENCHMARK_DATA["closed"]["updated"]}',
    ), unsafe_allow_html=True)

with c2:
    if price_data_ok:
        display_ratio = f"{price_ratio:.1f}%"
        desc2 = f"开源托管均价仅为闭源的 {price_ratio:.1f}%<br>闭源均价 ${avg_closed_price:.2f}/M · 开源 ${avg_open_price:.2f}/M"
    else:
        display_ratio = "N/A"
        desc2 = "OpenRouter 数据暂时无法获取<br>请稍后刷新重试"
    st.markdown(metric_card('价格压缩 <span class="source-tag">OpenRouter</span>', display_ratio,
                            price_color, price_arrow, desc2), unsafe_allow_html=True)

with c3:
    if deploy_data_ok:
        stars_display = f"{total_stars/1000:.0f}K"
        desc3 = f"ollama+vLLM+llama.cpp 合计 {stars_display} stars<br>星标总量反映本地部署生态规模"
    else:
        stars_display = "N/A"
        desc3 = "GitHub API 数据暂时无法获取<br>请稍后刷新重试"
    st.markdown(metric_card('部署动能 <span class="source-tag">GitHub</span>', stars_display,
                            deploy_color, deploy_arrow, desc3), unsafe_allow_html=True)

with c4:
    if vel_data_ok:
        dl_display = f"{total_downloads/1_000_000:.1f}M" if total_downloads > 1_000_000 else f"{total_downloads/1000:.0f}K"
        desc4 = f"顶级开源模型合计下载 {dl_display}<br>反映开源生态扩张速度与市场渗透率"
    else:
        dl_display = "N/A"
        desc4 = "HuggingFace 数据暂时无法获取<br>请稍后刷新重试"
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

alert = alert_map.get(state, alert_map["WATCH"])
st.markdown(render_alert(state, alert["title"], alert["body"]), unsafe_allow_html=True)

# =========================================================
# 主图直接展示；计算方法与原始分项值留在底部标签页。
# =========================================================

def _render_detection_logic():
    st.markdown(logic_panel([
        {"text": "<b>能力代差（×0.20）</b>：对比闭源与开源顶级模型在 MMLU、HumanEval、MATH 三项 benchmark 的均值差距", "thresholds": [
            ("#22c55e", "代差 > 12%", "SAFE", "green"),
            ("#fbbf24", "代差 6–12%", "WATCH", "yellow"),
            ("#f97316", "代差 2–6%", "WARNING", "orange"),
            ("#ef4444", "代差 < 2%", "CRITICAL", "red"),
        ]},
        {"text": "<b>价格压缩（×0.35）</b>：OpenRouter 实时价格，计算开源托管均价占闭源均价的比例", "thresholds": [
            ("#22c55e", "开源价格 > 70% 闭源", "SAFE", "green"),
            ("#fbbf24", "开源价格 45–70% 闭源", "WATCH", "yellow"),
            ("#f97316", "开源价格 25–45% 闭源", "WARNING", "orange"),
            ("#ef4444", "开源价格 < 25% 闭源", "CRITICAL", "red"),
        ]},
        {"text": "<b>部署动能（×0.30）</b>：GitHub stars 总量作为企业本地化迁移意图的领先指标"},
        {"text": "<b>生态速度（×0.15）</b>：HuggingFace 顶级开源模型下载量，反映市场渗透加速度"},
    ]), unsafe_allow_html=True)

with st.container(border=True):
    st.markdown('<div class="panel-title">📊 指标分项评分（OSCI 构成）</div>', unsafe_allow_html=True)

    categories = ["能力代差", "价格压缩", "部署动能", "生态速度"]
    scores     = [cap_s, price_s, deploy_s, vel_s]
    weights    = [0.20, 0.35, 0.30, 0.15]
    colors_bar = []
    for s in scores:
        if s < 25:
            colors_bar.append("#22c55e")
        elif s < 50:
            colors_bar.append("#fbbf24")
        elif s < 75:
            colors_bar.append("#f97316")
        else:
            colors_bar.append("#ef4444")

    weighted_scores = [s * w for s, w in zip(scores, weights)]
    bar_labels = [f"{c}  ×{w:.2f}  →  {s:.0f}分" for c, w, s in zip(categories, weights, scores)]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=scores,
        y=bar_labels,
        orientation="h",
        marker_color=colors_bar,
        marker_line_width=0,
        width=0.55,
        text=[f"{s:.0f}" for s in scores],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=16),
    ))

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
    src_ollama = f"ollama: {github_data['ollama']['stars']//1000}K ★" if github_data and 'ollama' in github_data else "ollama: N/A"
    src_vllm   = f"vLLM: {github_data['vllm']['stars']//1000}K ★"   if github_data and 'vllm'   in github_data else "vLLM: N/A"
    src_llama  = f"llama.cpp: {github_data['llama.cpp']['stars']//1000}K ★" if github_data and 'llama.cpp' in github_data else "llama.cpp: N/A"

    st.markdown(source_tag_row([
        '<span class="source-tag">OpenRouter ✓</span>',
        '<span class="source-tag">GitHub ✓</span>',
        '<span class="source-tag">HuggingFace ✓</span>',
        f'<span class="source-tag-gray">{src_ollama}</span>',
        f'<span class="source-tag-gray">{src_vllm}</span>',
        f'<span class="source-tag-gray">{src_llama}</span>',
    ]), unsafe_allow_html=True)

# =========================================================
# 页脚
# =========================================================

# =========================================================
# 底部注释：静态基准数据说明
# =========================================================

st.markdown(note_panel("⚠ 静态基准数据说明（能力代差指标）", f"""
    <b>当前数据：</b>
    闭源基准 = {BENCHMARK_DATA["closed"]["name"]}（MMLU {BENCHMARK_DATA["closed"]["mmlu"]} / HumanEval {BENCHMARK_DATA["closed"]["humaneval"]} / MATH {BENCHMARK_DATA["closed"]["math"]}）<br>
    <b>对比模型：</b>
    开源基准 = {BENCHMARK_DATA["open"]["name"]}（MMLU {BENCHMARK_DATA["open"]["mmlu"]} / HumanEval {BENCHMARK_DATA["open"]["humaneval"]} / MATH {BENCHMARK_DATA["open"]["math"]}）<br>
    <b>录入时间：</b>{BENCHMARK_DATA["closed"]["updated"]} &nbsp;·&nbsp;
    <b>建议更新频率：</b>每季度一次，或主要新模型发布后 &nbsp;·&nbsp;
    <b>更新位置：</b>代码顶部 BENCHMARK_DATA 字典<br>
    <b>权重说明：</b>能力代差仅占 OSCI 权重的 20%，且上限压至 60 分（商业粘性缓冲）。
    Benchmark 追平不等于商业崩塌，企业迁移滞后周期约 12–18 个月。
"""), unsafe_allow_html=True)

logic_tab, evidence_tab, source_tab = st.tabs(["检测逻辑", "指标与历史证据", "数据覆盖与来源"])
with logic_tab:
    _render_detection_logic()
with evidence_tab:
    st.markdown('<div class="panel-title">📋 OSCI 分项原始评分</div>', unsafe_allow_html=True)
    st.dataframe([
        {"指标": category, "权重": f"{weight:.0%}", "分项评分": round(score, 1),
         "加权贡献": round(score * weight, 1)}
        for category, weight, score in zip(categories, weights, scores)
    ], use_container_width=True, hide_index=True)

with source_tab:
    render_data_freshness([
        {"name": "模型价格", "source": "OpenRouter API", "updated_at": "每小时缓存", "mode": "live"},
        {"name": "开发者生态", "source": "GitHub REST · Hugging Face API", "updated_at": "每小时缓存", "mode": "live"},
        {"name": "能力基准", "source": "季度人工复核", "updated_at": BENCHMARK_DATA["closed"]["updated"], "mode": "static"},
    ])
render_footer(f'OpenRouter API · GitHub REST API · HuggingFace API · Benchmark 静态维护（{BENCHMARK_DATA["closed"]["updated"]}）')
