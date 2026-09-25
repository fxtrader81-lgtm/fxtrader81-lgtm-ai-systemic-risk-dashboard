# Compute-Dollar Risk Terminal — 公共组件迁移状态

## 当前状态

七个风险因子页面与系统总览已接入统一设计系统。因子05监测融资结构脆弱性，因子06监测信贷与再融资压力，原宏观页面顺延为因子07并只承担跨市场确认。

| 页面 | 公共CSS | 页眉 | 顶部评分卡 | 结论框 | 数据新鲜度 | 页脚 |
|---|---|---|---|---|---|---|
| 因子01 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 因子02 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 因子03 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 因子04 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 因子05 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 因子06 | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| 因子07 | ✅ | ✅ | 阶段卡（分数作辅助） | ✅ | ✅ | ✅ |
| 系统总览 | ✅ | ✅ | AI结构风险组件 | 总览结论组件 | 来源覆盖组件 | ✅ |

## 公共模块

- `components/ui.py`：CSS加载、普通页眉、总览页眉、普通指标卡、面板、检测逻辑、阈值行、说明框、数据新鲜度、页脚和Dashboard信息块。
- `core/alert_engine.py`：四级状态、因子顶部评分卡和动态结论框。
- `core/score_engine.py`：AI结构性总分、七因子导航和评分注册。
- `core/credit_risk.py`：因子06信用利差、实际利率、NFCI与AI融资交易评分。
- `core/macro_risk.py`：因子07股票、VIX、利率冲击和跨市场确认评分。
- `core/transmission_phase.py`：市场阶段及05→06→07传导链快照；仅作观察，不作预测概率。
- `components/transmission.py`：市场阶段卡与四节点传导链的共享展示组件。
- `core/credit_history.py`：信用事件前6个月与前3个月的当前数据版本代理回放。
- `styles/base.css`：颜色变量、全局背景、字体与Streamlit基础覆盖。
- `styles/components.css`：评分卡、指标卡、结论框、Dashboard和响应式组件。
- `styles/pages.css`：页面布局、阈值、历史事件、说明面板和窄屏适配。

旧的 `styles/bloomberg.css` 已删除，避免与当前三层样式重复。

## 页面开发约束

1. 页面文件不得新增 `<style>` 块。
2. 普通指标卡使用 `metric_card()`。
3. 检测步骤与阈值使用 `logic_panel()`。
4. 因子01–06顶部综合评分使用 `render_osci_card()`；因子07以公共 `market_phase_card()` 展示当前市场阶段，评分只作辅助解释。
5. 动态结论使用 `render_alert()`。
6. 数据来源和更新时间使用 `render_data_freshness()` 与 `render_footer()`。
7. 页面特有图表可以保留在页面内；重复出现的布局应进入 `components/`。

## 验证命令

```bash
PYTHONPYCACHEPREFIX=/tmp/codex-pycache python3 -m compileall app.py components config core pages
streamlit run app.py
```
