# =========================================================
# config/api_keys.py
# 所有 API Key 统一在此管理，禁止在各 Straw 文件内硬编码
# =========================================================

import os

FMP_API_KEY  = os.environ.get("FMP_API_KEY", "")
FMP_BASE     = "https://financialmodelingprep.com/stable"

FRED_API_KEY = os.environ.get("FRED_API_KEY", "")
FRED_BASE    = "https://api.stlouisfed.org/fred/series/observations"

EIA_API_KEY  = os.environ.get("EIA_API_KEY", "")
EIA_BASE     = "https://api.eia.gov/v2"
