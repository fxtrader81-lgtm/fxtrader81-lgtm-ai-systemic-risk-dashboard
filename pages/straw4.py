import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime, date

# =========================================================
# 页面配置
# =========================================================

st.set_page_config(
    page_title="稻草四：全球AI能源控制体系失效",
    layout="wide"
)

# =========================================================
# CSS — 与稻草一/二/三完全一致的黑金风格
# =========================================================

st.markdown("""
<style>

html, body, [class*="css"] {
    background-color: #050816 !important;
    color: white;
    font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.stApp { background-color: #050816 !important; }
section[data-testid="stMain"] > div { background-color: #050816 !important; }
.block-container {
    padding-top: 1.8rem;
    padding-left: 2.2rem;
    padding-right: 2.2rem;
    max-width: 1600px;
    background-color: #050816 !important;
}

.main-title {
    font-size: 32px; font-weight: 800; color: #ffffff;
    margin: 0 0 6px 0; letter-spacing: -0.5px;
}
.sub-title {
    font-size: 16px !important;
    color: #cbd5e1 !important;
    margin: 0;
}
.timestamp-text { font-size: 13px; color: #475569; margin-bottom: 8px; display: block; }
.symbol-badge {
    display: inline-block;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px; padding: 3px 16px;
    font-size: 13px; font-weight: 600; color: #94a3b8; letter-spacing: 1px;
}

/* ESRI 总分大卡片 */
.osci-card {
    background: linear-gradient(135deg, #0b1120 0%, #0d1829 100%);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.osci-left { display: flex; flex-direction: column; gap: 6px; }
.osci-label { font-size: 13px; font-weight: 600; color: #475569; letter-spacing: 1.5px; text-transform: uppercase; }
.osci-score { font-size: 72px; font-weight: 800; line-height: 1; letter-spacing: -3px; }
.osci-desc { font-size: 15px; color: #94a3b8; margin-top: 4px; }
.osci-right { text-align: right; }
.osci-state-label { font-size: 13px; color: #475569; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px; }
.osci-state { font-size: 28px; font-weight: 800; letter-spacing: 0.5px; }
.osci-bar-wrap { margin-top: 12px; width: 280px; height: 6px; background: rgba(255,255,255,0.08); border-radius: 3px; }
.osci-bar-fill { height: 6px; border-radius: 3px; }

/* 指标卡片 */
.metric-card {
    background-color: #0b1120;
    border: 1px solid rgba(255,255,255,0.07);
    border-radius: 14px; padding: 20px 22px 18px;
    height: 168px;
}
.metric-label {
    color: #ffffff; font-size: 18px; font-weight: 600;
    margin-bottom: 16px; text-transform: uppercase; letter-spacing: 0.4px;
}
.metric-row { display: flex; align-items: baseline; gap: 8px; margin-bottom: 14px; }
.metric-number { font-size: 38px; font-weight: 800; line-height: 1; letter-spacing: -1.5px; }
.metric-arrow { font-size: 20px; font-weight: 700; }
.metric-desc, .metric-desc p {
    color: #cbd5e1 !important;
    font-size: 15px !important;
    line-height: 1.6;
}

.green  { color: #22c55e; }
.red    { color: #ef4444; }
.yellow { color: #fbbf24; }
.orange { color: #f97316; }
.gray   { color: #94a3b8; }
.purple { color: #a78bfa; }

/* Alert 结论框 */
.alert-box {
    margin: 18px 0; background: #120e00;
    border: 1px solid rgba(251,191,36,0.18);
    border-radius: 14px; padding: 22px 26px;
    display: flex; gap: 18px; align-items: flex-start;
}
.alert-box-red {
    margin: 18px 0; background: #120000;
    border: 1px solid rgba(239,68,68,0.25);
    border-radius: 14px; padding: 22px 26px;
    display: flex; gap: 18px; align-items: flex-start;
}
.alert-box-green {
    margin: 18px 0; background: #001208;
    border: 1px solid rgba(34,197,94,0.2);
    border-radius: 14px; padding: 22px 26px;
    display: flex; gap: 18px; align-items: flex-start;
}
.alert-icon { font-size: 44px; flex-shrink: 0; line-height: 1; }
.alert-title {
    font-size: 23px !important;
    font-weight: 700;
    margin-bottom: 10px;
}
.alert-text, .alert-text p {
    font-size: 17px !important;
    color: #cbd5e1 !important;
    line-height: 1.75;
}

/* Panel */
.panel {
    background-color: #0b1120; border-radius: 14px;
    padding: 22px; border: 1px solid rgba(255,255,255,0.07);
}
.panel-title {
    font-size: 20px !important;
    font-weight: 700;
    margin-bottom: 20px;
    color: #e2e8f0;
}

.logic-step { display: flex; gap: 12px; margin-bottom: 13px; align-items: flex-start; }
.step-num {
    width: 22px; height: 22px; min-width: 22px; border-radius: 50%;
    background: #1e3a5f; color: #60a5fa; font-size: 12px; font-weight: 700;
    display: flex; align-items: center; justify-content: center; margin-top: 2px;
}
.step-text {
    font-size: 16px !important;
    color: #cbd5e1 !important;
    line-height: 1.6;
}
.threshold-block { margin-left: 34px; margin-top: 8px; }
.threshold-row {
    display: flex; align-items: center; gap: 8px;
    padding: 7px 12px; border-radius: 7px; margin-bottom: 6px;
    background: rgba(255,255,255,0.02);
}
.t-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.t-label { font-size: 15px !important; color: #cbd5e1 !important; flex: 1; }
.t-arrow { font-size: 13px; color: #475569; }
.t-status { font-size: 15px !important; font-weight: 600; }

/* 数据源标签 */
.source-tag {
    display: inline-block;
    background: rgba(96,165,250,0.1);
    border: 1px solid rgba(96,165,250,0.2);
    border-radius: 6px; padding: 2px 10px;
    font-size: 12px; color: #60a5fa; margin-left: 8px;
}
.source-tag-gray {
    display: inline-block;
    background: rgba(148,163,184,0.1);
    border: 1px solid rgba(148,163,184,0.2);
    border-radius: 6px; padding: 2px 10px;
    font-size: 12px; color: #94a3b8; margin-left: 8px;
}
.source-tag-warn {
    display: inline-block;
    background: rgba(251,191,36,0.1);
    border: 1px solid rgba(251,191,36,0.25);
    border-radius: 6px; padding: 2px 10px;
    font-size: 12px; color: #fbbf24; margin-left: 8px;
}
/* 数据新鲜度标签 — 绿色（新鲜）*/
.freshness-ok {
    display: inline-block;
    background: rgba(34,197,94,0.08);
    border: 1px solid rgba(34,197,94,0.2);
    border-radius: 6px; padding: 2px 10px;
    font-size: 12px; color: #22c55e; margin-left: 6px;
}
/* 数据新鲜度标签 — 黄色（偏旧，30-90天）*/
.freshness-warn {
    display: inline-block;
    background: rgba(251,191,36,0.1);
    border: 1px solid rgba(251,191,36,0.3);
    border-radius: 6px; padding: 2px 10px;
    font-size: 12px; color: #fbbf24; margin-left: 6px;
}
/* 数据新鲜度标签 — 红色（过期，>90天）*/
.freshness-stale {
    display: inline-block;
    background: rgba(239,68,68,0.1);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 6px; padding: 2px 10px;
    font-size: 12px; color: #ef4444; margin-left: 6px;
    animation: blink 2s infinite;
}
@keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.5; }
}
.source-tag-purple {
    display: inline-block;
    background: rgba(167,139,250,0.1);
    border: 1px solid rgba(167,139,250,0.25);
    border-radius: 6px; padding: 2px 10px;
    font-size: 12px; color: #a78bfa; margin-left: 8px;
}

/* 反证模块 */
.counter-card {
    background: rgba(34,197,94,0.04);
    border: 1px solid rgba(34,197,94,0.12);
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 10px;
}
.counter-title {
    font-size: 14px; font-weight: 700; color: #22c55e;
    letter-spacing: 0.5px; margin-bottom: 8px;
}
.counter-body {
    font-size: 14px; color: #94a3b8; line-height: 1.6;
}

.footer-text { margin-top: 14px; color: #1e293b; font-size: 11px; text-align: right; }
#MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
.modebar { display: none !important; }

</style>
""", unsafe_allow_html=True)

# =========================================================
# 工具函数：数据新鲜度
# =========================================================

def freshness_badge(updated_str: str) -> str:
    """
    传入 'YYYY-MM' 或 'YYYY-MM-DD' 格式的更新日期字符串，
    返回带颜色的 HTML 标签，显示"距上次更新 X 天"。
    超过 90 天 → 红色闪烁警告；30-90 天 → 黄色；≤30 天 → 绿色。
    """
    try:
        if len(updated_str) == 7:           # 'YYYY-MM'
            updated_str += "-01"
        d_updated = date.fromisoformat(updated_str)
        days_ago = (date.today() - d_updated).days
        if days_ago > 90:
            css = "freshness-stale"
            label = f"⚠ 数据已 {days_ago} 天未更新"
        elif days_ago > 30:
            css = "freshness-warn"
            label = f"🕐 {days_ago} 天前更新"
        else:
            css = "freshness-ok"
            label = f"✓ {days_ago} 天前更新"
        return f'<span class="{css}">{label}</span>'
    except Exception:
        return '<span class="source-tag-warn">更新时间未知</span>'


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

GPU_EFFICIENCY_DATA = {
    "A100":  {"tflops_per_watt": 0.58, "year": 2020},
    "H100":  {"tflops_per_watt": 1.00, "year": 2022},
    "H200":  {"tflops_per_watt": 1.32, "year": 2024},
    "B200":  {"tflops_per_watt": 1.75, "year": 2024},
    "Rubin": {"tflops_per_watt": 2.40, "year": 2026},  # 预估
    "updated": "2025-01",
}

ENERGY_COST_DATA = {
    # 美国数据中心PPA电价 — 改为 EIA 实时获取，此处作为后备默认值
    "us_datacenter_ppa_usd":    0.079,
    "us_datacenter_ppa_source": "静态默认值",
    # 中国西部大工业谷电价（静态）
    "cn_west_industrial_usd":   0.028,
    # 推理电力成本占OpEx比例（%）
    "inference_energy_opex_pct": 15,
    # 海外AI专用电力容量（GW）
    "offshore_ai_capacity_gw":  18,
    # 美国本土AI专用电力容量（GW）
    "us_ai_capacity_gw":        52,
    "updated": "2025-01",
}

# =========================================================
# EIA API — 实时美国商业电价
# =========================================================

EIA_API_KEY = "osqP3deadWXx7Hk1nmgoFXiGZkgXV6aQ4YFofFci"

@st.cache_data(ttl=86400)   # 每 24 小时刷新一次（EIA 数据月度更新）
def fetch_eia_electricity_price() -> dict:
    """
    从 EIA Open Data API v2 获取美国最新商业电价（cents/kWh）。
    端点：electricity/retail-sales
    sector: COM（商业用电，涵盖数据中心 PPA 参考价格）
    frequency: monthly，取最新一期全国均值

    返回字典：
      price_usd     — USD/kWh（已换算）
      period        — 数据期间，如 "2024-11"
      source        — "EIA API (实时)"
      error         — 若获取失败，包含错误说明
    """
    url = "https://api.eia.gov/v2/electricity/retail-sales/data/"
    params = {
        "api_key":       EIA_API_KEY,
        "frequency":     "monthly",
        "data[0]":       "price",
        "facets[sectorid][]": "COM",    # 商业用电
        "sort[0][column]": "period",
        "sort[0][direction]": "desc",
        "length":        1,             # 只取最新一条
        "offset":        0,
    }
    try:
        r = requests.get(url, params=params, timeout=12)
        if r.status_code != 200:
            return {
                "price_usd": None,
                "period":    None,
                "source":    "EIA API 请求失败",
                "error":     f"HTTP {r.status_code}",
            }
        data = r.json()
        rows = data.get("response", {}).get("data", [])
        if not rows:
            return {
                "price_usd": None,
                "period":    None,
                "source":    "EIA API 返回空数据",
                "error":     "No rows returned",
            }
        row = rows[0]
        # EIA 价格单位是 cents/kWh，需除以 100 转为 USD/kWh
        price_cents = float(row.get("price", 0))
        price_usd   = round(price_cents / 100, 4)
        period      = row.get("period", "未知")
        return {
            "price_usd": price_usd,
            "period":    period,
            "source":    "EIA API (实时)",
            "error":     None,
        }
    except Exception as e:
        return {
            "price_usd": None,
            "period":    None,
            "source":    "EIA API 异常",
            "error":     str(e),
        }


# =========================================================
# 数据获取函数 — Yahoo Finance（实时市场信号）
# =========================================================

YF_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

def fetch_yf_chart(ticker):
    url = (
        f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?interval=1mo&range=1y"
    )
    try:
        r = requests.get(url, headers=YF_HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
        return {
            "current_price": meta.get("regularMarketPrice", 0),
            "week52_high":   meta.get("fiftyTwoWeekHigh", 0),
            "week52_low":    meta.get("fiftyTwoWeekLow", 0),
        }
    except Exception:
        return None


def fetch_yf_summary(ticker):
    url = (
        f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{ticker}"
        f"?modules=financialData,defaultKeyStatistics,summaryDetail"
    )
    try:
        r = requests.get(url, headers=YF_HEADERS, timeout=10)
        if r.status_code != 200:
            return None
        data = r.json()
        result = data.get("quoteSummary", {}).get("result", [])
        if not result:
            return None
        merged = {}
        for module in result[0].values():
            if isinstance(module, dict):
                merged.update(module)
        return merged
    except Exception:
        return None


def safe_raw(d, key, default=0):
    try:
        v = (d or {}).get(key, {})
        if isinstance(v, dict):
            return float(v.get("raw", default))
        return float(v) if v is not None else default
    except Exception:
        return default


@st.cache_data(ttl=3600)
def get_energy_stocks():
    results = {}
    for ticker in ["CEG", "VST", "NEE"]:
        chart   = fetch_yf_chart(ticker)
        summary = fetch_yf_summary(ticker)
        if not chart and not summary:
            continue
        current_p   = (chart or {}).get("current_price", 0)
        week52_high = (chart or {}).get("week52_high", 0)
        week52_low  = (chart or {}).get("week52_low", 0)
        rev_growth  = safe_raw(summary, "revenueGrowth") * 100
        price_pos   = ((current_p - week52_low) / (week52_high - week52_low) * 100
                       if week52_high > week52_low else 50)
        results[ticker] = {
            "current_price": current_p,
            "week52_high":   week52_high,
            "week52_low":    week52_low,
            "price_pos_pct": price_pos,
            "rev_growth":    rev_growth,
        }
    return results if results else None


@st.cache_data(ttl=3600)
def get_utility_etf():
    results = {}
    for ticker in ["XLU", "ICLN"]:
        chart = fetch_yf_chart(ticker)
        if not chart:
            continue
        current_p   = chart.get("current_price", 0)
        week52_high = chart.get("week52_high", 0)
        week52_low  = chart.get("week52_low", 0)
        price_pos   = ((current_p - week52_low) / (week52_high - week52_low) * 100
                       if week52_high > week52_low else 50)
        results[ticker] = {
            "current_price": current_p,
            "week52_high":   week52_high,
            "week52_low":    week52_low,
            "price_pos_pct": price_pos,
        }
    return results if results else None


# =========================================================
# ESRI 评分计算
# =========================================================

def compute_infra_score():
    queue       = INFRA_DATA["interconnection_queue_months"]
    queue_s     = max(0, min(100, (queue - 12) / 36 * 100))
    transformer = INFRA_DATA["transformer_lead_time_months"]
    transformer_s = max(0, min(100, (transformer - 12) / 36 * 100))
    avg_reserve = (INFRA_DATA["pjm_reserve_margin_pct"] +
                   INFRA_DATA["ercot_reserve_margin_pct"]) / 2
    reserve_s   = max(0, min(100, (20 - avg_reserve) / 12 * 100))
    return round(queue_s * 0.45 + transformer_s * 0.30 + reserve_s * 0.25, 1)


def compute_cost_score(us_price_usd: float):
    """
    us_price_usd: 从 EIA API 获取的实时价格，或静态后备值
    """
    cn_price  = ENERGY_COST_DATA["cn_west_industrial_usd"]
    ppp_ratio = cn_price / us_price_usd if us_price_usd > 0 else 0.5
    ppp_s     = max(0, min(100, (0.6 - ppp_ratio) / 0.4 * 100))
    opex_pct  = ENERGY_COST_DATA["inference_energy_opex_pct"]
    opex_s    = max(0, min(100, (opex_pct - 10) / 25 * 100))
    return round(ppp_s * 0.55 + opex_s * 0.45, 1)


def compute_efficiency_score():
    latest_perf    = GPU_EFFICIENCY_DATA["B200"]["tflops_per_watt"]
    baseline       = GPU_EFFICIENCY_DATA["H100"]["tflops_per_watt"]
    efficiency_gain = latest_perf / baseline
    return round(max(0, min(100, (2.0 - efficiency_gain) / 0.9 * 100)), 1)


def compute_market_score(energy_stocks, utility_etf):
    if not energy_stocks:
        return 40
    scores = []
    for ticker, d in energy_stocks.items():
        pos = d.get("price_pos_pct", 50)
        if pos > 80:   s = 75
        elif pos > 60: s = 55
        elif pos > 40: s = 35
        else:          s = 20
        scores.append(s)
    if utility_etf:
        for ticker, d in utility_etf.items():
            pos = d.get("price_pos_pct", 50)
            scores.append(pos * 0.6)
    return round(sum(scores) / len(scores)) if scores else 40


def compute_esri(infra_s, cost_s, efficiency_s, market_s):
    return round(
        0.40 * infra_s +
        0.25 * cost_s  +
        0.20 * efficiency_s +
        0.15 * market_s,
        1
    )


def get_state(esri):
    if esri < 30:
        return "SAFE",    "green",  "Grid Optimal",               "电力系统承载AI扩张，能源约束尚未成型，美国借电体系运转正常。"
    elif esri < 50:
        return "WATCH",   "yellow", "Infrastructure Lag Emerging", "基建时滞显现，并网排队开始压缩数据中心交付节奏，局部电力紧张。"
    elif esri < 70:
        return "WARNING", "orange", "Thermodynamic Bottleneck",    "热力学瓶颈形成，能源成本上升向推理成本传导，AI ROI开始承压。"
    else:
        return "CRITICAL","red",    "Energy Monetization Crunch",  "货币化能力受物理侧切断，算力扩张撞墙，需联动稻草一确认CASCADE。"


def score_to_color(s):
    if s < 30:   return "green",  "↗"
    elif s < 50: return "yellow", "→"
    elif s < 70: return "orange", "↘"
    else:        return "red",    "↓"


# =========================================================
# 顶部标题
# =========================================================

st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 20px;">
  <div>
    <div class="main-title">⚡ 稻草四：全球AI能源控制体系失效</div>
    <div class="sub-title">核心命题：AI需求增长速度 &gt; 美国控制体系下的能源扩张速度</div>
  </div>
  <div style="text-align:right; padding-top:4px;">
    <span class="timestamp-text">🕐 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
    <span class="symbol-badge">ESRI · 能源系统风险指数</span>
  </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# 数据加载
# =========================================================

with st.spinner("正在从 Yahoo Finance 拉取核电 · 电力市场数据..."):
    energy_stocks = get_energy_stocks()
    utility_etf   = get_utility_etf()

with st.spinner("正在从 EIA Open Data API 获取最新美国商业电价..."):
    eia_result = fetch_eia_electricity_price()

# 确定实际使用的美国电价
if eia_result["price_usd"] is not None:
    us_price_live = eia_result["price_usd"]
    us_price_source = f"EIA API 实时 · 数据期：{eia_result['period']}"
    us_price_tag_html = f'<span class="source-tag">EIA 实时 ✓ ({eia_result["period"]})</span>'
else:
    us_price_live = ENERGY_COST_DATA["us_datacenter_ppa_usd"]
    us_price_source = f"EIA API 不可用，使用静态后备值 ({eia_result['error']})"
    us_price_tag_html = '<span class="source-tag-warn">⚠ EIA API 失败，使用静态后备</span>'

# =========================================================
# 各分项评分
# =========================================================

infra_s      = compute_infra_score()
cost_s       = compute_cost_score(us_price_live)
efficiency_s = compute_efficiency_score()
market_s     = compute_market_score(energy_stocks, utility_etf)
esri         = compute_esri(infra_s, cost_s, efficiency_s, market_s)

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

st.markdown(f"""
<div class="osci-card">
  <div class="osci-left">
    <div class="osci-label">ENERGY SYSTEM RISK INDEX</div>
    <div style="display:flex; align-items:baseline; gap:12px;">
      <div class="osci-score {state_color}">{esri}</div>
      <div style="font-size:18px; color:#475569; font-weight:600;">/100</div>
    </div>
    <div class="osci-desc">综合评分：{state_cn}</div>
    <div class="osci-bar-wrap">
      <div class="osci-bar-fill" style="width:{esri}%; background:{bar_color};"></div>
    </div>
  </div>
  <div class="osci-right">
    <div class="osci-state-label">SYSTEM STATE</div>
    <div class="osci-state {state_color}">{state}</div>
    <div style="margin-top:8px; font-size:14px; color:#64748b;">{state_eng}</div>
    <div style="margin-top:16px; font-size:13px; color:#64748b; line-height:1.8;">
      基础设施 ×0.40 · 成本压力 ×0.25<br>
      效率对冲 ×0.20 · 市场信号 ×0.15
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

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
    fresh1  = freshness_badge(INFRA_DATA["updated"])
    st.markdown(f"""<div class="metric-card">
  <div class="metric-label">基础设施约束 {fresh1}</div>
  <div class="metric-row">
    <span class="metric-number {infra_color}">{queue}mo</span>
    <span class="metric-arrow {infra_color}">{infra_arrow}</span>
  </div>
  <div class="metric-desc">
    并网排队 {queue}月 · 变压器交期 {xfmr}月<br>
    PJM储备率 {pjm_r}% · ERCOT {ercot_r}%
  </div>
</div>""", unsafe_allow_html=True)

# 卡片2：能源成本压力（EIA 实时）
with c2:
    us_p  = us_price_live
    cn_p  = ENERGY_COST_DATA["cn_west_industrial_usd"]
    ppp   = round(cn_p / us_p, 3) if us_p > 0 else 0
    opex  = ENERGY_COST_DATA["inference_energy_opex_pct"]
    fresh2_cn  = freshness_badge(ENERGY_COST_DATA["updated"])   # 中国价格静态
    eia_period = eia_result.get("period", "")
    st.markdown(f"""<div class="metric-card">
  <div class="metric-label">能源成本压力 {us_price_tag_html}</div>
  <div class="metric-row">
    <span class="metric-number {cost_color}">{ppp:.3f}</span>
    <span class="metric-arrow {cost_color}">{cost_arrow}</span>
  </div>
  <div class="metric-desc">
    中美电价PPP比值（越低美国越贵）<br>
    美国 ${us_p:.4f}/kWh（{us_price_source[:20]}…） · 中国西部 ${cn_p}/kWh{fresh2_cn}<br>
    推理电力占OpEx {opex}%
  </div>
</div>""", unsafe_allow_html=True)

# 卡片3：GPU效率对冲（静态）
with c3:
    b200_eff  = GPU_EFFICIENCY_DATA["B200"]["tflops_per_watt"]
    h100_eff  = GPU_EFFICIENCY_DATA["H100"]["tflops_per_watt"]
    gain      = round(b200_eff / h100_eff, 2)
    rubin_eff = GPU_EFFICIENCY_DATA["Rubin"]["tflops_per_watt"]
    fresh3    = freshness_badge(GPU_EFFICIENCY_DATA["updated"])
    st.markdown(f"""<div class="metric-card">
  <div class="metric-label">GPU效率对冲 {fresh3}</div>
  <div class="metric-row">
    <span class="metric-number {eff_color}">{gain}x</span>
    <span class="metric-arrow {eff_arrow}">{eff_arrow}</span>
  </div>
  <div class="metric-desc">
    B200 vs H100 每瓦性能倍数<br>
    B200={b200_eff}x · Rubin预估={rubin_eff}x（H100基准=1.0）
  </div>
</div>""", unsafe_allow_html=True)

# 卡片4：市场信号
with c4:
    if energy_stocks:
        ceg = energy_stocks.get("CEG", {})
        vst = energy_stocks.get("VST", {})
        ceg_pos = ceg.get("price_pos_pct", 0)
        vst_pos = vst.get("price_pos_pct", 0)
        ceg_p   = ceg.get("current_price", 0)
        vst_p   = vst.get("current_price", 0)
        desc4   = f"CEG ${ceg_p:.1f}（52周位置 {ceg_pos:.0f}%）<br>VST ${vst_p:.1f}（52周位置 {vst_pos:.0f}%）"
        display4 = f"{(ceg_pos+vst_pos)/2:.0f}%"
    else:
        desc4    = "Yahoo Finance 数据暂时无法获取<br>请稍后刷新重试"
        display4 = "N/A"
    st.markdown(f"""<div class="metric-card">
  <div class="metric-label">核电市场信号 <span class="source-tag">Yahoo 实时</span></div>
  <div class="metric-row">
    <span class="metric-number {mkt_color}">{display4}</span>
    <span class="metric-arrow {mkt_color}">{mkt_arrow}</span>
  </div>
  <div class="metric-desc">{desc4}</div>
</div>""", unsafe_allow_html=True)

# =========================================================
# Alert 结论框
# =========================================================

us_cap     = ENERGY_COST_DATA["us_ai_capacity_gw"]
offshore   = ENERGY_COST_DATA["offshore_ai_capacity_gw"]
total_ctrl = us_cap + offshore
global_ai_demand_gw = 85
aecr = round(total_ctrl / global_ai_demand_gw * 100, 1)

alert_map = {
    "SAFE": {
        "box_class":   "alert-box-green",
        "icon":        "✅",
        "title_color": "#22c55e",
        "title":       "结论：美国能源控制体系稳固，AI扩张未受物理约束",
        "body":        f'当前 ESRI = <span class="green"><b>{esri}</b></span>，处于安全区间。AECR（AI能源覆盖率）= <b>{aecr}%</b>，美国控制体系下可调用能源容量覆盖当前全球AI需求。并网排队和变压器交期尚在可控范围，推理成本结构健康。'
    },
    "WATCH": {
        "box_class":   "alert-box",
        "icon":        "👁",
        "title_color": "#fbbf24",
        "title":       "结论：基建时滞出现，AI能源扩张速度开始落后于算力需求",
        "body":        f'当前 ESRI = <span class="yellow"><b>{esri}</b></span>，进入观察区间。AECR = <b>{aecr}%</b>。并网排队周期延长开始压缩数据中心交付节奏，局部电网储备率下降。能源约束尚未推高推理成本，但交付滞后将在6-12个月后显现。建议关注Constellation Energy（CEG）和Vistra（VST）的PPA签约量。'
    },
    "WARNING": {
        "box_class":   "alert-box",
        "icon":        "⚠️",
        "title_color": "#f97316",
        "title":       "结论：热力学瓶颈形成，能源成本开始侵蚀AI推理利润率",
        "body":        f'当前 ESRI = <span class="orange"><b>{esri}</b></span>，进入高危区间。AECR = <b>{aecr}%</b>。中美电价剪刀差扩大，美国数据中心电力成本在全球竞争中处于劣势。能源成本占推理OpEx比例上升，Inference Margin开始承压。注意：这是成本端信号，尚未构成系统崩塌，需联动稻草一（CapEx ROI）共同确认传导。'
    },
    "CRITICAL": {
        "box_class":   "alert-box-red",
        "icon":        "🔴",
        "title_color": "#ef4444",
        "title":       "结论：算力扩张撞墙，需与稻草一联动确认CASCADE",
        "body":        f'当前 ESRI = <span class="red"><b>{esri}</b></span>，进入危机区间。AECR = <b>{aecr}%</b>，美国控制的能源体系已无法覆盖全球AI需求。并网排队彻底失控，数据中心因无电可用成为闲置资产。注意：Straw 4单独不触发CASCADE。CASCADE条件：Straw 4 = CRITICAL <b>且</b> Straw 1 = WARNING以上（AI收入无法覆盖CapEx）同时成立。建议立即对照稻草一财报数据。'
    }
}

alert = alert_map.get(state, alert_map["WATCH"])
st.markdown(f"""
<div class="{alert['box_class']}">
  <div class="alert-icon">{alert['icon']}</div>
  <div class="alert-text">
    <div class="alert-title" style="color:{alert['title_color']};">{alert['title']}</div>
    <div>{alert['body']}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# 下方面板：检测逻辑 + 图表 + 反证模块
# =========================================================

lp, rp = st.columns([1, 1.5])

with lp:
    st.markdown(f"""<div class="panel">
  <div class="panel-title">⚙️ 检测逻辑</div>

  <div class="logic-step">
    <div class="step-num">1</div>
    <div class="step-text"><b>基础设施约束（×0.40）</b>：并网排队周期（45%权重）+ 变压器交期（30%）+ 电网储备率（25%）。物理瓶颈是最难用钱解决的约束。</div>
  </div>
  <div class="threshold-block">
    <div class="threshold-row"><div class="t-dot" style="background:#22c55e;"></div><div class="t-label">排队 &lt;12月 · 储备率 &gt;20%</div><div class="t-arrow">→</div><div class="t-status green">SAFE</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#fbbf24;"></div><div class="t-label">排队 12-24月 · 储备率 15-20%</div><div class="t-arrow">→</div><div class="t-status yellow">WATCH</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#f97316;"></div><div class="t-label">排队 24-36月 · 储备率 10-15%</div><div class="t-arrow">→</div><div class="t-status orange">WARNING</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#ef4444;"></div><div class="t-label">排队 &gt;36月 · 储备率 &lt;10%</div><div class="t-arrow">→</div><div class="t-status red">CRITICAL</div></div>
  </div>

  <div class="logic-step" style="margin-top:14px;">
    <div class="step-num">2</div>
    <div class="step-text"><b>能源成本压力（×0.25）</b>：中美电价PPP比值 + 推理电力占OpEx比例。美国电价现已接入 EIA API 实时数据，每24小时自动刷新。</div>
  </div>
  <div class="threshold-block">
    <div class="threshold-row"><div class="t-dot" style="background:#22c55e;"></div><div class="t-label">PPP &gt; 0.45 · OpEx电力 &lt;10%</div><div class="t-arrow">→</div><div class="t-status green">SAFE</div></div>
    <div class="threshold-row"><div class="t-dot" style="background:#ef4444;"></div><div class="t-label">PPP &lt; 0.25 · OpEx电力 &gt;30%</div><div class="t-arrow">→</div><div class="t-status red">CRITICAL</div></div>
  </div>

  <div class="logic-step" style="margin-top:14px;">
    <div class="step-num">3</div>
    <div class="step-text"><b>GPU效率对冲（×0.20）</b>：B200 vs H100每瓦性能倍数。效率革命是真实的反制力量，倍数越高说明热力学压力越小。</div>
  </div>

  <div class="logic-step" style="margin-top:6px;">
    <div class="step-num">4</div>
    <div class="step-text"><b>市场信号（×0.15）</b>：核电（CEG/VST）股价在52周区间的位置。市场对电力稀缺性的实时定价。</div>
  </div>

</div>""", unsafe_allow_html=True)

with rp:
    st.markdown('<div class="panel"><div class="panel-title">📊 ESRI分项评分构成 · 能源风险传导链</div>', unsafe_allow_html=True)

    categories = ["基础设施约束", "能源成本压力", "GPU效率对冲", "市场信号"]
    scores     = [infra_s, cost_s, efficiency_s, market_s]
    weights    = [0.40, 0.25, 0.20, 0.15]
    bar_labels = [f"{c}  ×{w:.2f}  →  {s:.0f}分"
                  for c, w, s in zip(categories, weights, scores)]

    bar_colors_list = []
    for s in scores:
        if s < 30:   bar_colors_list.append("#22c55e")
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
        text=[f"{s:.0f}" for s in scores],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=15),
    ))
    fig.add_shape(type="line", x0=esri, x1=esri, y0=-0.5, y1=3.5,
                  line=dict(color="rgba(255,255,255,0.3)", width=1.5, dash="dash"))
    fig.add_annotation(x=esri, y=3.7, text=f"ESRI={esri}",
                       showarrow=False, font=dict(color="#94a3b8", size=13), xanchor="center")
    fig.update_layout(
        height=280,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#64748b", size=12),
        margin=dict(l=10, r=60, t=30, b=10),
        xaxis=dict(range=[0, 105], showgrid=True,
                   gridcolor="rgba(255,255,255,0.05)", zeroline=False,
                   tickfont=dict(color="#64748b", size=11)),
        yaxis=dict(showgrid=False, tickfont=dict(color="#94a3b8", size=13)),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    ceg_pos_str = f"CEG: {energy_stocks['CEG']['price_pos_pct']:.0f}% 52w位" if energy_stocks and 'CEG' in energy_stocks else "CEG: N/A"
    vst_pos_str = f"VST: {energy_stocks['VST']['price_pos_pct']:.0f}% 52w位" if energy_stocks and 'VST' in energy_stocks else "VST: N/A"
    eia_tag = f'<span class="source-tag">EIA ✓ {eia_result.get("period","")}</span>' if eia_result["price_usd"] else '<span class="source-tag-warn">EIA 不可用</span>'
    st.markdown(f"""
<div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:4px;">
  <span class="source-tag">Yahoo Finance ✓</span>
  {eia_tag}
  <span class="source-tag-warn">基础设施数据 静态维护</span>
  <span class="source-tag-warn">效率数据 静态维护</span>
  <span class="source-tag-gray">AECR={aecr}%</span>
  <span class="source-tag-gray">{ceg_pos_str}</span>
  <span class="source-tag-gray">{vst_pos_str}</span>
</div>
""", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# 反证模块
# =========================================================

st.markdown("""
<div style="margin-top:24px; margin-bottom:8px;">
  <div style="font-size:18px; font-weight:700; color:#e2e8f0; margin-bottom:4px;">
    🛡️ 反证模块（Counter Signals）— 能源风险对冲因素
  </div>
  <div style="font-size:14px; color:#475569;">
    以下信号若持续增强，将系统性降低稻草四的风险等级
  </div>
</div>
""", unsafe_allow_html=True)

cc1, cc2, cc3 = st.columns(3)

with cc1:
    st.markdown("""<div class="counter-card">
  <div class="counter-title">Counter A · 全球借电体系扩张</div>
  <div class="counter-body">
    中东AI园区（阿联酋 1.5GW · 沙特 2GW）、加拿大水电数据中心、北欧地热数据中心持续扩张。
    若海外AI专用电力容量占比超过40%，说明美国成功绕过本土瓶颈，能源约束缓解。
    <br><br>
    <span style="color:#fbbf24; font-size:13px;">当前海外占比：</span>
    <span style="color:#ffffff; font-weight:700;">""" + f"{round(offshore/(us_cap+offshore)*100,1)}%" + """</span>
  </div>
</div>""", unsafe_allow_html=True)

with cc2:
    rubin_gain = round(GPU_EFFICIENCY_DATA["Rubin"]["tflops_per_watt"] /
                       GPU_EFFICIENCY_DATA["H100"]["tflops_per_watt"], 1)
    st.markdown(f"""<div class="counter-card">
  <div class="counter-title">Counter B · GPU效率革命</div>
  <div class="counter-body">
    Blackwell→Rubin路线图显示每瓦性能持续翻倍。若Rubin量产后每瓦性能达到H100的{rubin_gain}x，
    相同算力需求下电力消耗大幅下降，热力学压力系统性缓解。
    <br><br>
    <span style="color:#fbbf24; font-size:13px;">路线图效率增益：</span>
    <span style="color:#ffffff; font-weight:700;">H100→Rubin={rubin_gain}x</span>
  </div>
</div>""", unsafe_allow_html=True)

with cc3:
    st.markdown("""<div class="counter-card">
  <div class="counter-title">Counter C · 独立能源系统（Behind-the-Meter）</div>
  <div class="counter-body">
    微软重启三里岛核电站（835MW）、谷歌签署SMR协议、Meta自建天然气电站。
    科技巨头脱离公共电网建立私有能源系统，若此趋势加速，公共电网压力下降，
    并网排队瓶颈对AI扩张的约束力减弱。
    <br><br>
    <span style="color:#fbbf24; font-size:13px;">观察信号：</span>
    <span style="color:#ffffff; font-weight:700;">SMR商业化进程 · 核电PPA签约量</span>
  </div>
</div>""", unsafe_allow_html=True)

# =========================================================
# 底部注释：数据说明（含EIA实时状态）
# =========================================================

eia_status_line = (
    f"EIA商业电价（实时）：${us_price_live:.4f}/kWh · 数据期：{eia_result.get('period','N/A')} · 每24小时自动刷新"
    if eia_result["price_usd"]
    else f"EIA API 不可用（{eia_result.get('error','')}），使用静态后备值 ${ENERGY_COST_DATA['us_datacenter_ppa_usd']}/kWh"
)

fresh_infra_inline = freshness_badge(INFRA_DATA["updated"])
fresh_gpu_inline   = freshness_badge(GPU_EFFICIENCY_DATA["updated"])
fresh_cost_inline  = freshness_badge(ENERGY_COST_DATA["updated"])

st.markdown(f"""
<div style="margin-top: 28px; padding: 18px 22px; background: #0a0f1e;
     border: 1px solid rgba(251,191,36,0.15); border-radius: 10px;
     border-left: 3px solid #fbbf24;">
  <div style="font-size:13px; font-weight:700; color:#fbbf24; margin-bottom:10px; letter-spacing:0.5px;">
    📡 数据来源与新鲜度说明
  </div>
  <div style="font-size:13px; color:#64748b; line-height:2.1;">

    <b style="color:#22c55e;">● 实时数据（自动刷新）</b><br>
    &nbsp;&nbsp;· <b style="color:#94a3b8;">美国商业电价：</b>{eia_status_line}<br>
    &nbsp;&nbsp;· <b style="color:#94a3b8;">核电市场信号：</b>Yahoo Finance — CEG · VST · NEE · XLU · ICLN，每小时刷新<br>

    <br><b style="color:#fbbf24;">● 静态数据（手动维护）</b><br>
    &nbsp;&nbsp;· <b style="color:#94a3b8;">基础设施数据 {fresh_infra_inline}：</b>
    并网排队 {INFRA_DATA["interconnection_queue_months"]}月（FERC）·
    变压器交期 {INFRA_DATA["transformer_lead_time_months"]}月（LPT采购调研）·
    PJM储备率 {INFRA_DATA["pjm_reserve_margin_pct"]}%（NERC）<br>
    &nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#475569; font-size:12px;">更新时机：FERC每季度1/4/7/10月 · NERC每年5/11月发布夏冬评估</span><br>

    &nbsp;&nbsp;· <b style="color:#94a3b8;">效率数据 {fresh_gpu_inline}：</b>
    B200每瓦性能={GPU_EFFICIENCY_DATA["B200"]["tflops_per_watt"]}x · Rubin预估={GPU_EFFICIENCY_DATA["Rubin"]["tflops_per_watt"]}x（H100=1.0，来源：NVIDIA官方规格）<br>
    &nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#475569; font-size:12px;">更新时机：每次NVIDIA发布新架构后</span><br>

    &nbsp;&nbsp;· <b style="color:#94a3b8;">中国西部电价 {fresh_cost_inline}：</b>
    ${ENERGY_COST_DATA["cn_west_industrial_usd"]}/kWh（国家能源局，新疆/内蒙直供电）·
    推理电力占OpEx {ENERGY_COST_DATA["inference_energy_opex_pct"]}%（行业均值）<br>
    &nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#475569; font-size:12px;">更新时机：每季度，或国家能源局发布重大价格调整后</span><br>

    <br><b style="color:#94a3b8;">手动更新位置：</b>代码顶部 INFRA_DATA · GPU_EFFICIENCY_DATA · ENERGY_COST_DATA 三个字典<br>
    <b style="color:#94a3b8;">无法自动获取的数据：</b>
    FERC并网队列原始Excel · NERC区域储备率 · 数据中心PPA合同价格（私有付费数据）
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(
    f'<div class="footer-text">'
    f'实时：Yahoo Finance（CEG · VST · NEE · XLU · ICLN）· EIA Open Data API（US商业电价 {eia_result.get("period","N/A")}）&nbsp;|&nbsp; '
    f'静态：FERC · NERC · NVIDIA规格 · BloombergNEF（{INFRA_DATA["updated"]}）&nbsp;|&nbsp; '
    f'{datetime.now().strftime("%Y-%m-%d %H:%M")}'
    f'</div>',
    unsafe_allow_html=True
)
