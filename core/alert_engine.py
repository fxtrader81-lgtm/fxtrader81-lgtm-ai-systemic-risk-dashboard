# =========================================================
# core/alert_engine.py
# 统一预警状态判断与 HTML 渲染
# 各 Straw 调用 render_alert(score, config) 即可
# =========================================================

from config.thresholds import (
    SCORE_THRESHOLDS, STATE_COLORS,
    STATE_BOX_CLASS, STATE_ICONS
)


def score_to_state(score: float) -> str:
    """
    0-100 分 → SAFE / WATCH / WARNING / CRITICAL
    """
    if score < 25:
        return "SAFE"
    elif score < 50:
        return "WATCH"
    elif score < 75:
        return "WARNING"
    else:
        return "CRITICAL"


def render_alert(
    state: str,
    title: str,
    body: str,
    *,
    override_box_class: str = None,
    override_icon: str = None,
    override_title_color: str = None,
) -> str:
    """
    返回完整的 alert HTML 字符串，传入 st.markdown(..., unsafe_allow_html=True)。

    参数
    ----
    state               : "SAFE" / "WATCH" / "WARNING" / "CRITICAL"
    title               : 结论标题文字（支持 HTML 内联）
    body                : 正文描述（支持 HTML 内联）
    override_*          : 可覆盖默认颜色/图标/box_class（特殊 Straw 专用）
    """
    box_class   = override_box_class   or STATE_BOX_CLASS.get(state, "alert-box")
    icon        = override_icon        or STATE_ICONS.get(state, "⚠️")
    title_color = override_title_color or STATE_COLORS.get(state, "#fbbf24")

    return f"""
<div class="{box_class}">
  <div class="alert-icon">{icon}</div>
  <div class="alert-text">
    <div class="alert-title" style="color:{title_color};">{title}</div>
    <div>{body}</div>
  </div>
</div>
"""


def render_osci_card(
    label: str,
    score: float,
    state: str,
    desc: str,
    bar_color: str = None,
    *,
    state_detail: str = "",
    components_html: str = "",
    score_display: str = None,
) -> str:
    """
    渲染 Straw 顶部大分数卡片（OSCI 风格）。
    label   : e.g. "OSCI  开源压缩综合指数"
    score   : 0-100
    state   : SAFE/WATCH/WARNING/CRITICAL
    desc    : 左侧综合评分说明
    state_detail   : 状态下方的英文解释
    components_html: 状态解释下方的指标/权重信息（可含 <br>）
    score_display  : 可选的分数字符串，用于保留各指数既有精度
    """
    color     = bar_color or STATE_COLORS.get(state, "#fbbf24")
    bar_width = 0 if score is None else min(int(score), 100)
    display_score = score_display if score_display is not None else ("N/A" if score is None else f"{score:g}")
    detail_html = (
        f'<div style="margin-top:8px; font-size:14px; color:#94a3b8;">{state_detail}</div>'
        if state_detail else ""
    )
    components_block = (
        '<div style="margin-top:16px; font-size:13px; color:#94a3b8; line-height:1.8;">'
        f"{components_html}</div>"
        if components_html else ""
    )

    return f"""
<div class="osci-card">
  <div class="osci-left">
    <div class="osci-label">{label}</div>
    <div class="osci-score-row">
      <div class="osci-score" style="color:{color};">{display_score}</div>
      <div class="osci-scale">/100</div>
    </div>
    <div class="osci-desc">{desc}</div>
    <div class="osci-bar-wrap">
      <div class="osci-bar-fill" style="width:{bar_width}%; background:{color};"></div>
    </div>
  </div>
  <div class="osci-right">
    <div class="osci-state-label">SYSTEM STATE</div>
    <div class="osci-state" style="color:{color};">{state}</div>
    {detail_html}
    {components_block}
  </div>
</div>
"""
