# AI 信用传导与循环融资｜第一版实施说明

本专题已拆分并入 05「AI融资结构脆弱性」和 06「AI信贷与再融资压力」，不再占用独立导航页；新增的公司披露和逐发行人AI融资事件不参与现有因子评分或总览结论。06的10%银行融资可得性使用美联储SLOOS广泛贷款标准，不是逐发行人报价；传导链仍只作为待验证的工作假说。06整页历史按季度冻结，2026Q3现有记录是用当前FRED数据版本按9月30日截点完成的版本化复算20.1/SAFE，不是当日自动保存的原始快照。

## 数据及口径

- 覆盖 Microsoft、Amazon、Alphabet、Meta、Oracle 五家公司。OpenAI、Anthropic 只作为已确认关系的观察对象，不推算其未披露财务或合同金额。
- 财务自动取数：SEC `companyfacts` 的公司级、标准 `us-gaap`、USD、10-Q/10-K 事实。05 页默认不请求 SEC；展开公司披露明细后，按所选公司读取并缓存 24 小时，可单独清除此缓存。`SEC_USER_AGENT` 可设为包含机构及联系信息的合法识别字符串。当地网络或 SEC 拒绝访问时不退回无来源的估算。
- 按申报期间的 `start/end` 区分季度原值、年度及年初累计值。优先直接季度数据；仅在相同财政年度起点且期间连续时，以本期累计减上期累计得到季度。TTM 仅在四个连续季度均有值时计算。多种标签是备选概念，不相加。
- 现金资本开支以 `PaymentsToAcquirePropertyPlantAndEquipment` 为首版代理；经营现金流以 `NetCashProvidedByUsedInOperatingActivities` 为准。这些是公司级指标，不是 AI 业务专属。融资租赁、未入账设备应付款及尚未开始的租赁不并入现金资本开支。公司定义的自由现金流单独标注为待核验。
- 现金缺口 `max(CapEx−OCF,0)` 只是现金覆盖代理，不等于实际借款需求。债务流入与偿还必须同时有披露才计算净债务融资；净融资不是 AI CapEx 用途归因。缺失和零分母不填零。
- RPO 仅在 SEC 公司级标准化事实存在时显示。商业 RPO、分部 RPO、未来 12 个月确认比例、客户集中与合同条款仍需核对公司附注；RPO/全公司收入只能视作代理比较。RPO 不是现金、应收、贷款或已实现收入。
- AI 投资损益、未实现收益、权益法及减值没有通用的公司级 AI 分类字段；第一版不虚构调整利润。税前金额不得直接从税后净利扣除。
- 公司债利差、CDS、ABS、private credit、认购倍数、Token 有效成交价、使用量及 GPU 租赁价未接入可比且已授权的数据源；06页不再用这些缺口构造长期N/A指标或模拟SAFE，而是把发行事件单列为非评分证据。10%评分使用FRED `DRTSCILM`大中型企业工商业贷款标准净收紧比例。Token/GPU属于02等需求及算力观察，不强行纳入05/06。

## 来源与复核

- SEC 原始结构化披露：<https://www.sec.gov/search-filings/edgar-application-programming-interfaces>。结构化接口不包含全部公司自定义及分部标签；每家公司需以原始 10-Q/10-K 附注复核。
- 微软与 OpenAI 官方关系：<https://blogs.microsoft.com/blog/2025/01/21/microsoft-and-openai-evolve-partnership-to-drive-the-next-phase-of-ai/>。
- 亚马逊与 Anthropic 官方关系：<https://www.aboutamazon.com/news/company-news/amazon-aws-anthropic-ai>。
- Oracle 与 OpenAI 云关系：<https://www.oracle.com/news/announcement/openai-selects-oracle-cloud-infrastructure-to-extend-microsoft-azure-ai-platform-2024-06-11/>。
- 05页在现有结构评分和图示后展示待验证传导路径、已确认关系与按需展开的五家公司财报/RPO/利润质量证据；06页在广泛信用图表后说明逐发行人信用证据边界，原有经核验交易和新闻线索保持原位但明确不评分；07页继续负责市场确认。06页SLOOS分项按季度自动取数，历史表按同一规则回放。

## 未完成的数据工作

1. 对五家公司的 SEC API 实测及各自 10-K/10-Q 标签映射进行逐项验收。当前开发环境中 SEC API 返回 HTTP 403，因此单元测试只能证明本地计算和异常显示，不证明线上能自动读到财报。
2. 从原始附注手工核验商业 RPO、合同期限、预付款、客户集中、投资损益税后影响、已确认租赁负债、未开始租赁及采购承诺，记录期间、单位、申报日期、页码和原始链接。
3. 取得合法、可比的逐发行人 CDS/债券日终数据后再接 20/60 交易日变化；报价和历史收盘必须分开，Oracle 单列，不能代表组合。
4. 在取得同一研究样本的 Token 有效价格、实际使用量及 GPU 租赁价之前，不用挂牌价或 OpenRouter 平台份额推断全球需求。

## 验证与回滚

运行 `PYTHONPYCACHEPREFIX=/private/tmp/ai-credit-pycache .venv/bin/python -m unittest discover -s tests -v`。计算及合并视图模拟数据由 `tests/test_credit_transmission.py` 覆盖。验证 05 财务明细需先确认 SEC API 可访问，随后检查桌面与窄屏；06 不依赖 SEC API。

合并版使用 `core/credit_transmission.py` 与 `components/credit_transmission_views.py`，由 `pages/straw5.py`、`pages/straw6.py` 调用；独立 `pages/credit_transmission.py` 已移除。若仅撤销此次合并，应移除两页的组件调用、恢复 `app.py` 和 `pages/dashboard.py` 原入口，再从此前版本恢复独立页；不要重置整个仓库或清理无关未跟踪文件。
