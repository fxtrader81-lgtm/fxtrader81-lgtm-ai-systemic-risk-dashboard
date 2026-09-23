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

# AI结构性风险加权。因子06与07是传导/确认层，不混入结构总分。
STRAW_WEIGHTS = {
    "straw1": 0.25,
    "straw2": 0.15,
    "straw3": 0.20,
    "straw4": 0.15,
    "straw5": 0.25,
}
