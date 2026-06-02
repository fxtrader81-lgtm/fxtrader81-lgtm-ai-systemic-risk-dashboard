import streamlit as st
import requests
import plotly.graph_objects as go
from datetime import datetime

# =========================================================
# 页面配置
# =========================================================

st.set_page_config(
page_title="稻草三：数据中心资产减值",
layout="wide"
)

# =========================================================
# CSS — 与稻草一/二完全一致的黑金风格
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

/* DCOI 总分大卡片 */
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
.step-text, .logic-step p {
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
.t-label, .threshold-row p {
   font-size: 15px !important;
   color: #cbd5e1 !important;
   flex: 1;
}
.t-arrow { font-size: 13px; color: #475569; }
.t-status { font-size: 15px !important; font-weight: 600; }

/* 数据源标签 */
.source-tag {
   display: inline-block;
   background: rgba(96,165,250,0.1);
   border: 1px solid rgba(96,165,250,0.2);
   border-radius: 6px;
   padding: 2px 10px;
   font-size: 12px;
   color: #60a5fa;
   margin-left: 8px;
}
.source-tag-gray {
   display: inline-block;
   background: rgba(148,163,184,0.1);
   border: 1px solid rgba(148,163,184,0.2);
   border-radius: 6px;
   padding: 2px 10px;
   font-size: 12px;
   color: #94a3b8;
   margin-left: 8px;
}
.source-tag-warn {
   display: inline-block;
   background: rgba(251,191,36,0.1);
   border: 1px solid rgba(251,191,36,0.25);
   border-radius: 6px;
   padding: 2px 10px;
   font-size: 12px;
   color: #fbbf24;
   margin-left: 8px;
}

/* AOF 功率密度表格 */
.gpu-table { width: 100%; border-collapse: collapse; margin-top: 8px; }
.gpu-table th {
   font-size: 12px; color: #475569; text-transform: uppercase;
   letter-spacing: 0.5px; padding: 8px 12px; text-align: left;
   border-bottom: 1px solid rgba(255,255,255,0.06);
}
.gpu-table td {
   font-size: 14px; color: #cbd5e1; padding: 9px 12px;
   border-bottom: 1px solid rgba(255,255,255,0.03);
}
.gpu-table tr:last-child td { border-bottom: none; }
.gpu-gen-active { color: #fbbf24; font-weight: 700; }
.gpu-gen-danger { color: #ef4444; font-weight: 700; }

.footer-text { margin-top: 14px; color: #1e293b; font-size: 11px; text-align: right; }
#MainMenu { visibility: hidden; } footer { visibility: hidden; } header { visibility: hidden; }
.modebar { display: none !important; }

</style>
""", unsafe_allow_html=True)

# =========================================================
# FMP API 配置（与稻草一相同）
# =========================================================

API_KEY = "jDx2a8ksphDCURyajTmywdYAXyJXBpLN"
BASE    = "https://financialmodelingprep.com/stable"

# =========================================================
# 静态基准数据（手动维护）
# GPU 功率密度代际表 — 数据来自 NVIDIA 官方规格
# 更新频率：每次 NVIDIA 发布新架构后更新，约每年 1-2 次
# =========================================================

GPU_GENERATIONS = [
{"gen": "V100",    "tdp_w": 300,  "rack_kw_min": 10, "rack_kw_max": 20,  "year": 2017, "status": "legacy"},
{"gen": "A100",    "tdp_w": 400,  "rack_kw_min": 20, "rack_kw_max": 30,  "year": 2020, "status": "legacy"},
{"gen": "H100",    "tdp_w": 700,  "rack_kw_min": 40, "rack_kw_max": 80,  "year": 2022, "status": "active"},
{"gen": "H200",    "tdp_w": 1000, "rack_kw_min": 60, "rack_kw_max": 100, "year": 2024, "status": "active"},
{"gen": "B200",    "tdp_w": 1200, "rack_kw_min": 100,"rack_kw_max": 140, "year": 2024, "status": "current"},
{"gen": "Rubin",   "tdp_w": 1400, "rack_kw_min": 180,"rack_kw_max": 220, "year": 2026, "status": "upcoming"},
]

# 传统风冷机房设计功率上限（行业公认工程标准）
LEGACY_RACK_LIMIT_KW = 25   # 传统风冷机房单机柜上限（kW）
UPGRADED_RACK_LIMIT_KW = 50 # 改造后风冷机房单机柜上限（kW）
LIQUID_RACK_LIMIT_KW   = 200 # 液冷机房单机柜上限（kW）

# 当前主流部署 GPU（用于计算 AOF）
CURRENT_DEPLOY_GPU = "H100"
CURRENT_RACK_KW    = 60   # H100 典型部署机柜功率

# AOF 计算：当前主流部署功率 ÷ 老机房设计上限
AOF = round(CURRENT_RACK_KW / LEGACY_RACK_LIMIT_KW, 1)
AOF_UPDATED = "2025-01"

# =========================================================
# 工具函数
# =========================================================

def fetch(url):
try:
r = requests.get(url, timeout=10)
if r.status_code == 200:
return r.json()
return None
except:
return None

def safe(x, k, default=0):
try:
v = x.get(k, default)
return float(v) if v is not None else default
except:
return default

# =========================================================
# 数据获取函数
# =========================================================

@st.cache_data(ttl=3600)
def get_reit_data():
"""
   获取数据中心 REIT 估值压力数据
   EQIX = Equinix（全球最大数据中心REIT）
   DLR  = Digital Realty（第二大数据中心REIT）
   使用 income-statement 获取营收数据，通过营收增速和毛利率判断压力
   """
results = {}
for ticker in ["EQIX", "DLR"]:
income = fetch(f"{BASE}/income-statement?symbol={ticker}&limit=4&apikey={API_KEY}")
cashflow = fetch(f"{BASE}/cash-flow-statement?symbol={ticker}&limit=4&apikey={API_KEY}")

if not isinstance(income, list) or len(income) < 2:
continue

rev_now    = safe(income[0], "revenue")
rev_prev   = safe(income[1], "revenue")
ebitda_now = safe(income[0], "ebitda")
capex_now  = abs(safe(cashflow[0], "capitalExpenditure")) if isinstance(cashflow, list) and cashflow else 0
rev_growth = (rev_now - rev_prev) / rev_prev * 100 if rev_prev > 0 else 0
# 毛利率
gross_margin = safe(income[0], "grossProfitRatio") * 100

results[ticker] = {
"rev_now":     rev_now,
"rev_growth":  rev_growth,
"gross_margin": gross_margin,
"ebitda":      ebitda_now,
"capex":       capex_now,
"period":      income[0].get("date", ""),
"name":        ticker,
}
return results if results else None


@st.cache_data(ttl=3600)
def get_liquid_cooling_data():
"""
   获取液冷设备厂商财务数据
   VRT  = Vertiv（全球最大液冷基础设施供应商）
   SMCI = Super Micro Computer（液冷服务器领先厂商）
   """
results = {}
for ticker in ["VRT", "SMCI"]:
income = fetch(f"{BASE}/income-statement?symbol={ticker}&limit=4&apikey={API_KEY}")

if not isinstance(income, list) or len(income) < 2:
continue

rev_now  = safe(income[0], "revenue")
rev_prev = safe(income[1], "revenue")
rev_growth = (rev_now - rev_prev) / rev_prev * 100 if rev_prev > 0 else None
gross_margin = safe(income[0], "grossProfitRatio") * 100

results[ticker] = {
"rev_growth":   rev_growth,
"gross_margin": gross_margin,
"rev_now":      rev_now,
"period":       income[0].get("date", ""),
"name":         ticker,
}
return results if results else None


@st.cache_data(ttl=3600)
def get_power_data():
"""
   获取电力基础设施数据
   NEE = NextEra Energy（最大可再生能源电力公司，数据中心重要供电方）
   SO  = Southern Company（另一大电力供应商）
   用营收增速代理数据中心用电需求
   """
results = {}
for ticker in ["NEE", "SO"]:
income = fetch(f"{BASE}/income-statement?symbol={ticker}&limit=4&apikey={API_KEY}")

if not isinstance(income, list) or len(income) < 2:
continue

rev_now  = safe(income[0], "revenue")
rev_prev = safe(income[1], "revenue")
rev_growth = (rev_now - rev_prev) / rev_prev * 100 if rev_prev > 0 else 0
op_margin = safe(income[0], "operatingIncomeRatio") * 100

results[ticker] = {
"rev_growth": rev_growth,
"op_margin":  op_margin,
"rev_now":    rev_now,
"period":     income[0].get("date", ""),
"name":       ticker,
}
return results if results else None


# =========================================================
# DCOI 评分计算
# =========================================================

def compute_dcoi(aof_score, reit_stress_score, liquid_signal_score, power_stress_score):
"""
   DCOI = 0.25 x AOF功率压力 + 0.35 x REIT估值压力 + 0.25 x 液冷信号 + 0.15 x 电力压力
   各分项 0-100，越高代表资产减值风险越大

   权重逻辑：
   REIT估值最重(0.35)：市场对底层资产的直接定价，最权威
   AOF功率压力(0.25)：危机的物理根源，但传导有滞后
   液冷信号(0.25)：市场用真金白银投票风冷时代结束
   电力压力(0.15)：物理约束量化，辅助验证
   """
dcoi = (0.25 * aof_score +
0.35 * reit_stress_score +
0.25 * liquid_signal_score +
0.15 * power_stress_score)
return round(dcoi, 1)


def get_state(dcoi):
if dcoi < 25:
return "SAFE", "green", "22c55e", "Compatible Infrastructure", "基础设施与GPU路线图兼容，资产估值稳定，减值风险低。"
elif dcoi < 45:
return "WATCH", "yellow", "fbbf24", "Upgrade Stress Emerging", "功率密度跃迁压力出现，液冷需求加速，风冷资产开始承压。"
elif dcoi < 65:
return "WARNING", "orange", "f97316", "Asset Repricing Underway", "风冷资产开始系统性折价，REIT估值承压，改造成本攀升。"
else:
return "CRITICAL", "red", "ef4444", "Technical Obsolescence Confirmed", "大量AI基建资产技术性贬值信号明确，市场重新定价正在发生。"


# =========================================================
# 分项评分函数
# =========================================================

def score_aof(aof):
"""
   AOF = 当前主流机柜功率 / 老机房设计上限
   AOF < 1.5 -> SAFE(0分); AOF > 4.0 -> CRITICAL(100分)
   """
if aof < 1.5:
return 0, "green", "↗", "SAFE"
elif aof < 2.5:
s = (aof - 1.5) / 1.0 * 33
return round(s), "yellow", "→", "WATCH"
elif aof < 3.5:
s = 33 + (aof - 2.5) / 1.0 * 34
return round(s), "orange", "↘", "WARNING"
else:
s = min(100, 67 + (aof - 3.5) / 0.5 * 33)
return round(s), "red", "↓", "CRITICAL"


def score_reit(reit_data):
"""
   REIT财务压力评分：基于EQIX/DLR的营收增速和毛利率
   营收增速放缓 + 毛利率下降 = 底层资产变现能力恶化
   这是数据中心资产重新定价的财务端信号
   """
if not reit_data:
return 50, "gray", "—", "N/A"

scores = []
for ticker, d in reit_data.items():
g = d.get("rev_growth", 0)
gm = d.get("gross_margin", 50)

# 营收增速越低风险越高
if g > 15:
gs = 10
elif g > 8:
gs = 30
elif g > 3:
gs = 55
elif g > 0:
gs = 70
else:
gs = 90

# 毛利率越低风险越高（REIT毛利率通常50-60%）
if gm > 55:
ms = 10
elif gm > 45:
ms = 30
elif gm > 35:
ms = 55
else:
ms = 80

scores.append(gs * 0.6 + ms * 0.4)

avg = sum(scores) / len(scores) if scores else 50

if avg < 25:
return round(avg), "green", "↗", "SAFE"
elif avg < 50:
return round(avg), "yellow", "→", "WATCH"
elif avg < 70:
return round(avg), "orange", "↘", "WARNING"
else:
return round(avg), "red", "↓", "CRITICAL"


def score_liquid(lc_data):
"""
   液冷信号评分：基于Vertiv和SMCI的营收增速与价格动能
   营收增速越高 = 液冷需求越爆发 = 风冷淘汰越快
   """
if not lc_data:
return 50, "gray", "—", "N/A"

growth_scores = []
for ticker, d in lc_data.items():
if d["rev_growth"] is None:
continue
g = d["rev_growth"]
if g < 10:
s = 10
elif g < 30:
s = 30
elif g < 60:
s = 55
elif g < 100:
s = 75
else:
s = 90
growth_scores.append(s)

if not growth_scores:
return 50, "gray", "—", "N/A"

avg = sum(growth_scores) / len(growth_scores)

if avg < 25:
return round(avg), "green", "↗", "SAFE"
elif avg < 50:
return round(avg), "yellow", "→", "WATCH"
elif avg < 70:
return round(avg), "orange", "↘", "WARNING"
else:
return round(avg), "red", "↓", "CRITICAL"


def score_power(power_data):
"""
   电力压力评分：基于NEE/SO的营收增速
   电力公司收入增速加快 = 数据中心用电需求旺盛 = 功率密度危机的物理证据
   """
if not power_data:
return 30, "gray", "—", "N/A"

scores = []
for ticker, d in power_data.items():
g = d.get("rev_growth", 0)
if g < 3:
s = 15
elif g < 8:
s = 35
elif g < 15:
s = 60
else:
s = 80
scores.append(s)

if not scores:
return 30, "gray", "—", "N/A"

avg = sum(scores) / len(scores)

if avg < 25:
return round(avg), "green", "↗", "SAFE"
elif avg < 45:
return round(avg), "yellow", "→", "WATCH"
elif avg < 65:
return round(avg), "orange", "↘", "WARNING"
else:
return round(avg), "red", "↓", "CRITICAL"


# =========================================================
# 顶部标题
# =========================================================

st.markdown(f"""
<div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom: 20px;">
 <div>
   <div class="main-title">🏗️ 稻草三：数据中心资产技术性减值</div>
   <div class="sub-title">核心检测维度：AI时代GPU迭代速度是否已超出数据中心基础设施的金融折旧周期</div>
 </div>
 <div style="text-align:right; padding-top:4px;">
   <span class="timestamp-text">🕐 更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</span>
   <span class="symbol-badge">DCOI · 数据中心淘汰指数</span>
 </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# 数据加载
# =========================================================

with st.spinner("正在从 FMP API 拉取 REIT · 液冷厂商 · 电力数据..."):
reit_data  = get_reit_data()
lc_data    = get_liquid_cooling_data()
power_data = get_power_data()

# 调试面板（临时）— 确认数据后删除
with st.expander("🔧 调试：API原始返回", expanded=True):
    st.write("**REIT data:**", reit_data)
    st.write("**Liquid cooling data:**", lc_data)
    st.write("**Power data:**", power_data)
    import requests as _req
    for _ticker in ["EQIX", "VRT", "NEE"]:
        _url = f"{BASE}/income-statement?symbol={_ticker}&limit=2&apikey={API_KEY}"
        try:
            _r = _req.get(_url, timeout=10)
            st.write(f"**{_ticker}:** status={_r.status_code} | {_r.text[:300]}")
        except Exception as _e:
            st.write(f"**{_ticker} error:** {_e}")

# =========================================================
# 各分项评分
# =========================================================

aof_s,   aof_color,   aof_arrow,   aof_status   = score_aof(AOF)
reit_s,  reit_color,  reit_arrow,  reit_status  = score_reit(reit_data)
lc_s,    lc_color,    lc_arrow,    lc_status    = score_liquid(lc_data)
power_s, power_color, power_arrow, power_status = score_power(power_data)

# =========================================================
# DCOI 综合评分
# =========================================================

dcoi  = compute_dcoi(aof_s, reit_s, lc_s, power_s)
state, state_color, state_hex, state_eng, state_cn = get_state(dcoi)

bar_color_map = {
"green": "#22c55e", "yellow": "#fbbf24",
"orange": "#f97316", "red": "#ef4444"
}
bar_color = bar_color_map.get(state_color, "#94a3b8")

# =========================================================
# DCOI 总分大卡片
# =========================================================

st.markdown(f"""
<div class="osci-card">
 <div class="osci-left">
   <div class="osci-label">DATA CENTER OBSOLESCENCE INDEX</div>
   <div style="display:flex; align-items:baseline; gap:12px;">
     <div class="osci-score {state_color}">{dcoi}</div>
     <div style="font-size:18px; color:#475569; font-weight:600;">/100</div>
   </div>
   <div class="osci-desc">综合评分：{state_cn}</div>
   <div class="osci-bar-wrap">
     <div class="osci-bar-fill" style="width:{dcoi}%; background:{bar_color};"></div>
   </div>
 </div>
 <div class="osci-right">
   <div class="osci-state-label">SYSTEM STATE</div>
   <div class="osci-state {state_color}">{state}</div>
   <div style="margin-top:8px; font-size:14px; color:#64748b;">{state_eng}</div>
   <div style="margin-top:16px; font-size:13px; color:#64748b; line-height:1.8;">
     GPU功率压力 ×0.25 · REIT估值 ×0.35<br>
     液冷信号 ×0.25 · 电力压力 ×0.15
   </div>
 </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# 四张指标卡片
# =========================================================

c1, c2, c3, c4 = st.columns(4)

# 卡片1：AOF 资产淘汰系数
with c1:
st.markdown(f"""<div class="metric-card">
 <div class="metric-label">AOF 资产淘汰 <span class="source-tag-warn">⚠ 静态基准</span></div>
 <div class="metric-row">
   <span class="metric-number {aof_color}">{AOF}x</span>
   <span class="metric-arrow {aof_color}">{aof_arrow}</span>
 </div>
 <div class="metric-desc">
   {CURRENT_DEPLOY_GPU} 机柜 {CURRENT_RACK_KW}kW ÷ 老机房上限 {LEGACY_RACK_LIMIT_KW}kW<br>
   倍数越高，存量风冷机房技术性报废越严重
 </div>
</div>""", unsafe_allow_html=True)

# 卡片2：REIT 财务压力
with c2:
if reit_data:
eqix = reit_data.get("EQIX", {})
dlr  = reit_data.get("DLR",  {})
eqix_g = eqix.get("rev_growth", 0)
dlr_g  = dlr.get("rev_growth",  0)
avg_g  = (eqix_g + dlr_g) / 2
desc2  = f"EQIX营收增速 {eqix_g:.1f}% · DLR增速 {dlr_g:.1f}%<br>增速放缓 = 底层资产变现能力恶化"
display2 = f"{avg_g:+.1f}%"
else:
desc2 = "FMP API 数据暂时无法获取<br>请稍后刷新重试"
display2 = "N/A"
st.markdown(f"""<div class="metric-card">
 <div class="metric-label">REIT 估值压力 <span class="source-tag">FMP</span></div>
 <div class="metric-row">
   <span class="metric-number {reit_color}">{display2}</span>
   <span class="metric-arrow {reit_color}">{reit_arrow}</span>
 </div>
 <div class="metric-desc">{desc2}</div>
</div>""", unsafe_allow_html=True)

# 卡片3：液冷加速信号
with c3:
if lc_data:
vrt  = lc_data.get("VRT",  {})
smci = lc_data.get("SMCI", {})
vrt_g  = vrt.get("rev_growth")
smci_g = smci.get("rev_growth")
vrt_str  = f"{vrt_g:+.1f}%"  if vrt_g  is not None else "N/A"
smci_str = f"{smci_g:+.1f}%" if smci_g is not None else "N/A"
desc3 = f"Vertiv营收增速 {vrt_str} · SMCI增速 {smci_str}<br>液冷厂商爆发 = 风冷资产加速淘汰"
avg_g = [x for x in [vrt_g, smci_g] if x is not None]
display3 = f"{sum(avg_g)/len(avg_g):+.1f}%" if avg_g else "N/A"
else:
desc3 = "FMP API 数据暂时无法获取<br>请稍后刷新重试"
display3 = "N/A"
st.markdown(f"""<div class="metric-card">
 <div class="metric-label">液冷加速信号 <span class="source-tag">FMP</span></div>
 <div class="metric-row">
   <span class="metric-number {lc_color}">{display3}</span>
   <span class="metric-arrow {lc_color}">{lc_arrow}</span>
 </div>
 <div class="metric-desc">{desc3}</div>
</div>""", unsafe_allow_html=True)

# 卡片4：电力基础设施
with c4:
if power_data:
nee = power_data.get("NEE", {})
so  = power_data.get("SO",  {})
nee_g = nee.get("rev_growth", 0)
so_g  = so.get("rev_growth",  0)
avg_pg = (nee_g + so_g) / 2
desc4 = f"NEE营收增速 {nee_g:+.1f}% · SO增速 {so_g:+.1f}%<br>电力需求增速反映数据中心用电压力"
display4 = f"{avg_pg:+.1f}%"
else:
desc4 = "FMP API 数据暂时无法获取<br>请稍后刷新重试"
display4 = "N/A"
st.markdown(f"""<div class="metric-card">
 <div class="metric-label">电力基础设施 <span class="source-tag">FMP</span></div>
 <div class="metric-row">
   <span class="metric-number {power_color}">{display4}</span>
   <span class="metric-arrow {power_color}">{power_arrow}</span>
 </div>
 <div class="metric-desc">{desc4}</div>
</div>""", unsafe_allow_html=True)

# =========================================================
# Alert 结论框
# =========================================================

alert_map = {
"SAFE": {
"box_class": "alert-box-green",
"icon": "✅",
"title_color": "#22c55e",
"title": "结论：数据中心基础设施与GPU路线图仍然兼容，资产减值风险低",
"body": f'当前 DCOI = <span class="green"><b>{dcoi}</b></span>，处于安全区间。现有数据中心资产能够支撑当前主流GPU部署需求，REIT估值稳定，市场尚未对底层资产进行系统性重新定价。'
},
"WATCH": {
"box_class": "alert-box",
"icon": "👁",
"title_color": "#fbbf24",
"title": "结论：GPU功率密度跃迁压力出现，液冷改造需求开始爆发",
"body": f'当前 DCOI = <span class="yellow"><b>{dcoi}</b></span>，进入观察区间。AOF系数显示老机房兼容性开始下降，液冷厂商订单加速是风冷资产进入折旧加速期的领先信号。建议关注 EQIX/DLR 下季度财报中的 impairment charges 与 retrofit CapEx 数字。'
},
"WARNING": {
"box_class": "alert-box",
"icon": "⚠️",
"title_color": "#f97316",
"title": "结论：风冷资产开始系统性折价，数据中心REIT估值承压",
"body": f'当前 DCOI = <span class="orange"><b>{dcoi}</b></span>，进入高危区间。市场正在重新定价 AI 基础设施资产：AI-ready液冷机房溢价扩大，传统风冷机房折价加剧。注意：这是资产端信号，尚未构成金融传导事件。需联动稻草一（CapEx异常）共同确认。'
},
"CRITICAL": {
"box_class": "alert-box-red",
"icon": "🔴",
"title_color": "#ef4444",
"title": "结论：AI基础设施技术性减值信号明确，需与稻草一联动确认传导",
"body": f'当前 DCOI = <span class="red"><b>{dcoi}</b></span>，进入危机区间。大量存量数据中心资产面临提前技术性报废：GPU迭代速度已远超机房设计寿命，液冷改造成本接近重建，REIT底层资产价值受损。注意：CASCADE事件（CMBS暴雷/信贷收缩）需要稻草一+三联动触发，Straw 3 单独不构成系统性金融危机。建议监控各大银行10-Q中对数据中心抵押贷款的拨备变化。'
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
# 下方面板：检测逻辑 + GPU 功率密度图
# =========================================================

lp, rp = st.columns([1, 1.5])

with lp:
st.markdown(f"""<div class="panel">
 <div class="panel-title">⚙️ 检测逻辑</div>

 <div class="logic-step">
   <div class="step-num">1</div>
   <div class="step-text"><b>AOF 资产淘汰系数（×0.25）</b>：当前主流GPU机柜功率 ÷ 老机房设计上限，倍数越高代表存量机房技术性报废越严重</div>
 </div>
 <div class="threshold-block">
   <div class="threshold-row"><div class="t-dot" style="background:#22c55e;"></div><div class="t-label">AOF &lt; 1.5x</div><div class="t-arrow">→</div><div class="t-status green">SAFE</div></div>
   <div class="threshold-row"><div class="t-dot" style="background:#fbbf24;"></div><div class="t-label">AOF 1.5–2.5x</div><div class="t-arrow">→</div><div class="t-status yellow">WATCH</div></div>
   <div class="threshold-row"><div class="t-dot" style="background:#f97316;"></div><div class="t-label">AOF 2.5–3.5x</div><div class="t-arrow">→</div><div class="t-status orange">WARNING</div></div>
   <div class="threshold-row"><div class="t-dot" style="background:#ef4444;"></div><div class="t-label">AOF &gt; 3.5x</div><div class="t-arrow">→</div><div class="t-status red">CRITICAL</div></div>
 </div>

 <div class="logic-step" style="margin-top:14px;">
   <div class="step-num">2</div>
   <div class="step-text"><b>REIT 估值压力（×0.35）</b>：EQIX/DLR 距52周高点跌幅，市场对底层资产的直接重定价信号</div>
 </div>
 <div class="threshold-block">
   <div class="threshold-row"><div class="t-dot" style="background:#22c55e;"></div><div class="t-label">距高点 &lt; 5%</div><div class="t-arrow">→</div><div class="t-status green">SAFE</div></div>
   <div class="threshold-row"><div class="t-dot" style="background:#fbbf24;"></div><div class="t-label">距高点 5–15%</div><div class="t-arrow">→</div><div class="t-status yellow">WATCH</div></div>
   <div class="threshold-row"><div class="t-dot" style="background:#f97316;"></div><div class="t-label">距高点 15–25%</div><div class="t-arrow">→</div><div class="t-status orange">WARNING</div></div>
   <div class="threshold-row"><div class="t-dot" style="background:#ef4444;"></div><div class="t-label">距高点 &gt; 25%</div><div class="t-arrow">→</div><div class="t-status red">CRITICAL</div></div>
 </div>

 <div class="logic-step" style="margin-top:14px;">
   <div class="step-num">3</div>
   <div class="step-text"><b>液冷加速信号（×0.25）</b>：Vertiv/SMCI 营收增速，液冷厂商爆发 = 风冷淘汰加速</div>
 </div>
 <div class="logic-step" style="margin-top:6px;">
   <div class="step-num">4</div>
   <div class="step-text"><b>电力压力（×0.15）</b>：NEE/XLU 相对强弱，电力需求旺盛是功率密度危机的物理证据</div>
 </div>

</div>""", unsafe_allow_html=True)

with rp:
st.markdown('<div class="panel"><div class="panel-title">⚡ GPU 功率密度代际跃迁（单机柜 kW）</div>', unsafe_allow_html=True)

gens        = [g["gen"]          for g in GPU_GENERATIONS]
rack_mid    = [(g["rack_kw_min"] + g["rack_kw_max"]) / 2 for g in GPU_GENERATIONS]
rack_min    = [g["rack_kw_min"]  for g in GPU_GENERATIONS]
rack_max    = [g["rack_kw_max"]  for g in GPU_GENERATIONS]
years       = [g["year"]         for g in GPU_GENERATIONS]
statuses    = [g["status"]       for g in GPU_GENERATIONS]

bar_colors = []
for s in statuses:
if s == "legacy":
bar_colors.append("#334155")
elif s == "active":
bar_colors.append("#f97316")
elif s == "current":
bar_colors.append("#ef4444")
else:
bar_colors.append("#7c3aed")

fig = go.Figure()

# 风冷上限参考线
fig.add_shape(type="line", x0=-0.5, x1=5.5,
y0=LEGACY_RACK_LIMIT_KW, y1=LEGACY_RACK_LIMIT_KW,
line=dict(color="#22c55e", width=1.5, dash="dash"))
fig.add_annotation(x=5.3, y=LEGACY_RACK_LIMIT_KW + 6,
text=f"传统风冷上限 {LEGACY_RACK_LIMIT_KW}kW",
showarrow=False, font=dict(color="#22c55e", size=11), xanchor="right")

# 改造后风冷上限
fig.add_shape(type="line", x0=-0.5, x1=5.5,
y0=UPGRADED_RACK_LIMIT_KW, y1=UPGRADED_RACK_LIMIT_KW,
line=dict(color="#fbbf24", width=1.5, dash="dot"))
fig.add_annotation(x=5.3, y=UPGRADED_RACK_LIMIT_KW + 6,
text=f"改造风冷上限 {UPGRADED_RACK_LIMIT_KW}kW",
showarrow=False, font=dict(color="#fbbf24", size=11), xanchor="right")

# 柱状图（误差棒表示范围）
fig.add_trace(go.Bar(
x=gens,
y=rack_mid,
marker_color=bar_colors,
marker_line_width=0,
width=0.6,
error_y=dict(
type="data",
symmetric=False,
array=[mx - mid for mx, mid in zip(rack_max, rack_mid)],
arrayminus=[mid - mn for mn, mid in zip(rack_min, rack_mid)],
color="rgba(255,255,255,0.2)",
thickness=2,
),
text=[f"{int(mid)}kW" for mid in rack_mid],
textposition="outside",
textfont=dict(color="#94a3b8", size=13),
))

fig.update_layout(
height=310,
paper_bgcolor="rgba(0,0,0,0)",
plot_bgcolor="rgba(0,0,0,0)",
font=dict(color="#64748b", size=12),
margin=dict(l=10, r=20, t=10, b=10),
xaxis=dict(
showgrid=False, zeroline=False,
tickfont=dict(color="#94a3b8", size=13),
),
yaxis=dict(
title="机柜功率 (kW)",
gridcolor="rgba(255,255,255,0.05)",
zeroline=False,
tickfont=dict(color="#64748b", size=11),
title_font=dict(color="#64748b", size=11),
),
showlegend=False,
)

st.plotly_chart(fig, use_container_width=True)

# 图例说明
st.markdown("""
<div style="display:flex; gap:16px; flex-wrap:wrap; margin-top:2px; padding: 0 4px;">
 <span style="font-size:12px; color:#334155;">■ <span style="color:#94a3b8;">Legacy（已淘汰）</span></span>
 <span style="font-size:12px; color:#f97316;">■ <span style="color:#94a3b8;">Active（主流在用）</span></span>
 <span style="font-size:12px; color:#ef4444;">■ <span style="color:#94a3b8;">Current（最新部署）</span></span>
 <span style="font-size:12px; color:#7c3aed;">■ <span style="color:#94a3b8;">Upcoming（路线图）</span></span>
</div>
""", unsafe_allow_html=True)

# 数据来源标签
vrt_rev  = f"VRT: {lc_data['VRT']['rev_growth']:+.1f}% YoY"   if lc_data and 'VRT'  in lc_data and lc_data['VRT']['rev_growth']  is not None else "VRT: N/A"
smci_rev = f"SMCI: {lc_data['SMCI']['rev_growth']:+.1f}% YoY" if lc_data and 'SMCI' in lc_data and lc_data['SMCI']['rev_growth'] is not None else "SMCI: N/A"

st.markdown(f"""
<div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:10px;">
 <span class="source-tag">FMP API ✓</span>
 <span class="source-tag-warn">GPU规格 静态维护</span>
 <span class="source-tag-gray">{vrt_rev}</span>
 <span class="source-tag-gray">{smci_rev}</span>
 <span class="source-tag-gray">AOF={AOF}x · 基准期 {AOF_UPDATED}</span>
</div>
""", unsafe_allow_html=True)

st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# 底部注释：静态基准数据说明
# =========================================================

st.markdown(f"""
<div style="margin-top: 28px; padding: 18px 22px; background: #0a0f1e;
    border: 1px solid rgba(251,191,36,0.15); border-radius: 10px;
    border-left: 3px solid #fbbf24;">
 <div style="font-size:13px; font-weight:700; color:#fbbf24; margin-bottom:10px; letter-spacing:0.5px;">
   ⚠ 静态基准数据说明（AOF 资产淘汰系数）
 </div>
 <div style="font-size:13px; color:#64748b; line-height:1.9;">
   <b style="color:#94a3b8;">当前基准：</b>
   主流部署 GPU = {CURRENT_DEPLOY_GPU}，典型机柜功率 = {CURRENT_RACK_KW}kW &nbsp;·&nbsp;
   传统风冷机房设计上限 = {LEGACY_RACK_LIMIT_KW}kW（行业公认工程标准）<br>
   <b style="color:#94a3b8;">AOF计算：</b>
   {CURRENT_RACK_KW}kW ÷ {LEGACY_RACK_LIMIT_KW}kW = <b style="color:#fbbf24;">{AOF}x</b> &nbsp;·&nbsp;
   含义：老机房需要改造才能运行当前主流 GPU，改造成本接近新建时 AOF ≥ 4x<br>
   <b style="color:#94a3b8;">数据来源：</b>NVIDIA 官方规格表 &nbsp;·&nbsp;
   <b style="color:#94a3b8;">录入时间：</b>{AOF_UPDATED} &nbsp;·&nbsp;
   <b style="color:#94a3b8;">建议更新频率：</b>每次 NVIDIA 发布新架构后更新（约每年 1-2 次）<br>
   <b style="color:#94a3b8;">更新位置：</b>代码顶部 GPU_GENERATIONS 列表 和 CURRENT_DEPLOY_GPU / CURRENT_RACK_KW 变量<br>
   <b style="color:#94a3b8;">无法自动获取的数据：</b>
   CMBS/ABS信用利差（需Bloomberg终端）· 液冷渗透率（Uptime Institute付费报告）·
   改造成本per MW（工程报价，无公开API）。以上三项用 REIT市场定价 + 液冷厂商营收 作为代理指标。
 </div>
</div>
""", unsafe_allow_html=True)

st.markdown(
f'<div class="footer-text">实时数据：FMP API（EQIX · DLR · VRT · SMCI · NEE · XLU）&nbsp;|&nbsp; 静态数据：NVIDIA GPU规格（{AOF_UPDATED}）&nbsp;|&nbsp; {datetime.now().strftime("%Y-%m-%d %H:%M")}</div>',
unsafe_allow_html=True
)
