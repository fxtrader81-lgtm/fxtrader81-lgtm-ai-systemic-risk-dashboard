# Compute-Dollar Risk Terminal — 迁移手册
# 如何将现有 straw2.py ~ straw6.py 接入新架构

## 文件对应关系

| 旧文件         | 新位置                   |
|---------------|--------------------------|
| app.py         | pages/straw1.py ✅ 已完成 |
| straw2.py      | pages/straw2.py 🚧 待迁移 |
| straw3.py      | pages/straw3.py 🚧 待迁移 |
| straw4.py      | pages/straw4.py 🚧 待迁移 |
| straw5.py      | pages/straw5.py 🚧 待迁移 |
| straw6.py      | pages/straw6.py 🚧 待迁移 |

---

## 迁移步骤（以任意 straw 为例）

### 第一步：删除 CSS 块
把文件顶部整段 `st.markdown("""<style>...</style>""", ...)` 删除。
改为：
```python
from components.ui import load_css
load_css()
```

### 第二步：替换 API Keys 和 fetch()
删除：
```python
API_KEY = "jDx2..."
BASE = "https://..."
def fetch(url): ...
```
改为：
```python
from core.data_loader import fmp_income, fmp_cashflow, fred_latest_value, ...
```
数据加载器清单：
- FMP → fmp_income / fmp_cashflow / fmp_index_quote / fmp_historical
- FRED → fred_series / fred_latest_value
- yfinance → yf_history
- GitHub → github_stars
- HuggingFace → huggingface_downloads
- OpenRouter → openrouter_models

### 第三步：替换 Alert HTML
删除手写的 `<div class="alert-box">...</div>`。
改为：
```python
from core.alert_engine import render_alert, render_osci_card

st.markdown(render_alert(state, title, body), unsafe_allow_html=True)
```
state 取值：`"SAFE"` / `"WATCH"` / `"WARNING"` / `"CRITICAL"`

### 第四步：替换 go.Figure()（可选）
如果图表类型已在 components/charts.py 中定义，直接调用：
```python
from components.charts import build_growth_comparison_chart, build_horizontal_bar

fig = build_horizontal_bar(categories, scores, weights, reference_line=osci)
st.plotly_chart(fig, use_container_width=True)
```
如果当前图表类型尚未抽象（如 Straw3 的 GPU 世代图），先保留 go.Figure()，
后续可逐步移入 components/charts.py。

### 第五步：末尾注册评分
```python
from core.score_engine import register_score
register_score("straw2", osci)  # 把当前 Straw 的综合分传入
```
Dashboard 会自动汇总。

---

## 特殊说明

### Straw2（开源压缩）
- 数据源：openrouter_models() / github_stars() / huggingface_downloads()
- 评分：OSCI 总分直接 register_score("straw2", osci)

### Straw3（数据中心减值）
- 数据源：yf_history()（REIT/CMBS/相关ETF）
- GPU 世代图：使用 components/charts.py 的 build_gpu_generation_bar()

### Straw4（能源控制）
- 数据源：EIA API（不在 data_loader 内，可直接调用或添加 eia_series() 函数）
- 添加方式：在 core/data_loader.py 末尾仿照 fred_series() 写一个 eia_series()

### Straw6（宏观预警）
- 数据源：fred_series(["DGS10","DGS30"]) + fmp_index_quote + yf_history
- Tab 结构（ALL/US/CN）保持不变
- 双 Y 轴图：使用 components/charts.py 的 build_dual_axis_chart()

---

## 如何运行

```bash
cd compute_dollar
streamlit run app.py
```

访问 http://localhost:8501
左侧导航栏选择 Straw 页面。
