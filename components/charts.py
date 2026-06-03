# =========================================================
# components/charts.py
# 公共图表组件库
# 各 Straw 调用这里的函数，禁止各自手写 go.Figure()
# =========================================================

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Optional

# ---- 公共 Layout 基础配置 -----------------------------------

_BASE_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#64748b", size=12),
    margin=dict(l=10, r=10, t=10, b=10),
)

_AXIS_STYLE = dict(
    showgrid=True,
    gridcolor="rgba(255,255,255,0.05)",
    zeroline=False,
    tickfont=dict(color="#64748b", size=11),
)


def _base_fig(height: int = 340, r_margin: int = 10) -> go.Figure:
    fig = go.Figure()
    layout = {**_BASE_LAYOUT, "height": height,
              "margin": dict(l=10, r=r_margin, t=10, b=10)}
    fig.update_layout(**layout)
    return fig


# ---- 双线趋势图（Straw1 风格） --------------------------------

def build_growth_comparison_chart(
    years: list,
    series_a: list,
    series_b: list,
    label_a: str = "收入增长率(%)",
    label_b: str = "资本开支增长率(%)",
    color_a: str = "#22c55e",
    color_b: str = "#ef4444",
    height: int = 340,
) -> go.Figure:
    """
    双折线对比图，带数值标注。
    最新数据点放大标注（size=20），历史节点小标注（size=11）。
    """
    fig = _base_fig(height=height, r_margin=95)
    annotations = []

    if years:
        fig.add_trace(go.Scatter(
            x=years, y=series_a, mode="lines+markers",
            name=label_a,
            line=dict(color=color_a, width=2.5),
            marker=dict(size=7),
        ))
        fig.add_trace(go.Scatter(
            x=years, y=series_b, mode="lines+markers",
            name=label_b,
            line=dict(color=color_b, width=2.5),
            marker=dict(size=7),
        ))

        for i, (y, va, vb) in enumerate(zip(years, series_a, series_b)):
            is_last = (i == len(years) - 1)
            sz_a = 20 if is_last else 11
            sz_b = 20 if is_last else 11
            anchor = "left" if is_last else "center"
            xshift = 14 if is_last else 0
            yanchor = "bottom"

            if is_last:
                annotations += [
                    dict(x=y, y=va, text=f"<b>{va:.2f}%</b>",
                         showarrow=False, xanchor=anchor, xshift=xshift,
                         font=dict(color=color_a, size=sz_a)),
                    dict(x=y, y=vb, text=f"<b>{vb:.2f}%</b>",
                         showarrow=False, xanchor=anchor, xshift=xshift,
                         font=dict(color=color_b, size=sz_b)),
                ]
            else:
                annotations += [
                    dict(x=y, y=va, text=f"{va:.2f}%",
                         showarrow=False, yanchor=yanchor, yshift=8,
                         font=dict(color=color_a, size=sz_a)),
                    dict(x=y, y=vb, text=f"{vb:.2f}%",
                         showarrow=False, yanchor=yanchor, yshift=8,
                         font=dict(color=color_b, size=sz_b)),
                ]

    fig.update_layout(
        annotations=annotations,
        legend=dict(orientation="h", y=1.15,
                    font=dict(size=12, color="#94a3b8"),
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(
            type="linear",
            tickvals=years,
            ticktext=[str(y) for y in years],
            showgrid=False, zeroline=False,
            tickfont=dict(color="#64748b", size=11),
        ),
        yaxis=dict(
            title="增长率 (%)",
            gridcolor="rgba(255,255,255,0.05)",
            zeroline=True, zerolinecolor="rgba(255,255,255,0.08)",
            tickfont=dict(color="#64748b"),
            title_font=dict(color="#64748b", size=11),
        ),
    )
    return fig


# ---- 水平条形图（Straw2 OSCI 分项） --------------------------

def build_horizontal_bar(
    categories: list,
    scores: list,
    weights: Optional[list] = None,
    reference_line: Optional[float] = None,
    reference_label: str = "",
    height: int = 320,
) -> go.Figure:
    """
    水平条形图，颜色按分数区间自动着色。
    weights: 可选，影响 y轴标签显示。
    """
    colors = []
    for s in scores:
        if s < 25:   colors.append("#22c55e")
        elif s < 50: colors.append("#fbbf24")
        elif s < 75: colors.append("#f97316")
        else:        colors.append("#ef4444")

    if weights:
        bar_labels = [f"{c}  ×{w:.2f}  →  {s:.0f}分"
                      for c, w, s in zip(categories, weights, scores)]
    else:
        bar_labels = categories

    fig = _base_fig(height=height, r_margin=60)
    fig.add_trace(go.Bar(
        x=scores, y=bar_labels, orientation="h",
        marker_color=colors, marker_line_width=0,
        width=0.55,
        text=[f"{s:.0f}" for s in scores],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=16),
    ))

    if reference_line is not None:
        n = len(scores)
        fig.add_shape(
            type="line",
            x0=reference_line, x1=reference_line,
            y0=-0.5, y1=n - 0.5,
            line=dict(color="rgba(255,255,255,0.3)", width=1.5, dash="dash"),
        )
        fig.add_annotation(
            x=reference_line, y=n - 0.4,
            text=reference_label or f"{reference_line:.0f}",
            showarrow=False,
            font=dict(color="#94a3b8", size=14),
            xanchor="center",
        )

    fig.update_layout(
        xaxis=dict(range=[0, 105], showgrid=True,
                   gridcolor="rgba(255,255,255,0.05)",
                   zeroline=False, tickfont=dict(color="#64748b", size=11)),
        yaxis=dict(showgrid=False, tickfont=dict(color="#94a3b8", size=15)),
        bargap=0.35,
    )
    return fig


# ---- 单线时序图（FRED 国债收益率等） -------------------------

def build_line_chart(
    dates: list,
    values: list,
    name: str = "",
    color: str = "#60a5fa",
    fill: bool = False,
    height: int = 300,
    y_title: str = "",
    reference_lines: Optional[list] = None,  # [{"y": val, "color": ..., "label": ...}]
) -> go.Figure:
    """
    单条折线图（支持 fill=True 面积图）。
    reference_lines: 水平参考线列表。
    """
    fig = _base_fig(height=height)
    fill_mode = "tozeroy" if fill else None

    fig.add_trace(go.Scatter(
        x=dates, y=values, mode="lines",
        name=name, fill=fill_mode,
        line=dict(color=color, width=2),
        fillcolor=f"{color}18" if fill else None,
    ))

    if reference_lines:
        for rl in reference_lines:
            fig.add_hline(
                y=rl["y"],
                line_color=rl.get("color", "rgba(255,255,255,0.2)"),
                line_dash="dash",
                annotation_text=rl.get("label", ""),
                annotation_font_color=rl.get("color", "#94a3b8"),
                annotation_position="bottom right",
            )

    fig.update_layout(
        xaxis=dict(**_AXIS_STYLE, showgrid=False),
        yaxis=dict(**_AXIS_STYLE,
                   title=y_title,
                   title_font=dict(color="#64748b", size=11)),
    )
    return fig


# ---- 双 Y 轴图（股债相关性等） ------------------------------

def build_dual_axis_chart(
    x: list,
    y1: list, y1_name: str, y1_color: str = "#60a5fa",
    y2: list = None, y2_name: str = "", y2_color: str = "#fbbf24",
    height: int = 340,
    y1_title: str = "", y2_title: str = "",
) -> go.Figure:
    """双Y轴折线图，右轴可选。"""
    fig = make_subplots(specs=[[{"secondary_y": y2 is not None}]])

    fig.add_trace(
        go.Scatter(x=x, y=y1, name=y1_name,
                   line=dict(color=y1_color, width=2)),
        secondary_y=False,
    )
    if y2 is not None:
        fig.add_trace(
            go.Scatter(x=x, y=y2, name=y2_name,
                       line=dict(color=y2_color, width=2)),
            secondary_y=True,
        )

    fig.update_layout(
        **{**_BASE_LAYOUT, "height": height},
        legend=dict(orientation="h", y=1.1,
                    font=dict(color="#94a3b8", size=11),
                    bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(**_AXIS_STYLE, showgrid=False)
    fig.update_yaxes(title_text=y1_title, **_AXIS_STYLE, secondary_y=False)
    if y2 is not None:
        fig.update_yaxes(title_text=y2_title, **_AXIS_STYLE, secondary_y=True)

    return fig


# ---- GPU 功耗/世代范围图（Straw3 专用） ----------------------

def build_gpu_generation_bar(
    generations: list,  # [{"gen": "H100\n(2022)", "rack_kw_min":60, "rack_kw_max":100, "status":"active"}]
    highlight_kw: Optional[float] = None,
    height: int = 320,
) -> go.Figure:
    """GPU 代际功耗范围图（堆叠条形，基础值不显示）。"""
    labels   = [g["gen"]          for g in generations]
    kw_min   = [g["rack_kw_min"]  for g in generations]
    kw_range = [g["rack_kw_max"] - g["rack_kw_min"] for g in generations]
    colors   = []
    for g in generations:
        s = g.get("status", "")
        if s == "current": colors.append("#ef4444")
        elif s == "active": colors.append("#fbbf24")
        elif s == "next":   colors.append("#475569")
        else:               colors.append("#1e3a5f")

    fig = _base_fig(height=height)
    # 透明底座
    fig.add_trace(go.Bar(
        x=labels, y=kw_min, marker_color="rgba(0,0,0,0)",
        showlegend=False, hoverinfo="skip",
    ))
    # 实际范围
    fig.add_trace(go.Bar(
        x=labels, y=kw_range, marker_color=colors,
        marker_line_width=0,
        text=[f"{mn}–{mx}kW" for mn, mx in zip(kw_min, [g["rack_kw_max"] for g in generations])],
        textposition="outside",
        textfont=dict(color="#94a3b8", size=11),
        showlegend=False,
    ))

    if highlight_kw is not None:
        fig.add_hline(
            y=highlight_kw,
            line_color="#ef4444", line_dash="dash",
            annotation_text=f"传统上限 {highlight_kw}kW",
            annotation_font_color="#ef4444",
            annotation_position="bottom right",
        )

    fig.update_layout(
        barmode="stack",
        xaxis=dict(showgrid=False, tickfont=dict(color="#94a3b8", size=11)),
        yaxis=dict(title="机架功耗 (kW)", **_AXIS_STYLE,
                   title_font=dict(color="#64748b", size=11)),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    return fig
