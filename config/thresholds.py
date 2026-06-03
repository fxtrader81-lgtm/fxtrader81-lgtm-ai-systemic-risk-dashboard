# =========================================================
# config/thresholds.py
# 所有风险阈值统一在此定义
# =========================================================

# 通用四段评分：score → state
# 用于 Straw2 / Straw3 / Straw4 的 OSCI 类总分
SCORE_THRESHOLDS = {
    "SAFE":     (0,  25),
    "WATCH":    (25, 50),
    "WARNING":  (50, 75),
    "CRITICAL": (75, 100),
}

# 通用颜色映射
STATE_COLORS = {
    "SAFE":     "#22c55e",
    "WATCH":    "#fbbf24",
    "WARNING":  "#f97316",
    "CRITICAL": "#ef4444",
}

STATE_BOX_CLASS = {
    "SAFE":     "alert-box-green",
    "WATCH":    "alert-box",
    "WARNING":  "alert-box",
    "CRITICAL": "alert-box-red",
}

STATE_ICONS = {
    "SAFE":     "✅",
    "WATCH":    "👁",
    "WARNING":  "⚠️",
    "CRITICAL": "🔴",
}

# Straw1 专用阈值（增速差）
STRAW1_THRESHOLDS = {
    "过热预警": 0.20,   # diff >= 0.20
    "偏热":     0.0,    # 0 <= diff < 0.20
    # diff < 0 → 健康
}

# System Risk Score 加权（后续 Dashboard 用）
STRAW_WEIGHTS = {
    "straw1": 0.20,
    "straw2": 0.20,
    "straw3": 0.15,
    "straw4": 0.15,
    "straw5": 0.15,
    "straw6": 0.15,
}
