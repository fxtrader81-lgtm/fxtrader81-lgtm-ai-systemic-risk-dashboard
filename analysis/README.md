# 信贷压力与市场确认：回测归档

更新：2026-09-24。此目录保存探索性分析，不是看板的正式评分规则，也不构成交易信号。

## 核心结论

- 月度回测的 19 条记录是**领先压力信号起点**，不是 19 次独立危机。其中 5 条随后六个月出现相对信号月末至少 10% 的标普500回调，但集中在 2008、2020、2022 三轮下跌。
- 2017 年后的 21 个联合信号月中，7 个随后出现 10% 回调，表观命中率 33.3%。这些月度观测相互重叠，且阈值经过探索；不可把 33.3% 解释为已经校准的事件概率，也不可对 21 个重叠月份直接使用独立二项样本的 95% 置信区间。
- 本次日度核对显示：三轮独立下跌中，月末市场确认都发生在标普500已较近期高点下跌至少 5% 之后。2008 年 3 月/8 月的两次确认时已跌约 15.5%/10.1%，2020 年 2 月确认时约跌 12.8%，2022 年 1 月确认时约跌 5.9%。因此，第07页应描述为**市场传导与跌势确认**；“未来三个月 VIX 峰值”的统计只可描述后续压力，不能证明信号当天的预测能力。
- 2019 年 11 月的领先压力起点距 2020 年新冠下跌有约三个月，但事件是外生冲击；这条关联不能解释为模型预见了疫情。

## 数据与口径

- 月度信号使用 `market_correction_backtest.py` 中的规则；相对过去 120 个月的滚动分位只使用截至观察月的数据。领先压力八项至少三项、市场确认四项至少两项时为联合信号。月度结果分为 2016 年底前与 2017 年后。
- `confirmation_timing_audit.py` 用 Yahoo Finance 的 `^GSPC` 日收盘价核对信号月末、首次确认、此前约六个月高点和首次跌破高点 5%/10% 的日期。2019—2022 年两个关键确认日的 Yahoo 收盘价与 FRED `SP500` 一致到显示精度。FRED `SP500` 仅提供约十年历史，故更早时期仍使用 Yahoo。
- 日度稳健性代理只使用标普63交易日动量、距126交易日高点和当日 VIX 三项中的至少两项，不使用后修订的 STLFSI4。它不是完整的第07页评分。
- 第06页数据中的 NFCI 是每周发布，覆盖前一个周五；历史值可被修订。第07页的 STLFSI4 于 2022 年推出并回填早年历史。因此，旧月度回测是**当前数据版本的历史重建**，尚不是严格按每个历史时点可获得的数据版本进行的实时样本外检验。历史信号必须再核对发布日期和数据版本。

## 文件

| 文件 | 内容 |
|---|---|
| `market_correction_backtest.py` | 月度信号、规则和模型探索代码 |
| `leading_market_transition.py` | 19 个信号起点及随后市场变化 |
| `confirmation_timing_audit.py` | 五条正样本的日度时间顺序核对 |
| `outputs/rule_performance.csv` | 月度规则表现，保留原始探索结果 |
| `outputs/monthly_signal_audit.csv` | 每月信号和随后回撤 |
| `outputs/event_signal_audit.csv` | 预选历史事件审计 |
| `outputs/leading_market_transition_episodes.csv` | 19 个信号起点的记录 |
| `outputs/leading_market_transition_summary.csv` | 信号起点汇总，已纠正名称 |
| `outputs/confirmation_timing_audit.csv` | 2008、2020、2022 日度确认顺序 |

原始数据来源：[FRED BAA10Y](https://fred.stlouisfed.org/series/BAA10Y)、[NFCI](https://fred.stlouisfed.org/series/NFCI)、[STLFSI4](https://fred.stlouisfed.org/series/STLFSI4)、[VIXCLS](https://fred.stlouisfed.org/series/VIXCLS) 与 Yahoo Finance `^GSPC`。方法版本限制见[圣路易斯联储对 STLFSI4 的说明](https://fredblog.stlouisfed.org/2022/11/the-st-louis-feds-financial-stress-index-version-4/)及[芝加哥联储对 NFCI 发布时间和修订的说明](https://www.chicagofed.org/research/data/nfci/current-data-aws)。
